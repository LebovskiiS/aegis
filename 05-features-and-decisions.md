---
name: aegis-docs-features
description: Feature list and decision log
tags: [project, features, decisions]
created: 2026-06-20
---

# Features and decisions

← [[Aegis-Docs]]

## Feature list
1. **Stack via arguments** (`--stack "fastapi==0.115, react@18.3"`) — MVP -> auto-read lockfile (v2)
2. **Download official docs** of the pinned versions (llms.txt -> DevDocs -> fallback scraper)
3. **Integrity** — hash after download + verify on each load (detect tampering/corruption)
4. **Local indexing** on open source (BM25 + vectors + reranker)
5. **HTTP `/locate`** -> pointer `{file, anchor, lines, why}` for Claude
6. **Auto-sync with lockfile** — connected: auto-pull new versions; air-gapped: refresh from mirror
7. **Trust package** — auto-gen data-flow / SBOM / "no PHI" attestation (see [[04-uniqueness-and-compliance]])
8. **Input tolerance** — case + lib-name typo fix
9. **Query rewriter** — local LLM (Ollama), fail-safe

## Decision log
- YES **Container = search engine, not a brain.** Claude thinks. No generative LLM in the core; embedding+reranker suffice. Full LLM = separate fully-offline mode.
- YES **Return a pointer, not text** — savings come from local traversal (0 Claude tokens), not a short answer.
- YES **Obsidian = storage, index = search.** Don't conflate. Wikilink graph = bonus (related blocks), not a replacement for search.
- YES **Anchor by heading, not hard line numbers** — line numbers drift on updates; recompute at ingest.
- YES **Hybrid snippet+pointer** — tiny snippet up front + pointer to read more.
- YES **Integrity = hash + verify** (Sergei's call). Per-block sha256 not needed for start; `source+version` is enough. File hash for integrity — yes.
- YES **Versions from the LOCKFILE**, not raw `requirements.txt`. Python: poetry.lock/uv.lock/pip freeze. Node: package-lock/pnpm-lock.
- YES **MVP: manual `--stack`**, auto-detect = v2.
- NO **Don't compete** on "cheaper/faster" or "for everyone" — one segment: regulated air-gapped.
- YES **Interface = HTTP service** (`/health`, `/locate`, `/libs`, `/reindex`). MVP: plain HTTP on `127.0.0.1` + CLAUDE.md instruction. Prod: wrap in MCP-over-HTTP. MCP runs OVER HTTP — not an alternative.
- YES **Deployment:** localhost (1 per dev) -> shared server behind internal LB for the team.
- CAUTION **Public internet:** breaks air-gap, needs auth+TLS+rate-limit. Default: bind `127.0.0.1`; exposure = customer's deliberate choice.
- YES **"Claude asks correctly" = contract + embeddings, NOT a local LLM.** Clear `/locate` description + semantic embeddings absorb phrasing.
- YES **Query-rewriting via local LLM — INCLUDED.** Qwen2.5-1.5B/3B via Ollama -> plan `{vector_query, keywords, lib?, version?, subqueries}` feeding both hybrid channels. **Fail-safe:** error/timeout -> raw query. Toggle `AEGIS_REWRITE`, 4s timeout, cache, temp=0. Code: `src/query_rewriter.py`. Cost: Ollama+model in image (~1–2 GB); for air-gap bake the model.
- YES **Input tolerance.** Lib name: case normalize + fuzzy-match against indexed libs (`difflib`): `FastAPI`/`FASTAPI`->`fastapi`, `fastpi`->`fastapi`. Better than an LLM (valid set is known & finite). Query: case-insensitive (FTS5/embeddings) + prefix BM25 (`term*`); in-query typos fixed by LLM rewriter + semantics. Code: `index._resolve_lib`.
- YES **Air-gap ingestion — docs brought in ahead of time, NOT fetched at runtime.** (A, default) bake into image at `docker build` with internet; (B) internal mirror/volume; (C) offline bundle. `AEGIS_OFFLINE=1` forbids network.
- YES **Air-gap = egress control, NOT NAT.** Block outbound (k8s NetworkPolicy `egress:[]`, internal-only docker net) = "provable zero-egress". Restricting inbound = a separate concern (access control), not air-gap.
- YES **Two containers (production).** `aegis-indexer` (fetch+index, has internet, runs occasionally) and `aegis-server` (`/locate`, isolated, always on). They never call each other — communicate via a shared store (indexer writes, server reads). Indexer triggered by schedule/build/event, NOT by the server. MVP collapses to one container (server with baked docs); code already split (`ingest.py` / `app.py`).
- FIX SQLite connection `check_same_thread=False` + lock — FastAPI calls `/locate` from a threadpool.

## Open question
- Need **fully-offline generation** (no Claude at all, a local LLM answers) as a premium air-gapped mode? Affects ~80% of complexity. For now: the container only searches; the regular Claude thinks.
