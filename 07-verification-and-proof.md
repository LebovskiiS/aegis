---
name: aegis-docs-verification
description: End-to-end verification results and the token-economy proof
tags: [project, verification, proof]
created: 2026-06-20
---

# Verification & proof

← [[Aegis-Docs]]

All verified **live on real documentation** (FastAPI README, 29 sections; also Kubernetes
docs, 134 sections / 189 KB), no LLM, machine clean.

## Token economy (the core claim)
Query: "how do I validate a request body with a Pydantic model"

| Approach | Tokens (~4 chars/token est.) | vs reading the page |
|----------|------------------------------|---------------------|
| Agent reads the whole page | ~5,776 | 1× |
| Aegis **snippet** | ~182 | **~32× fewer** |
| Aegis **pointer only** | ~18 | **~321× fewer** |
| **Corpus search** | **0 agent tokens** (runs locally) | — |

The search runs inside the service; the agent pays only for a short question + the exact slice.

## End-to-end (it works)
- Query → service returned pointer `fastapi/0.115/doc.md` lines **276-311**, score 0.73.
- The agent read **exactly those 36 lines** (the `class Item(BaseModel)` + PUT example), not the
  23,105-char file.
- Kubernetes: 5/5 real questions hit the correct section (score 0.76–0.87), e.g. "roll back a
  deployment" → `deployment.md` *Rolling Back to a Previous Revision*.

## Compliance proofs (all pass; tampering detected)
- **Doc integrity** (sha256): OK; editing a doc → flagged.
- **Audit log** (hash-chain): OK, chain intact; editing/deleting a line → "entry altered / chain broken".
- **Signed manifest** (ed25519): OK, signature valid + vault matches; tampering meta → "vault changed".
- **Auth**: no `X-API-Key` → 401; with key → 200; identity (email) recorded in the audit log.

## Footprint
- Service: ~715 MB with embeddings in RAM (~150 MB BM25-only). **No LLM. 0 tokens to search.**

## One-line claim (for a writeup / pitch)
> A local service indexes the official docs for the exact versions in your stack and gives an
> AI agent a precise pointer/snippet instead of a whole page. Search runs locally (0 agent
> tokens); answers are ~30–300× cheaper in tokens than reading the doc. Verifiable integrity
> (hashes + ed25519 signatures + tamper-evident audit log), air-gappable, no code leaves the box.

## LLM judge — finding
The optional relevance judge needs a **7b+** model (1.5b/3b grade unreliably). On 7b it works
(grade 10 for the correct hit, found:false for out-of-corpus), but it's heavy — keep OFF on a
laptop, run on separate hardware. Default: cosine + the agent's own judgment.
See [[05-features-and-decisions]].
