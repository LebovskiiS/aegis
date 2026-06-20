"""Aegis Docs - core HTTP service.

Endpoints:
  GET  /health   - status + integrity check
  GET  /libs     - what is indexed
  POST /locate   - question -> pointer {file, anchor, lines, why, source}

Run:
  AEGIS_VAULT=./vault AEGIS_STACK="fastapi==0.115" \
    uvicorn app:app --app-dir src --port 8080
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

import ingest as ingest_mod
from index import Index
from query_rewriter import rewrite
from judge import grade

_index = Index()
SNIPPET_MAX = int(os.getenv("AEGIS_SNIPPET_MAX", "1500"))
MIN_SCORE = float(os.getenv("AEGIS_MIN_SCORE", "0.35"))
MIN_GRADE = int(os.getenv("AEGIS_MIN_GRADE", "4"))


class LocateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    lib: str | None = None
    version: str | None = None


class Pointer(BaseModel):
    found: bool
    file: str | None = None
    anchor: str | None = None
    lines: str | None = None
    snippet: str | None = None
    why: str | None = None
    source: str | None = None
    lib: str | None = None
    version: str | None = None
    score: float | None = None
    grade: int | None = None
    rewritten: bool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault = Path(os.getenv("AEGIS_VAULT", "vault"))
    stack = os.getenv("AEGIS_STACK", "")
    if stack and not (vault / "chunks.jsonl").exists():
        ingest_mod.ingest(ingest_mod.parse_stack(stack))
    _index.load()
    yield


app = FastAPI(title="Aegis Docs", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "chunks": len(_index.chunks),
        "vectors": _index.has_vectors,
        "integrity_failures": ingest_mod.verify_integrity(),
    }


@app.get("/libs")
def libs() -> list[dict]:
    meta_path = Path(os.getenv("AEGIS_VAULT", "vault")) / "meta.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))["libs"]


@app.post("/locate", response_model=Pointer)
def locate(req: LocateRequest) -> Pointer:
    plan = rewrite(req.query, req.lib, req.version)
    hits = _index.search(plan.model_dump())
    if not hits:
        return Pointer(found=False, rewritten=plan.rewritten)
    top = hits[0]
    score = top.get("score")
    g = grade(req.query, top["text"])  # LLM relevance 1-10, or None (fail-safe)

    # Confidence gate: prefer the LLM grade if available, else fall back to cosine.
    if g is not None:
        if g < MIN_GRADE:
            return Pointer(found=False, score=score, grade=g, rewritten=plan.rewritten)
    elif score is not None and score < MIN_SCORE:
        return Pointer(found=False, score=score, rewritten=plan.rewritten)

    why = next(
        (ln for ln in top["text"].splitlines() if ln.strip() and not ln.startswith("#")),
        top["anchor"],
    )
    snippet = top["text"]
    if len(snippet) > SNIPPET_MAX:
        snippet = snippet[:SNIPPET_MAX].rstrip() + "\n... (truncated; read more via file + lines)"
    return Pointer(
        found=True,
        file=top["file"],
        anchor=top["anchor"],
        lines=f'{top["start_line"]}-{top["end_line"]}',
        snippet=snippet,
        why=why[:160],
        source=top["source"],
        lib=top["lib"],
        version=top["version"],
        score=score,
        grade=g,
        rewritten=plan.rewritten,
    )
