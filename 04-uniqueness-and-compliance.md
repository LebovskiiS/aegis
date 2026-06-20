---
name: aegis-docs-moat
description: Differentiation, trust package, why not a business associate
tags: [project, compliance, moat, security]
created: 2026-06-20
---

# Uniqueness and compliance

← [[Aegis-Docs]]

## Where NOT to compete
- NO "cheaper on tokens" / "faster search" — taken.
- NO "universal for everyone" — target one segment: healthcare/fintech air-gapped.

## 4 things mcp-local-rag and others don't have
1. **Provable zero-egress** — strict network policy, "outbound: 0" at startup. Can run from an internal mirror, no internet. Security team verifies in 5 minutes.
2. **Auto-generated trust package** — the product itself emits the documents for vendor security review.
3. **Provenance** — the pointer carries `source + version`. (Hash optional, see integrity.)
4. **Hard pin to lockfile versions** — indexes exactly the versions the customer uses -> no wrong-version hallucinations.

## "Trust package" = what it is
Not a term — a working phrase. When a company installs third-party software, its security team runs a **vendor security review** (a questionnaire). The trust package = a **pre-assembled folder of answers** the product **auto-generates**:
- **data-flow diagram** — "where does data go" -> nothing leaves
- **SBOM** — list of all dependencies
- **attestation** — "the product does not process PHI" -> no BAA needed
- **threat model** — one page

```
[user code] ──> [container: index+search] ──> [Claude locally]
                       │
                       └──✗──> Internet   (NO outbound)
```

## HIPAA — key nuance (strongest card)
> The deciding HIPAA factor is **not where it's hosted, but whether the software touches PHI.**

The product indexes **public technical docs** (FastAPI, React), not medical data -> **touches no PHI** -> **almost certainly NOT a business associate** -> no BAA -> a huge burden drops.

Note: "Local" alone doesn't remove HIPAA — what removes it is **not processing PHI**. That's our case.

## Reality on "audit = clearance" (myth-busting)
- There is **no** single "pass an audit -> everyone trusts you" stamp.
- **SOC 2 Type II** audits the **company and processes over 3–12 months**, tens of $k/year, ongoing. Not a binary.
- HIPAA "certification" as a stamp **doesn't exist**.
- **Main early/solo card:** air-gapped -> the customer **audits the container themselves** (traffic, SBOM, data-flow) before any SOC2. Self-hosting lowers the trust barrier.

## The real advantage
Not code (commodity) and not "a passed audit" (no such event). The edge = **Sergei himself**: HIPAA/SOC2 infra background -> can credibly produce the compliance story, which an indie dev can't.

> Uniqueness = "a docs assistant a hospital's security team will actually approve." Half search, half trust package. Nobody does the second half.
