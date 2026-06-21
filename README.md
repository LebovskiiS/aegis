# 🛡️ Aegis Docs

**A local, air-gappable documentation service for AI coding agents.**

Your AI agent (Claude, Cursor, …) already sees your code, but not the *current* API of
your third-party libraries — so it hallucinates. Aegis indexes the official docs for the
exact versions in your stack, **locally**, and answers an agent's question with a precise
**pointer + snippet** instead of a whole page. The corpus is searched locally, so it
costs the agent **0 tokens** to search, and nothing leaves your machine.

Built for regulated environments (HIPAA / SOC 2): air-gappable, tamper-evident audit
log, signed docs, access control, hardened container.

---

## Why

- **Accurate** — version-pinned official docs, not stale model memory.
- **Cheap** — agent gets ~150 tokens, not a 6k-token page (≈30× less; ≈300× with pointer-only).
- **Private / air-gappable** — docs are baked in; runtime needs no internet.
- **Auditable** — every query is logged in a tamper-evident, signed chain.

---

## Install

Aegis is two layers: a thin **CLI** (control plane) you install on your machine, and
the **engine** (indexer + service) that runs in a container the CLI drives. Heavy deps
live in the image, never on your host — so the CLI stays light enough for Homebrew/pipx.

### 1. The CLI (control plane)
```bash
brew install LebovskiiS/aegis/aegis   # macOS / Linux — Homebrew tap (see packaging/homebrew/)
pipx install aegis-docs               # any OS with Python 3.10+
```

### 2. The engine (container)
```bash
aegis doctor                          # check Docker is ready
aegis up                              # pull + run the engine on 127.0.0.1:8080 (docs baked in)
```
One multi-arch image (`lebovskiis/aegis` on Docker Hub, amd64 + arm64) for every OS.

### Local dev — no Docker, engine in-process
```bash
make demo                             # venv + deps + index a stack + serve — one command
```
Run `make help` for every target.

---

## Quickstart

**Container (recommended) — the CLI drives the engine:**
```bash
aegis up                                       # pull + run the engine (docs baked in)
aegis locate "how do I stream a response" --lib fastapi
aegis status        # | aegis logs -f | aegis down
```

**Local / dev — engine in-process (no Docker):**
```bash
aegis init                            # write aegis.yaml (config template)
aegis ingest "fastapi==0.115"         # fetch + index docs
aegis serve --config aegis.yaml       # start the service
aegis locate "how do I stream a response" --lib fastapi
```
Wire it into your project's `CLAUDE.md` using [claude-snippet.md](claude-snippet.md) so the
agent asks the service instead of guessing.

---

## Configuration (`aegis.yaml`)

`aegis init` writes a fully-commented template ([aegis.example.yaml](aegis.example.yaml)).
Precedence: **defaults < config file < explicit CLI flags.**

| Section | Key settings | Purpose |
|---------|--------------|---------|
| `server` | host, port, vault, **offline**, log_level | bind + air-gap + logging |
| `stack` | list of `lib==version` | what to index on first start |
| `search` | top_k, snippet_max, min_score | result tuning |
| `llm` | enabled, host, model, threads, min_grade | optional relevance judge (off by default) |
| `auth` | user (email), api_key | access control + audit identity |
| `provenance` | pubkey | verify signed manifest at startup |
| `audit` | log, sink (none/local/s3/gcs) | tamper-evident log + shipping |

Load it: `aegis serve --config aegis.yaml`.

---

## CLI reference

| Command | What it does |
|---------|--------------|
| `aegis doctor` | check Docker + the engine image are ready |
| `aegis up` | pull + run the engine container (control plane) |
| `aegis down` / `aegis status` / `aegis logs` | engine lifecycle |
| `aegis init` | write the `aegis.yaml` template |
| `aegis ingest "fastapi==0.115"` | fetch + index docs into the vault |
| `aegis serve --config aegis.yaml` | run the HTTP service |
| `aegis locate "<q>" --lib <lib>` | query a running service |
| `aegis add <lib>` | index a library on demand (connected mode) |
| `aegis health` / `aegis libs` | status / what's indexed |
| `aegis keygen / sign / verify` | ed25519 signed provenance manifest |
| `aegis audit-verify` | check the audit hash-chain |
| `aegis audit-ship --config aegis.yaml` | ship the audit log to a bucket |
| `aegis apikey` | generate a random API key |

---

## LLM judge (optional, off by default)

A local LLM can grade each result's relevance 1–10. Small models (≤3b) grade
unreliably, so this needs a **7b+** model and is best on **separate hardware**.

```bash
aegis serve --llm true --llm-host http://ollama:11434 \
            --llm-model qwen2.5:7b-instruct --threads 2
```
`--threads` caps CPU; the model unloads after each call (frees RAM). Without it, Aegis
ranks by semantic similarity (cosine) and the calling agent judges relevance — fast and
light (~360 MB).

---

## Security & compliance

- **Doc integrity** — sha256 of every doc, checked on `/health` (`integrity_failures`).
- **Tamper-evident audit log** — hash-chained ledger of every query; `aegis audit-verify`
  detects any deletion/edit. Ship to S3/GCS for retention via `aegis audit-ship`.
- **Signed provenance** — `aegis keygen` → `aegis sign`; verified at startup with
  `provenance.pubkey`. Proves the docs are the signed, unmodified set.
- **Access control** — set `auth.user` + `auth.api_key`; clients send `X-API-Key`
  (else 401); the user email is recorded as the audit identity.
- **Air-gap** — `server.offline: true` forbids runtime network; bind `127.0.0.1`; in k8s
  use a NetworkPolicy with `egress: []` for provable zero-egress.
- **Hardened container** — non-root user, read-only vault, healthcheck. CI scans with
  hadolint + Trivy + pip-audit; releases attach an SBOM + provenance.

---

## Architecture

Two roles (production): **`aegis-indexer`** fetches docs + builds the index (has network,
runs occasionally); **`aegis-server`** serves `/locate` (isolated, no egress, always on).
They share a store — the indexer writes, the server reads. The MVP collapses both into one
container. See the design notes ([03-architecture.md](03-architecture.md)).

```
agent --/locate--> aegis-server --reads--> [ vault + index ]  <--writes-- aegis-indexer
                       |                                                        |
                  (no internet)                                       (fetches official docs)
```

---

## Docker Compose (with resource caps)

```bash
docker compose up --build     # mem 1g, cpu 1, loopback only, no LLM
```
See [docker-compose.yml](docker-compose.yml). The judge runs as a separate, capped
`ollama` service under the `judge` profile.

---

## License / status

Working-name **Aegis Docs**, status: MVP core working end-to-end. Not yet published to a
registry — push to GitHub + tag `v0.2.0` to trigger the multi-arch release build.
