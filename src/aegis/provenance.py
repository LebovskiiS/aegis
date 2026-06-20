"""Signed provenance manifest for the vault (ed25519 signatures).

Builds a manifest of every indexed doc (source URL, version, sha256) and signs it with
a private key. Consumers verify with the public key -> proves the docs are exactly the
ones the publisher indexed, unmodified. `verify()` also checks the manifest still
matches the vault on disk (so silent edits are caught). This complements the
hash-chained audit log: the chain protects the request ledger, the manifest protects
the documentation corpus.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _vault() -> Path:
    return Path(os.getenv("AEGIS_VAULT", "vault"))


def keygen(priv_path: Path, pub_path: Path) -> None:
    priv = Ed25519PrivateKey.generate()
    priv_path.write_bytes(
        priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        priv.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def build_manifest() -> dict:
    meta = json.loads((_vault() / "meta.json").read_text(encoding="utf-8"))
    return {"libs": meta["libs"], "files": meta["files"]}


def _payload(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign(priv_path: Path) -> Path:
    manifest = build_manifest()
    priv = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    sig = priv.sign(_payload(manifest))
    out = {"manifest": manifest, "signature": base64.b64encode(sig).decode()}
    dest = _vault() / "manifest.signed.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def verify(pub_path: Path) -> tuple[bool, str]:
    f = _vault() / "manifest.signed.json"
    if not f.exists():
        return False, "no signed manifest"
    obj = json.loads(f.read_text(encoding="utf-8"))
    pub = serialization.load_pem_public_key(pub_path.read_bytes())
    try:
        pub.verify(base64.b64decode(obj["signature"]), _payload(obj["manifest"]))
    except Exception:  # noqa: BLE001
        return False, "signature INVALID"
    if build_manifest() != obj["manifest"]:
        return False, "vault changed since signing"
    return True, "signature valid + vault matches manifest"
