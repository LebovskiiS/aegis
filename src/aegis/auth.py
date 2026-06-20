"""Optional API-key auth + caller identity.

If AEGIS_API_KEYS is set (comma-separated `label:key` or bare `key` items), protected
endpoints require a matching `X-API-Key` header; the matched label becomes the
identity written to the audit log. If unset, auth is disabled (local dev) -> "anon".
Keys themselves are never logged.
"""
from __future__ import annotations

import os

from fastapi import Header, HTTPException


def _keys() -> dict[str, str]:
    out: dict[str, str] = {}
    for part in os.getenv("AEGIS_API_KEYS", "").split(","):
        part = part.strip()
        if not part:
            continue
        label, key = part.split(":", 1) if ":" in part else ("client", part)
        out[key.strip()] = label.strip()
    return out


def identity(x_api_key: str | None = Header(default=None)) -> str:
    """FastAPI dependency: returns the caller's label, or 401 if a key is required/invalid."""
    keys = _keys()
    if not keys:
        return "anon"  # auth disabled (local/dev)
    if x_api_key and x_api_key in keys:
        return keys[x_api_key]
    raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")
