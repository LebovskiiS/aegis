"""The MCP server speaks the protocol: initialize + tools/list (no engine needed)."""
from __future__ import annotations

import json
import sys
import subprocess


def test_mcp_handshake_lists_the_locate_tool():
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "t", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    stdin = "".join(json.dumps(m) + "\n" for m in msgs)
    proc = subprocess.run(
        [sys.executable, "-c", "from aegis import mcp_server; mcp_server.serve()"],
        input=stdin, capture_output=True, text=True, timeout=30,
    )
    out = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]

    init = next(m for m in out if m.get("id") == 1)
    assert init["result"]["serverInfo"]["name"] == "aegis-docs"

    tools = next(m for m in out if m.get("id") == 2)
    assert any(t["name"] == "locate_docs" for t in tools["result"]["tools"])
