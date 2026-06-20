"""Verbose operational logging for troubleshooting.

Separate from the tamper-evident audit log: this is *ops* logging — requests in/out,
timings, the query, the rewrite plan, search hits and errors — so you can see what
happens and where it breaks. SECRETS ARE NEVER LOGGED: API keys / auth headers are
redacted. Level via AEGIS_LOG_LEVEL (DEBUG / INFO / WARNING; default INFO).
"""
from __future__ import annotations

import logging
import os
import sys

_REDACT = {"x-api-key", "authorization", "api-key", "apikey", "cookie"}


def get_logger(name: str = "aegis") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = os.getenv("AEGIS_LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s", "%Y-%m-%dT%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level, logging.INFO))
    logger.propagate = False
    return logger


def redact_headers(headers) -> dict:
    """Return headers with any secret values masked (for debug logging)."""
    out = {}
    for k, v in headers.items():
        out[k] = "***redacted***" if k.lower() in _REDACT else v
    return out
