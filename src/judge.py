"""
Local LLM relevance judge for Aegis Docs.

Grades how well a retrieved snippet answers the query, on a 1-10 scale:
  10 = exactly what was asked (trust it, no need to double-check)
   1 = some overlap but probably not it (Claude should re-check / re-query)

Why this exists: a cosine score alone cannot separate "wrong but topically near"
from "right but typo'd" (observed: an out-of-corpus query scored higher than a
correct-but-misspelled one). An LLM reading the actual content distinguishes them.

Principles:
  - Local, free LLM via Ollama (same model as the rewriter).
  - FAIL-SAFE: any error / timeout / absent Ollama -> return None (no grade);
    the caller falls back to the cosine score. Never blocks search.
  - Cached, low temperature. Grades only the top hit (one call per query).

AEGIS_JUDGE=0 disables it.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
JUDGE_MODEL = os.getenv("AEGIS_JUDGE_MODEL", os.getenv("AEGIS_REWRITE_MODEL", "qwen2.5:3b-instruct"))
JUDGE_ENABLED = os.getenv("AEGIS_JUDGE", "1") not in ("0", "false", "False")
JUDGE_TIMEOUT = float(os.getenv("AEGIS_JUDGE_TIMEOUT", "6.0"))

_PROMPT = """Rate how well the documentation snippet answers the developer's question.
Return STRICT JSON: {{"grade": <integer 1-10>}}
10 = the snippet directly and fully answers the question.
1 = barely related, probably not what was asked.

Question: {query}

Snippet:
{snippet}

JSON:"""


def _call_ollama(prompt: str) -> str:
    resp = httpx.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": JUDGE_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=JUDGE_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["response"]


@lru_cache(maxsize=512)
def grade(query: str, snippet: str) -> int | None:
    """Return a 1-10 relevance grade, or None if unavailable (caller falls back to cosine)."""
    if not JUDGE_ENABLED or not query.strip() or not snippet.strip():
        return None
    try:
        raw = _call_ollama(_PROMPT.format(query=query, snippet=snippet[:1500]))
        g = int(json.loads(raw)["grade"])
        return max(1, min(10, g))
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        return None


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "how to stream a response"
    s = sys.argv[2] if len(sys.argv) > 2 else "Use StreamingResponse to stream the body from a generator."
    print("grade:", grade(q, s), "(None = Ollama unavailable -> caller uses cosine)")
