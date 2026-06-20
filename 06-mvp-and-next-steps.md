---
name: aegis-docs-mvp
description: What's built and what's next
tags: [project, mvp, roadmap]
created: 2026-06-20
---

# Status & next steps

← [[Aegis-Docs]]

## Built & verified (done)
- **Core**: ingest → vault (markdown) → hybrid index (BM25 + embeddings, cosine rank) →
  `/locate` pointer + snippet. Verified on real FastAPI + Kubernetes docs ([[07-verification-and-proof]]).
- **CLI + pip package** (`aegis`): serve / ingest / locate / add / health / libs / init /
  keygen / sign / verify / audit-verify / audit-ship / apikey.
- **Config file** `aegis.yaml` (`aegis init`, `serve --config`) — every setting in one place.
- **LLM judge** optional (`--llm`), fail-safe; works on 7b+, OFF by default.
- **Compliance**: sha256 doc integrity, hash-chain audit log, ed25519 signed manifest,
  API-key/user auth, verbose redacted logger.
- **Container security**: hardened Dockerfile (non-root, read-only vault, healthcheck);
  CI hadolint + Trivy + pip-audit.
- **Distribution**: multi-arch image (amd64 + arm64), GHCR release workflow with SBOM;
  cross-platform (pip + Docker, all OS).

## Next
- **Publish**: PyPI (`pip install aegis-docs`) + push the image to the registry (currently local only).
- **Two-container split** (indexer + server) for production — code is already separated.
- **LLM judge on dedicated hardware** (7b+), wired via `--llm-host`.
- **Trust-package auto-gen** — data-flow + SBOM + "no-PHI" attestation in one command.
- **`update`/reindex** that re-fetches per-lib sources (needs ingest to track source URLs).
- (open) **fully-offline generation** with a local model, for true no-internet environments.

## Key decision
Search-only (the agent thinks) is the default — light, fast, 0 search tokens. The full LLM is
opt-in for separate hardware. See [[05-features-and-decisions]].
