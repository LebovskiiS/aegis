"""Ingestor: fetch a library's docs -> vault (markdown) -> chunks.jsonl + integrity.

MVP: tries llms.txt from a map of known sources; if there is no network/URL,
falls back to a bundled sample so the core is testable offline.

AEGIS_OFFLINE=1 forbids the network (air-gap): bundled/mirror only.
In air-gap, ingest runs at build time (with internet) and the vault is baked into the image.

Run:  AEGIS_VAULT=./vault python ingest.py "fastapi==0.115"
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import httpx

VAULT = Path(os.getenv("AEGIS_VAULT", "vault"))

# Known llms-full.txt sources (preferred over scraping).
LLMS_SOURCES = {
    "fastapi": "https://fastapi.tiangolo.com/llms-full.txt",
}

# Bundled sample - so the core runs and is testable without internet.
SAMPLE_DOCS = {
    "fastapi": """# FastAPI

FastAPI is a modern, fast web framework for building APIs with Python,
based on standard type hints.

## First Steps

Create an app and declare a route.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

## StreamingResponse

Use `StreamingResponse` to stream the response body from a generator -
useful for large files and server-sent events, to avoid holding everything in memory.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def number_generator():
    for i in range(10):
        yield f"chunk {i}\\n"

@app.get("/stream")
async def stream():
    return StreamingResponse(number_generator(), media_type="text/plain")
```

## BackgroundTasks

`BackgroundTasks` lets you run work after the response is returned - for example,
sending an email without delaying the client.

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

def write_log(message: str):
    with open("log.txt", "a") as f:
        f.write(message)

@app.post("/send")
async def send(background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, "sent\\n")
    return {"status": "queued"}
```

## Dependencies

The dependency system injects shared logic (auth, DB sessions) into routes via `Depends`.

```python
from fastapi import Depends, FastAPI

app = FastAPI()

def common_params(q: str | None = None):
    return {"q": q}

@app.get("/items/")
async def items(params: dict = Depends(common_params)):
    return params
```
""",
}


def fetch_doc(lib: str) -> tuple[str, str]:
    """Return (markdown, source). Network -> llms.txt; otherwise -> bundled sample.

    AEGIS_OFFLINE=1 -> network forbidden (air-gap): bundled/mirror only.
    In air-gap, ingest runs at build time (with internet); the vault is baked into the image.
    """
    offline = os.getenv("AEGIS_OFFLINE", "0") not in ("0", "false", "False")
    url = None if offline else LLMS_SOURCES.get(lib)
    if url:
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            if r.status_code == 200 and len(r.text) > 200:
                return r.text, url
        except httpx.HTTPError:
            pass
    if lib in SAMPLE_DOCS:
        return SAMPLE_DOCS[lib], f"bundled-sample:{lib}"
    raise ValueError(f"no documentation source for library '{lib}'")


def chunk_markdown(md: str) -> list[dict]:
    """Split markdown by headings (#..###). Keep start/end lines and the anchor."""
    lines = md.split("\n")
    chunks: list[dict] = []
    cur_start = 0
    cur_anchor = "intro"

    def flush(end: int) -> None:
        text = "\n".join(lines[cur_start:end]).strip()
        if text:
            chunks.append(
                {"anchor": cur_anchor, "start_line": cur_start + 1, "end_line": end, "text": text}
            )

    for i, ln in enumerate(lines):
        if re.match(r"^#{1,3}\s+", ln):
            if i > cur_start:
                flush(i)
            cur_start = i
            cur_anchor = ln.lstrip("#").strip()
    flush(len(lines))
    return chunks


def parse_stack(s: str) -> list[tuple[str, str]]:
    """'fastapi==0.115, react@18.3' -> [('fastapi','0.115'), ('react','18.3')]."""
    out: list[tuple[str, str]] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.split(r"==|@", part, maxsplit=1)
        lib = m[0].strip()
        ver = m[1].strip() if len(m) > 1 else "latest"
        out.append((lib, ver))
    return out


def ingest(stack: list[tuple[str, str]]) -> dict:
    VAULT.mkdir(parents=True, exist_ok=True)
    all_chunks: list[dict] = []
    meta: dict = {"libs": [], "files": {}}
    cid = 0
    for lib, version in stack:
        md, source = fetch_doc(lib)
        doc_dir = VAULT / lib / version
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "doc.md"
        doc_path.write_text(md, encoding="utf-8")
        sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
        rel = doc_path.relative_to(VAULT).as_posix()  # forward slashes on every OS

        n = 0
        for ch in chunk_markdown(md):
            ch.update({"id": cid, "lib": lib, "version": version, "file": rel, "source": source})
            all_chunks.append(ch)
            cid += 1
            n += 1

        meta["libs"].append(
            {"lib": lib, "version": version, "source": source, "file": rel, "sha256": sha, "chunks": n}
        )
        meta["files"][rel] = sha

    (VAULT / "chunks.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in all_chunks), encoding="utf-8"
    )
    (VAULT / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def add_one(lib: str, version: str = "latest") -> dict:
    """Append a single library to an existing vault (connected/dev mode).

    Used by POST /add so an agent can request docs on demand. Skips if already
    indexed. Forbidden in air-gap (the caller guards on AEGIS_OFFLINE).
    """
    VAULT.mkdir(parents=True, exist_ok=True)
    chunks_path = VAULT / "chunks.jsonl"
    meta_path = VAULT / "meta.json"
    existing = (
        [json.loads(l) for l in chunks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if chunks_path.exists()
        else []
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"libs": [], "files": {}}
    if any(m["lib"] == lib and m["version"] == version for m in meta["libs"]):
        return meta  # already indexed

    md, source = fetch_doc(lib)
    doc_dir = VAULT / lib / version
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_path = doc_dir / "doc.md"
    doc_path.write_text(md, encoding="utf-8")
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    rel = doc_path.relative_to(VAULT).as_posix()  # forward slashes on every OS

    cid = max((c["id"] for c in existing), default=-1) + 1
    n = 0
    for ch in chunk_markdown(md):
        ch.update({"id": cid, "lib": lib, "version": version, "file": rel, "source": source})
        existing.append(ch)
        cid += 1
        n += 1
    meta["libs"].append(
        {"lib": lib, "version": version, "source": source, "file": rel, "sha256": sha, "chunks": n}
    )
    meta["files"][rel] = sha

    chunks_path.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in existing), encoding="utf-8"
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def verify_integrity() -> list[str]:
    """Compare file sha256 against meta.json. Return the list of mismatches (empty = ok)."""
    meta_path = VAULT / "meta.json"
    if not meta_path.exists():
        return []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    bad = []
    for rel, sha in meta["files"].items():
        p = VAULT / rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            bad.append(rel)
    return bad


if __name__ == "__main__":
    stack = parse_stack(sys.argv[1] if len(sys.argv) > 1 else "fastapi==0.115")
    print(json.dumps(ingest(stack), ensure_ascii=False, indent=2))
