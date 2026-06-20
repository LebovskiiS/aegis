---
name: aegis-docs-moc
description: Project map for Aegis Docs — air-gapped documentation for AI agents in regulated industries
tags: [project, moc, ai, security, mcp, rag]
status: concept + MVP core
created: 2026-06-20
---

# 🛡️ Aegis Docs

> Working name (placeholder) — can be renamed. Idea: shield/protection -> security & compliance.

## One line
**An air-gapped Docker setup that gives Claude precise documentation for the libraries in a project's stack (at the right versions), without sending a single byte outside — and auto-generates a trust package for passing vendor security review in healthcare/fintech.**

## In two sentences
Claude already sees your code but does NOT reliably know the current API of your third-party libraries -> hallucinations. The setup closes that gap: it downloads official docs for the pinned versions, indexes them locally, and returns Claude a **pointer** to the relevant block over HTTP. Corpus traversal happens locally -> 0 Claude tokens.

## Notes
- [[01-idea-and-problem]] — what we solve and why
- [[02-market-analysis]] — what already exists, where the gap is (with sources)
- [[03-architecture]] — who does what, data flow, the two containers
- [[04-uniqueness-and-compliance]] — trust package, why not PHI
- [[05-features-and-decisions]] — feature list + decision log
- [[06-mvp-and-next-steps]] — status & what's next
- [[07-verification-and-proof]] — verified results + token proof

## Status
🟢 **MVP + compliance built and verified end-to-end** on real FastAPI / Kubernetes docs — see [[07-verification-and-proof]].

**Proof:** snippet ~32× / pointer ~321× fewer tokens than reading the page; search = **0 agent tokens**; integrity via sha256 + ed25519 signatures + tamper-evident audit log.

## Key takeaway
The technology (local RAG over docs) is **commodity, not defensible.** Defensible: **air-gapped packaging + verifiability + compliance story + HIPAA/SOC2 expertise.** The barrier is trust, not code. See [[04-uniqueness-and-compliance]].
