---
name: aegis-docs-mvp
description: MVP scope and next steps
tags: [project, mvp, roadmap]
created: 2026-06-20
---

# MVP and next steps

← [[Aegis-Docs]]

## Status: core built & tested
End-to-end works (ingest -> index -> rewriter -> search -> pointer), in `src/`.
- OK `/health`, `/libs`, validation (422 on empty), `/locate` returns a pointer
- OK input tolerance: UPPERCASE + lib typo (`FASTPI`->`fastapi`) resolved
- LIMITATION BM25-only right now (`vectors:false`, `rewritten:false`): in-query typos and pure-intent queries can miss — exactly what the vector layer + LLM rewriter fix when enabled.

## MVP scope
```
docker run aegis-docs --stack "fastapi==0.115" -v ./myproject:/workspace
```
1. fetch FastAPI docs (priority: llms.txt) -> hash -> vault (markdown)
2. build index (BM25 + vectors)
3. serve HTTP `/locate`
4. Claude calls it via CLAUDE.md instruction

### Components
- [x] `ingest.py` (fetch + chunk + hash + meta)
- [x] `index.py` (FTS5 BM25 + optional fastembed vectors + RRF + lib resolve)
- [x] `app.py` (FastAPI `/health`, `/libs`, `/locate`)
- [x] `query_rewriter.py` (Ollama, fail-safe)
- [ ] `Dockerfile` (two stages: build-time ingest, runtime offline)
- [ ] real doc URLs (replace bundled sample)
- [ ] enable vectors (`pip install fastembed numpy`)

### What we test
- which pointer comes back for a real query
- token cost vs plain RAG
- whether the saving is real on real cases

## Next (after MVP validation)
- v2: auto-read lockfile + watch
- trust package (auto-gen) — see [[04-uniqueness-and-compliance]]
- two containers + internal mirror — see [[03-architecture]]
- (open) fully-offline generation with a local LLM

## Decision before more code
One question drives 80% of complexity: **search-only (Claude thinks)** or **fully-offline (local LLM answers)**?
-> For MVP: **search-only.** Light HTTP service, assembles fast.
