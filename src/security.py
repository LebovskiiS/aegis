"""
Input hardening for Aegis Docs.

The `query` string flows into local-LLM prompts (rewriter, judge), so it is
untrusted and a prompt-injection vector. Defenses, layered:
  1. Strict request validation (length + charset) -> reject junk early (HTTP 422).
  2. Sanitize the query (strip control chars, collapse whitespace) before use.
  3. Prompts wrap the query in tags and instruct the model to treat it as data.
  4. Outputs are clamped/validated (grade in 1-10, plan schema) -> tiny blast radius.
  5. No egress + no tools exposed to the local LLM -> nothing to exfiltrate even if tricked.

This module covers (1) and (2); (3)-(5) live in the prompts/handlers.
"""
from __future__ import annotations

import re

MAX_QUERY_LEN = 500
LIB_PATTERN = r"^[A-Za-z0-9._-]+$"
VERSION_PATTERN = r"^[A-Za-z0-9._-]+$"

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_query(q: str) -> str:
    """Strip control characters, collapse whitespace, cap length."""
    q = _CONTROL.sub(" ", q)
    q = " ".join(q.split())
    return q[:MAX_QUERY_LEN].strip()
