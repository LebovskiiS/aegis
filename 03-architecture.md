---
name: aegis-docs-architecture
description: Architecture — two containers, who does what, data flow
tags: [project, architecture]
created: 2026-06-20
---

# Architecture

← [[Aegis-Docs]]

## Two containers (production shape)
| Container | Role | Internet | Lifecycle |
|-----------|------|----------|-----------|
| **aegis-indexer** | fetch docs + build index | YES (or build-time) | runs occasionally (cron / build / lockfile change) |
| **aegis-server** | serve `/locate` to Claude | NO (egress=0) | runs always |

They **never call each other**. They communicate only through a **shared store** (volume / internal registry): the indexer **writes**, the server **reads**.

```
Schedule (cron) ──starts──▶ aegis-indexer ──writes──▶ [ STORE ]
Claude ──/locate──▶ aegis-server ──reads──▶ [ STORE ]
```

- **Who triggers the indexer:** a schedule / build / event — NOT the server.
- **Who calls the server:** Claude.
- **Both deployed?** Yes. Server = always on; indexer = wakes up, works, exits.
- **MVP:** collapse to ONE container (server with docs baked at build). The split is the production form; code is already split (`ingest.py` = indexer, `app.py` = server), so splitting later is cheap.

## Why split (resolves the air-gap contradiction)
The air-gapped server **never downloads.** Downloading happens earlier/elsewhere, where internet is allowed (build CI or the indexer job). Only finished files travel to the isolated server. Analogy: a factory (internet) makes cans; the bunker (air-gap) just opens them.

## Where docs come from (ingestion)
Docs are brought in **ahead of time**, never fetched at the server's runtime:
- **A. Bake into image (default):** `docker build` (with internet) runs `ingest.py` -> vault baked into image -> runtime offline.
- **B. Internal mirror / volume:** the indexer writes docs to a shared store the server mounts read-only.
- **C. Offline bundle:** ship a versioned doc-pack (tar/OCI) loaded into a volume.

`AEGIS_OFFLINE=1` forbids the network at runtime.

## Pipeline (what happens inside)
### Phase 1 — INDEXING (once, in aegis-indexer)
Done by a **script**. No LLM.
1. Read pinned versions (lockfile)
2. Download docs (httpx) — llms.txt -> DevDocs -> fallback
3. Hash (integrity) -> store as markdown in the vault
4. Chunk by headings -> embeddings -> index (BM25 + vectors)

### Phase 2 — SEARCH (each query, in aegis-server)
1. Claude -> `POST /locate {query}`
2. **Query rewriter** (local LLM, Ollama, fail-safe) -> plan `{vector_query, keywords, lib?, version?}`
3. BM25(keywords) + vector(vector_query) -> reranker picks the best block
4. Return a **pointer** to Claude
5. Claude reads exactly those lines

| Step | Who | LLM? |
|------|-----|------|
| download+chunk+index | script | no, code |
| text->vector | embedding | no, function |
| rewrite query | local LLM (Ollama, fail-safe) | yes, small, optional |
| find candidates | code (vector+BM25) | no |
| pick best | reranker | no, small model |
| read & answer | **Claude** | yes, the only "thinker" |

## Interface: HTTP service (+ optional MCP)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | status + integrity |
| POST | `/locate` | `{query, lib?, version?}` -> pointer |
| GET | `/libs` | what's indexed |
| POST | `/reindex` | rebuild index |

- **MVP:** plain HTTP on `127.0.0.1` + instruction in CLAUDE.md -> Claude calls via Bash/`curl`.
- **Prod:** wrap the same endpoints in **MCP-over-HTTP** -> Claude calls natively. MCP runs OVER HTTP, not an alternative.

## Deployment / network
- Local — one container per dev (bind `127.0.0.1`).
- Company — one shared server behind an internal LB.
- Public internet — breaks air-gap ([[04-uniqueness-and-compliance]]); needs auth+TLS+rate-limit. Egress control (k8s NetworkPolicy `egress:[]`) = the "provable zero-egress" feature. NAT is not the tool.

## Notes
- **Search core works without a generative LLM** (embedding + reranker; rewrite is fail-safe). Generative LLM (Ollama) is used for **query-rewriting** + optional fully-offline answering (not MVP).
- **"Claude asks correctly" = the contract**, not a local LLM. A clear `/locate` description + semantic embeddings absorb phrasing.
- **Index stack (open source, don't build our own):** fastembed / sentence-transformers, LanceDB / sqlite-vec, SQLite FTS5, bge-reranker. Optional framework: LlamaIndex / Haystack.
