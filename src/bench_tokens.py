"""
Token-cost benchmark: reading a whole doc page (what an agent does on its own,
e.g. via web fetch) vs an Aegis Docs snippet/pointer for the same question.

Token estimate is rough (~4 chars/token) and labeled as an estimate.

Run:
  python bench_tokens.py
  BENCH_DOC=<url> BENCH_QUERY="..." python bench_tokens.py
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import httpx

DOC_URL = os.getenv(
    "BENCH_DOC", "https://raw.githubusercontent.com/tiangolo/fastapi/master/README.md"
)
QUERY = os.getenv(
    "BENCH_QUERY",
    "how do I declare a request body with a Pydantic model and read path and query parameters",
)


def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)  # rough: ~4 chars per token


# 1) Fetch a real documentation page (this is what an agent would pull into context).
doc = httpx.get(DOC_URL, timeout=20, follow_redirects=True).text

# 2) Point Aegis at a fresh temp vault and index this doc.
tmp = Path(tempfile.mkdtemp())
os.environ["AEGIS_VAULT"] = str(tmp)
import ingest  # noqa: E402  (after AEGIS_VAULT is set)
import index  # noqa: E402

(tmp / "lib" / "v").mkdir(parents=True)
(tmp / "lib" / "v" / "doc.md").write_text(doc, encoding="utf-8")
chunks = []
for cid, ch in enumerate(ingest.chunk_markdown(doc)):
    ch.update({"id": cid, "lib": "lib", "version": "v", "file": "lib/v/doc.md", "source": DOC_URL})
    chunks.append(ch)
(tmp / "chunks.jsonl").write_text("\n".join(json.dumps(c) for c in chunks), encoding="utf-8")
(tmp / "meta.json").write_text(json.dumps({"libs": [], "files": {}}), encoding="utf-8")

idx = index.Index().load()
hits = idx.search({"vector_query": QUERY, "keywords": [], "lib": None, "version": None}, top_k=1)
top = hits[0]
snippet = top["text"]
pointer = json.dumps(
    {"file": top["file"], "lines": f'{top["start_line"]}-{top["end_line"]}', "anchor": top["anchor"]}
)

# 3) Compare.
doc_t, snip_t, ptr_t = est_tokens(doc), est_tokens(snippet), est_tokens(pointer)
print(f"Query : {QUERY}")
print(f"Doc   : {DOC_URL}")
print(f"Chunks indexed: {len(chunks)} | vectors: {idx.has_vectors}")
print("-" * 70)
print(f"SELF (read whole page) : {len(doc):>7} chars  ~ {doc_t:>6} tokens")
print(f"AEGIS snippet          : {len(snippet):>7} chars  ~ {snip_t:>6} tokens   [{top['anchor']}]")
print(f"AEGIS pointer only     : {len(pointer):>7} chars  ~ {ptr_t:>6} tokens")
print("-" * 70)
print(f"=> snippet uses ~{doc_t / snip_t:.0f}x fewer tokens than reading the whole page")
print(f"=> pointer uses ~{doc_t / ptr_t:.0f}x fewer tokens (agent then reads only those lines)")
