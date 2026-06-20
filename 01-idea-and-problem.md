---
name: aegis-docs-idea
description: The problem Aegis Docs solves, and why "over docs"
tags: [project, idea]
created: 2026-06-20
---

# Idea and problem

← [[Aegis-Docs]]

## The gap we close
- Claude **already reads your code** (the repo) itself.
- What Claude does **NOT know reliably** — the **current, exact API of third-party libraries** in the stack. It remembers them from training, which goes stale -> **hallucinations** ("no such method", "that's from an old version").

> The product gives Claude correct documentation for the **libraries in the stack, at the right versions**, so it doesn't invent APIs.

## Scope boundary
- "Over docs" = **third-party library docs** (FastAPI, React, Pydantic…), NOT your own code.
- Your code is Claude's job. Library docs are the container's job. They **complement**, not overlap.

## Token-economy principle
The container returns Claude a **pointer**, not text:
```json
{ "file": "fastapi/0.115/doc.md", "anchor": "StreamingResponse", "lines": "20-39", "why": "streaming example" }
```
Claude does one `Read(file, offset, limit)` -> reads exactly those lines.
**Traversal of the whole corpus happens locally -> 0 Claude tokens.** That's the main saving (not a short answer).

## Why this fits Sergei
Target industries (healthcare/fintech, air-gapped, HIPAA/SOC2) = exactly his expertise. The entry barrier here is **trust and compliance**, which he can produce. See [[04-uniqueness-and-compliance]].
