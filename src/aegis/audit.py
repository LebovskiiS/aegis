"""Tamper-evident audit log (hash-chained, append-only).

Each line is a JSON object that includes `prev` = the hash of the previous line and
its own `hash` = sha256(prev + payload). Deleting or editing any line breaks the
chain, so tampering is detectable even by an insider. Use `verify()` to check it.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

GENESIS = "0" * 64


def _path() -> Path:
    return Path(os.getenv("AEGIS_AUDIT_LOG", "audit.log"))


def _digest(prev: str, payload: str) -> str:
    return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()


def _last_hash(path: Path) -> str:
    if not path.exists():
        return GENESIS
    last = ""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        return GENESIS
    try:
        return json.loads(last).get("hash", GENESIS)
    except json.JSONDecodeError:
        return GENESIS


def record(event: dict) -> None:
    """Append an event to the chain. Never raises (audit must not break serving)."""
    try:
        path = _path()
        prev = _last_hash(path)
        entry = {"ts": round(time.time(), 3), "prev": prev, **event}
        payload = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = _digest(prev, payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def verify() -> tuple[bool, int, str]:
    """Verify the whole chain. Returns (ok, n_entries, message)."""
    path = _path()
    if not path.exists():
        return True, 0, "no audit log yet"
    prev = GENESIS
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, n, f"line {i}: invalid JSON"
            stored = entry.pop("hash", None)
            if entry.get("prev") != prev:
                return False, n, f"line {i}: chain broken (prev mismatch)"
            payload = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            if _digest(prev, payload) != stored:
                return False, n, f"line {i}: entry altered (hash mismatch)"
            prev = stored
    return True, n, "chain intact"
