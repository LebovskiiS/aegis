"""Hybrid index: BM25 (SQLite FTS5, built-in) + vector (fastembed, optional) -> RRF.

Degrades gracefully: if fastembed is not installed, runs in BM25-only mode.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sqlite3
import threading
from pathlib import Path

VAULT = Path(os.getenv("AEGIS_VAULT", "vault"))

try:  # semantic layer is optional
    import numpy as np
    from fastembed import TextEmbedding

    _HAS_VEC = True
except Exception:  # noqa: BLE001
    _HAS_VEC = False


class Index:
    def __init__(self) -> None:
        self.chunks: list[dict] = []
        self.libs: list[str] = []
        self.con: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self.embed_model = None
        self.vectors = None

    def load(self) -> "Index":
        path = VAULT / "chunks.jsonl"
        self.chunks = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        self.libs = sorted({c["lib"] for c in self.chunks})
        # BM25 via FTS5 (rowid = id+1). check_same_thread=False: FastAPI calls from a threadpool.
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        self.con.execute("CREATE VIRTUAL TABLE chunks USING fts5(text)")
        self.con.executemany(
            "INSERT INTO chunks(rowid, text) VALUES (?, ?)",
            [(c["id"] + 1, c["text"]) for c in self.chunks],
        )
        # Vectors (if available)
        if _HAS_VEC:
            self.embed_model = TextEmbedding()
            embs = list(self.embed_model.embed([c["text"] for c in self.chunks]))
            self.vectors = np.array(embs, dtype="float32")
        return self

    @property
    def has_vectors(self) -> bool:
        return _HAS_VEC and self.vectors is not None

    def _bm25(self, fts_query: str, k: int) -> list[int]:
        if not fts_query or self.con is None:
            return []
        try:
            with self._lock:
                cur = self.con.execute(
                    "SELECT rowid FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
                    (fts_query, k),
                )
                return [rowid - 1 for (rowid,) in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    def _vec(self, query: str, k: int) -> list[int]:
        if not self.has_vectors:
            return []
        q = np.array(list(self.embed_model.embed([query]))[0], dtype="float32")
        norms = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(q) + 1e-9
        sims = (self.vectors @ q) / norms
        return list(np.argsort(-sims)[:k])

    @staticmethod
    def _rrf(rank_lists: list[list[int]], kconst: int = 60) -> list[int]:
        scores: dict[int, float] = {}
        for ranks in rank_lists:
            for rank, idx in enumerate(ranks):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (kconst + rank)
        return [idx for idx, _ in sorted(scores.items(), key=lambda x: -x[1])]

    def _resolve_lib(self, lib: str | None) -> str | None:
        """Normalize case + fix typos against indexed libraries.
        'FastAPI'/'FASTAPI' -> 'fastapi', 'fastpi' -> 'fastapi'."""
        if not lib:
            return None
        lib = lib.strip().lower()
        if lib in self.libs:
            return lib
        match = difflib.get_close_matches(lib, self.libs, n=1, cutoff=0.6)
        return match[0] if match else lib

    def search(self, plan: dict, top_k: int = 3, pool: int = 10) -> list[dict]:
        kws = plan.get("keywords") or re.findall(r"[A-Za-z_][A-Za-z0-9_]+", plan["vector_query"])
        terms = [re.sub(r"[^A-Za-z0-9_]", "", w) for w in kws]
        terms = [t for t in terms if len(t) >= 2]
        fts_q = " OR ".join(f"{t}*" for t in terms)  # prefixes -> tolerant to case and suffixes
        bm = self._bm25(fts_q, pool)
        ve = self._vec(plan["vector_query"], pool)
        fused = self._rrf([bm, ve])

        want_lib = self._resolve_lib(plan.get("lib"))
        want_ver = plan.get("version")
        results: list[dict] = []
        for idx in fused:
            c = self.chunks[idx]
            if want_lib and c["lib"] != want_lib:
                continue
            if want_ver and want_ver != "latest" and c["version"] != want_ver:
                continue
            results.append(c)
            if len(results) >= top_k:
                break
        return results
