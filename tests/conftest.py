"""Shared pytest fixtures."""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """A fresh, offline vault bound to a temp dir.

    Returns (path, ingest, index). AEGIS_OFFLINE=1 makes ingest use the bundled
    sample docs, so tests need no network. The modules read AEGIS_VAULT at import
    time, so we reload them after pointing it at tmp_path.
    """
    monkeypatch.setenv("AEGIS_VAULT", str(tmp_path))
    monkeypatch.setenv("AEGIS_OFFLINE", "1")
    from aegis import index, ingest

    importlib.reload(ingest)
    importlib.reload(index)
    return tmp_path, ingest, index
