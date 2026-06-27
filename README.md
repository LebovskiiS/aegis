# 🛡️ Aegis Docs

**Local, air-gappable documentation for AI coding agents — built for regulated industries.**

[![security](https://github.com/LebovskiiS/aegis/actions/workflows/security.yml/badge.svg)](https://github.com/LebovskiiS/aegis/actions/workflows/security.yml)
[![PyPI](https://img.shields.io/pypi/v/aegis-docs)](https://pypi.org/project/aegis-docs/)
[![Docker](https://img.shields.io/docker/pulls/lebovskiis/aegis)](https://hub.docker.com/r/lebovskiis/aegis)
[![Python](https://img.shields.io/pypi/pyversions/aegis-docs)](https://pypi.org/project/aegis-docs/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## What it is

Your AI agent (Claude, Cursor, …) already reads your code — but **not** the *current* API of
your third-party libraries, so it hallucinates methods that don't exist. **Aegis indexes the
official docs for the exact versions in your stack, locally**, and answers the agent's question
with a precise **pointer + snippet** instead of a whole page.

The corpus is searched **on your machine**, so the agent spends **0 tokens** searching, and
**nothing leaves the host**.

## Why it's different — compliance, security, local

Local RAG over docs is commodity. Aegis is built around the part that isn't: **trust**.
It's designed to be **secure, local, and air-gappable** so it can run inside regulated
environments (**HIPAA / SOC 2**) where sending code or queries to a cloud service is a non-starter:

- **Local / air-gappable** — docs are baked into a container; at runtime it needs **no internet**.
- **Provably private** — bind to loopback, run with `offline: true`; in Kubernetes use a
  NetworkPolicy with `egress: []` for **zero outbound traffic**.
- **Auditable** — every query is recorded in a **tamper-evident, hash-chained, signed** ledger.
- **Verifiable** — every doc is sha256-checked against an **ed25519-signed manifest**.
- **Hardened** — the engine runs **non-root**, with a **read-only** doc vault.

## Result: ~30× fewer tokens

In our benchmark, answering a documentation question through Aegis takes **≈30× fewer tokens**
than letting the agent pull the whole doc page into context — and the **search itself costs the
agent 0 tokens** (it happens locally; the agent only reads the returned snippet). Reproduce it:

```bash
python -m aegis.bench_tokens      # whole page vs Aegis snippet/pointer, same question
```

| Approach | Tokens the agent pays |
|---|---|
| Read the whole doc page | baseline (1×) |
| **Aegis snippet** | **≈30× less** |
| Aegis pointer-only (agent reads exact lines) | ≈300× less |
| Local search step | **0** |

---

## Install

Two layers: a thin **CLI** (control plane) on your machine, and the **engine** (indexer + service)
in a container the CLI drives. The heavy deps live in the image, never on your host.

```bash
# 1) the CLI
brew install LebovskiiS/aegis/aegis     # macOS / Linux (Homebrew tap)
pipx install aegis-docs                 # any OS with Python 3.10+

# 2) the engine (needs Docker)
aegis doctor                            # check Docker is ready
aegis up                                # pull + run the engine on 127.0.0.1:8080 (docs baked in)
```

No Docker? Run the engine in-process for dev: `make demo` (venv + deps + index + serve).

## Use it

```bash
aegis locate "how do I stream a response" --lib fastapi   # pointer + snippet
aegis status      # state/health/ports   |   aegis logs -f   |   aegis down
```

### Native agent integration (MCP)

Expose Aegis to Claude Desktop / Cursor as a native tool — no curl. With the engine running,
add to your MCP client config:

```json
{ "mcpServers": { "aegis": { "command": "aegis", "args": ["mcp"] } } }
```

The agent now calls `locate_docs(query, lib?, version?)` itself and gets correct, version-pinned
docs. Or wire it the plain way via your project's `CLAUDE.md` ([claude-snippet.md](claude-snippet.md)).

---

## Tech used & why

| Layer | Tech | Why |
|---|---|---|
| Engine API | **FastAPI + Uvicorn** | async, typed, fast HTTP service for `/locate` |
| Keyword search | **SQLite FTS5 (BM25)** | built-in, zero infra, always-on baseline |
| Semantic search | **fastembed (ONNX)** | embeddings **locally** — no API calls, small footprint |
| Integrity / signing | **cryptography (ed25519)** | signed provenance manifest for non-repudiation |
| HTTP client | **httpx** | thin CLI ↔ engine, doc fetching |
| Agent protocol | **MCP (stdio)** | native Claude/Cursor integration, no extra deps |
| Packaging | **Docker (multi-arch) + Homebrew/pipx/PyPI** | air-gapped engine + light CLI, every OS |

**Design choice — thin CLI, heavy engine.** The CLI ships via Homebrew/pipx with only light deps
(httpx, cryptography, pyyaml) and *drives* the engine container. All weight (FastAPI, embeddings,
the doc vault) lives in the image — so install stays small and the runtime stays isolated.
The search core works **without any generative LLM**; the agent does the thinking.

## Security & compliance

- **Air-gap** — `server.offline: true` forbids runtime network; bind `127.0.0.1`; in k8s use a
  NetworkPolicy with `egress: []` for provable zero-egress.
- **Tamper-evident audit log** — hash-chained ledger of every query; `aegis audit-verify` detects
  any edit/deletion. Ship to S3/GCS for WORM retention with `aegis audit-ship`.
- **Signed provenance** — `aegis keygen` → `aegis sign`; verified at startup with `provenance.pubkey`.
- **Doc integrity** — sha256 of every doc, checked on `/health`.
- **Access control** — `auth.user` + `auth.api_key`; clients send `X-API-Key`; the user is the audit identity.
- **Hardened container** — non-root, read-only vault, healthcheck. CI scans with hadolint + Trivy + pip-audit.

## License

[MIT](LICENSE) © 2026 Sergei Zheliabovskii
