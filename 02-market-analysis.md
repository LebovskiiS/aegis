---
name: aegis-docs-market
description: Competitor analysis and where the open niche is
tags: [project, research, market]
created: 2026-06-20
---

# Market analysis

← [[Aegis-Docs]]

## Verdict
The core idea (local RAG over docs via MCP/HTTP) is **already implemented** by several projects. **No exact match for the whole chain exists**, but it **assembles from ready parts** -> the tech is not defensible. The moat is in the wrapper (see [[04-uniqueness-and-compliance]]).

## Cloud (own "docs + cheap")
- **Context7** (Upstash) — versioned docs into the prompt. 54k stars, ~890k weekly downloads. Most popular MCP. **Cloud.**
- **Deepcon** — ~1000 tokens/answer, 90% accuracy vs Context7's 65%. Competes on tokens.
- **Docfork** — 9000+ libs, BM25, ~2000-token cap, MIT. **Cloud.**

## Local (closer to us)
- **mcp-local-rag** (shinpr) — local-first RAG as MCP, semantic+keyword, offline. **~80% of our idea.** No auto-stack, no auto-fetch of official versions.
- **rag-code-mcp** (doITmagic) — privacy-first MCP, 100% local LLM (Ollama)+Qdrant. About **code**, not docs.
- **Onyx** — enterprise RAG, **air-gapped** (UC San Diego, 37k+ users offline on GPUs).
- **DevDocs.io** — ready offline corpus of official docs. For humans, no agent/MCP, no auto-stack. -> a **data source** for us.
- **llms.txt / llms-full.txt** — near-standard; docs in LLM-ready form (Anthropic, Cursor, Vercel). -> **priority source** at ingest.

## What does NOT exist as one product
The chain: **auto-stack -> official docs at exact versions -> local index -> integrity -> pointer to the agent -> air-gapped -> trust package.**

## Honest interpretation
"No analog" != green light. More often it means:
1. **Assembles in a weekend** -> everyone rolls their own, nobody productized it.
2. For many stacks **docs already ship with the package** (`node_modules`, Python sources) -> "downloading docs" is partly redundant.

## Sources
- https://github.com/shinpr/mcp-local-rag
- https://github.com/doITmagic/rag-code-mcp
- https://neuledge.com/blog/2026-02-06/top-7-mcp-alternatives-for-context7-in-2026/
- https://presenc.ai/research/state-of-llms-txt-2026
- https://intuitionlabs.ai/articles/enterprise-ai-code-assistants-air-gapped-environments
- https://ai-sdk.dev/docs/getting-started/coding-agents
