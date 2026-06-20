# Aegis Docs — core (MVP)

A service that returns Claude a **pointer + snippet** for the libraries in a project's
stack. Corpus traversal happens locally (0 Claude tokens). Ships as a pip package with
an `aegis` CLI.

## Layers (degrade gracefully)
1. **BM25** (SQLite FTS5, built-in) — always on.
2. **Vector** (fastembed) — install with `[semantic]`; results ranked by cosine.
3. **LLM judge** (Ollama) — **OFF by default**; needs a 7b+ model. Small models grade
   unreliably; rely on cosine + the calling agent.

## Install (macOS / Windows / Linux)

### Docker — pull from the registry (any OS, recommended)
```bash
docker pull ghcr.io/<owner>/aegis-docs:latest          # multi-arch: amd64 + arm64
docker run -p 127.0.0.1:8080:8080 ghcr.io/<owner>/aegis-docs:latest
```
The same image runs on Intel/AMD and Apple Silicon/ARM.

### pip (any OS with Python 3.10+)
```bash
python3 -m venv .venv
. .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install '.[semantic]'             # service + embeddings (recommended)
# pip install .                       # BM25-only
```

## Run (CLI)
```bash
aegis ingest "fastapi==0.115" --vault ./vault    # fetch + index docs
aegis serve --vault ./vault                       # start service (no LLM)

aegis locate "how do I stream a response" --lib fastapi   # query it
aegis health
aegis libs
aegis add fastapi --version 0.115                 # index a lib on demand (connected mode)
```

### LLM judge toggle (`--llm true|false`, default false)
```bash
# enable later, pointing at a SEPARATE, capped LLM container:
aegis serve --llm true --llm-host http://localhost:11434 \
            --llm-model qwen2.5:7b-instruct --threads 2
```
`--threads` caps model CPU; the model also unloads after each call (frees RAM).

## HTTP API (what the agent calls)
```
GET  /health   GET /libs
POST /locate  {query, lib?, version?}  -> {found, results:[{anchor,file,lines,snippet,score,grade}]}
POST /add     {lib, version?}          (connected mode only)
```

## Docker
```bash
docker compose up --build        # capped (mem 1g, cpu 1), loopback only, no LLM
```
The image bakes docs + the embedding model so the container runs offline.

## For the project's CLAUDE.md
See `claude-snippet.md`.
