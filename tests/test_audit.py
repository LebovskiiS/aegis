"""The tamper-evident audit log must catch any edit to the chain."""
from __future__ import annotations

import json


def test_audit_chain_intact_then_detects_tampering(tmp_path, monkeypatch):
    log = tmp_path / "audit.log"
    monkeypatch.setenv("AEGIS_AUDIT_LOG", str(log))
    from aegis import audit

    for i in range(3):
        audit.record({"event": "locate", "q": f"q{i}"})

    ok, n, _ = audit.verify()
    assert ok and n == 3, "freshly written chain must verify"

    # Edit one entry in place — the hash chain must break.
    lines = log.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[1])
    entry["q"] = "HACKED"
    lines[1] = json.dumps(entry)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok2, _, _ = audit.verify()
    assert not ok2, "editing a logged entry must be detected"
