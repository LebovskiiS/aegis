"""Integration: the core promise — index docs, then locate the right section."""
from __future__ import annotations


def test_ingest_then_locate_finds_the_right_section(vault):
    path, ingest, index = vault
    ingest.ingest(ingest.parse_stack("fastapi==0.115"))

    idx = index.Index().load()
    hits = idx.search(
        {"vector_query": "how do I stream a response", "keywords": ["stream"],
         "lib": "fastapi", "version": None},
        top_k=3,
    )

    assert hits, "locate returned no results"
    anchors = [h["anchor"] for h in hits]
    assert any("StreamingResponse" in a for a in anchors), anchors


def test_integrity_detects_a_tampered_doc(vault):
    path, ingest, _ = vault
    ingest.ingest(ingest.parse_stack("fastapi==0.115"))

    assert ingest.verify_integrity() == []  # clean right after indexing

    doc = next(path.glob("fastapi/*/doc.md"))
    doc.write_text(doc.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    assert ingest.verify_integrity(), "a modified doc must be flagged by the sha256 check"
