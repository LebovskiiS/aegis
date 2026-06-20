# CLAUDE.md — Aegis Docs

Project conventions for humans and AI assistants. This is a security product aimed
at regulated industries (HIPAA / SOC 2), so the Git history is part of the audit
trail: it must be clean, attributable, and tamper-evident.

## Language
All code, comments, docstrings, commit messages, and docs are in **English**.

---

## Git workflow & rules

### Branching
- `main` — protected, always releasable, audited. **No direct commits or pushes.**
- `dev` — integration branch; features land here first.
- Work branches off `dev`, named by type: `feat/...`, `fix/...`, `sec/...`,
  `docs/...`, `chore/...`, `refactor/...`, `test/...`, `ci/...`.
- Keep branches short-lived; integrate promptly to avoid drift.

### Commits
- **Conventional Commits**: `type(scope): subject` (e.g. `feat(search): add reranker`).
  Types: `feat fix docs sec refactor test chore build ci`.
- Subject: imperative mood, ≤ 72 chars. Body explains **what and why** — the rationale
  is what an auditor reads, not just the diff.
- **Atomic commits**: one logical change each. No `wip`/noise on shared branches (squash).
- **Sign every commit** (`git commit -S`, GPG or SSH signing) for non-repudiation.
  Verify with `git log --show-signature`.
- Trailers: reference the ticket/requirement for traceability (`Refs: AEGIS-123`) and
  keep the AI co-author trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Never commit** secrets, keys, tokens, PHI, customer data, models, or the generated
  `vault/` and `.venv/` (see `.gitignore`). Enforce with a secret scanner (e.g. gitleaks)
  in pre-commit/CI.

### Pull requests & review
- All changes reach `main` via PR: feature → `dev`, then a release PR `dev` → `main`.
  **No self-merge to `main`.**
- Require ≥ 1 review (≥ 2 for security-relevant code: `security.py`, `ingest.py`,
  `query_rewriter.py`, `judge.py`, `Dockerfile`, network/egress config). Use CODEOWNERS.
- PR description: what, why, security impact, and the linked ticket/requirement.
- CI gates must pass before merge: tests, lint, SAST + dependency scan, secret scan, SBOM.

### History integrity (audit-critical)
- **Never force-push or rewrite published history** on `main`/`dev` — the history is
  tamper-evidence.
- Prefer a **linear history** on `main` (squash- or rebase-merge); avoid merge spaghetti.
- Protected-branch rules: require signed commits, passing checks, review, and up-to-date
  branches before merge.

### Releases
- **Semantic versioning.** Tag releases with **annotated, signed tags**: `git tag -s vX.Y.Z`.
  A tag is the exact, audited artifact.
- Generate the CHANGELOG from Conventional Commits. Attach build provenance + SBOM to the
  release.

---

## Rules for Claude specifically
- If on `main` or `dev`, **branch first**; never commit to `main` directly.
- **Commit or push only when the user asks.**
- Use Conventional Commits, keep commits atomic, write audit-grade messages (what + why),
  and always include the `Co-Authored-By` trailer.
- Flag any change touching auth, network/egress, ingest, or LLM prompts in the commit body.
