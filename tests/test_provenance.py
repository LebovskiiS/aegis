"""Signed provenance: a valid signature verifies; a changed vault fails."""
from __future__ import annotations

import json


def test_sign_verify_roundtrip_then_detect_vault_change(vault, tmp_path):
    path, ingest, _ = vault
    ingest.ingest(ingest.parse_stack("fastapi==0.115"))
    from aegis import provenance

    priv, pub = tmp_path / "priv.pem", tmp_path / "pub.pem"
    provenance.keygen(priv, pub)
    provenance.sign(priv)

    ok, _ = provenance.verify(pub)
    assert ok, "a freshly signed vault must verify"

    # Flip a recorded file hash -> manifest no longer matches the signed one.
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    some_file = next(iter(meta["files"]))
    meta["files"][some_file] = "0" * 64
    (path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    ok2, _ = provenance.verify(pub)
    assert not ok2, "a changed vault must fail signature verification"
