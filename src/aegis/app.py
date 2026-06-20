"""Aegis Docs - core HTTP service.

Endpoints:
  GET  /health   - status + integrity check
  GET  /libs     - what is indexed
  POST /locate   - question -> graded results (snippet + pointer each)
  POST /add      - fetch+index a library on demand (connected mode only)

Cross-cutting:
  - verbose ops logging (logger.py) — request in/out, timings, query, hits; keys redacted
  - tamper-evident audit log (audit.py) — hash-chained ledger of queries
  - optional API-key auth (auth.py) — identity recorded in the audit log
  - signed provenance manifest verified at startup (provenance.py)
"""
from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import audit
from . import ingest as ingest_mod
from . import provenance
from .auth import identity
from .index import Index
from .judge import grade_many
from .logger import get_logger, redact_headers
from .query_rewriter import rewrite
from .security import LIB_PATTERN, MAX_QUERY_LEN, VERSION_PATTERN, sanitize_query

log = get_logger()
_index = Index()
SNIPPET_MAX = int(os.getenv("AEGIS_SNIPPET_MAX", "1500"))
MIN_SCORE = float(os.getenv("AEGIS_MIN_SCORE", "0.35"))
MIN_GRADE = int(os.getenv("AEGIS_MIN_GRADE", "4"))
TOP_K = int(os.getenv("AEGIS_TOP_K", "3"))


def _offline() -> bool:
    return os.getenv("AEGIS_OFFLINE", "0") not in ("0", "false", "False")


class LocateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LEN)
    lib: str | None = Field(default=None, max_length=64, pattern=LIB_PATTERN)
    version: str | None = Field(default=None, max_length=32, pattern=VERSION_PATTERN)


class AddRequest(BaseModel):
    lib: str = Field(..., min_length=1, max_length=64, pattern=LIB_PATTERN)
    version: str = Field(default="latest", max_length=32, pattern=VERSION_PATTERN)


class Hit(BaseModel):
    anchor: str
    file: str
    lines: str
    snippet: str
    source: str
    lib: str
    version: str
    score: float | None = None
    grade: int | None = None  # LLM relevance 1-10 (None if judge unavailable)


class LocateResponse(BaseModel):
    found: bool  # best result clears the confidence gate
    rewritten: bool | None = None
    results: list[Hit] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault = Path(os.getenv("AEGIS_VAULT", "vault"))
    stack = os.getenv("AEGIS_STACK", "")
    if stack and not (vault / "chunks.jsonl").exists():
        log.info("ingesting stack on first start: %s", stack)
        ingest_mod.ingest(ingest_mod.parse_stack(stack))
    _index.load()
    log.info("index loaded: %d sections, libs=%s, vectors=%s", len(_index.chunks), _index.libs, _index.has_vectors)

    pub = os.getenv("AEGIS_PUBKEY")
    if pub and Path(pub).exists():
        ok, msg = provenance.verify(Path(pub))
        (log.info if ok else log.error)("provenance: %s", msg)
        audit.record({"event": "startup", "provenance_ok": ok, "msg": msg})
    auth_on = bool(os.getenv("AEGIS_API_KEYS", "").strip())
    log.info("auth=%s offline=%s judge=%s", "on" if auth_on else "off", _offline(),
             os.getenv("AEGIS_JUDGE", "0") not in ("0", "false", "False"))
    yield


app = FastAPI(title="Aegis Docs", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    log.debug("-> %s %s headers=%s", request.method, request.url.path, redact_headers(request.headers))
    try:
        resp = await call_next(request)
    except Exception:
        log.exception("!! unhandled error on %s %s", request.method, request.url.path)
        raise
    dt = (time.perf_counter() - t0) * 1000
    lvl = log.debug if request.url.path == "/health" else log.info
    lvl("%s %s -> %s (%.0f ms)", request.method, request.url.path, resp.status_code, dt)
    return resp


@app.get("/health")
def health() -> dict:
    failures = ingest_mod.verify_integrity()
    if failures:
        log.error("integrity failures: %s", failures)
    return {
        "status": "ok",
        "chunks": len(_index.chunks),
        "libs": _index.libs,
        "vectors": _index.has_vectors,
        "offline": _offline(),
        "integrity_failures": failures,
    }


@app.get("/libs")
def libs() -> list[dict]:
    meta_path = Path(os.getenv("AEGIS_VAULT", "vault")) / "meta.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))["libs"]


def _to_snippet(text: str) -> str:
    if len(text) > SNIPPET_MAX:
        return text[:SNIPPET_MAX].rstrip() + "\n... (truncated; read more via file + lines)"
    return text


@app.post("/locate", response_model=LocateResponse)
def locate(req: LocateRequest, who: str = Depends(identity)) -> LocateResponse:
    query = sanitize_query(req.query)
    plan = rewrite(query, req.lib, req.version)
    log.debug("locate: who=%s query=%r lib=%r rewritten=%s", who, query, req.lib, plan.rewritten)
    hits = _index.search(plan.model_dump(), top_k=TOP_K)
    if not hits:
        log.info("locate: who=%s lib=%s -> no hits", who, req.lib)
        audit.record({"event": "locate", "identity": who, "lib": req.lib,
                      "query": query[:120], "found": False, "n": 0})
        return LocateResponse(found=False, rewritten=plan.rewritten)

    grades = grade_many(query, [h["text"] for h in hits])
    results = [
        Hit(
            anchor=h["anchor"],
            file=h["file"],
            lines=f'{h["start_line"]}-{h["end_line"]}',
            snippet=_to_snippet(h["text"]),
            source=h["source"],
            lib=h["lib"],
            version=h["version"],
            score=h.get("score"),
            grade=g,
        )
        for h, g in zip(hits, grades)
    ]
    # Best first: by grade (if any), then cosine score.
    results.sort(key=lambda r: (r.grade if r.grade is not None else -1, r.score or 0.0), reverse=True)

    best = results[0]
    if best.grade is not None:
        found = best.grade >= MIN_GRADE
    elif best.score is not None:
        found = best.score >= MIN_SCORE
    else:
        found = True

    log.debug("locate: %d hits; top=%s score=%s grade=%s found=%s",
              len(results), best.anchor, best.score, best.grade, found)
    audit.record({"event": "locate", "identity": who, "lib": req.lib, "query": query[:120],
                  "found": found, "n": len(results), "top": best.anchor,
                  "file": best.file, "lines": best.lines, "source": best.source})
    return LocateResponse(found=found, rewritten=plan.rewritten, results=results)


@app.post("/add")
def add(req: AddRequest, who: str = Depends(identity)) -> dict:
    if _offline():
        raise HTTPException(
            status_code=403,
            detail="offline mode: docs are added by the indexer at build time, not at runtime",
        )
    try:
        ingest_mod.add_one(req.lib, req.version)
    except ValueError as e:
        log.warning("add: who=%s lib=%s failed: %s", who, req.lib, e)
        raise HTTPException(status_code=404, detail=str(e))
    _index.load()
    log.info("add: who=%s indexed %s==%s (libs now %s)", who, req.lib, req.version, _index.libs)
    audit.record({"event": "add", "identity": who, "lib": req.lib, "version": req.version})
    return {
        "status": "added",
        "lib": req.lib,
        "version": req.version,
        "libs": _index.libs,
        "chunks": len(_index.chunks),
    }
