"""Aegis MCP server (stdio transport).

Exposes the engine's `/locate` to AI agents as a native MCP tool, so Claude
Desktop / Cursor / any MCP client can query the docs without curl. Speaks
newline-delimited JSON-RPC 2.0 over stdin/stdout (the MCP stdio transport) and
proxies tool calls to a running engine over HTTP.

Dependency-light on purpose: stdlib + httpx (already in the thin CLI), no MCP
SDK — so `aegis mcp` works straight from a Homebrew/pipx install.

Wire it into an MCP client (engine must be running, e.g. `aegis up`):
    { "mcpServers": { "aegis": { "command": "aegis", "args": ["mcp"] } } }
"""
from __future__ import annotations

import json
import os
import sys

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "aegis-docs", "version": "0.2.0"}

LOCATE_TOOL = {
    "name": "locate_docs",
    "description": (
        "Find the exact, version-pinned official documentation for a third-party "
        "library in this project's stack. Returns a pointer (file + line range) and a "
        "snippet — use it instead of guessing a library's API. Search runs locally."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "natural-language question about a library's API"},
            "lib": {"type": "string", "description": "optional library to scope to, e.g. 'fastapi'"},
            "version": {"type": "string", "description": "optional version, e.g. '0.115'"},
        },
        "required": ["query"],
    },
}


def _log(msg: str) -> None:
    # MCP stdio: stdout is the protocol channel — diagnostics MUST go to stderr.
    print(f"[aegis mcp] {msg}", file=sys.stderr, flush=True)


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _result(rid, result: dict) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "result": result})


def _error(rid, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


def _locate(url: str, args: dict) -> dict:
    """Call the engine's POST /locate and return an MCP tool result."""
    import httpx

    payload = {"query": args.get("query"), "lib": args.get("lib"), "version": args.get("version")}
    headers = {}
    if os.getenv("AEGIS_API_KEY"):
        headers["X-API-Key"] = os.environ["AEGIS_API_KEY"]
    try:
        r = httpx.post(url.rstrip("/") + "/locate", json=payload, headers=headers, timeout=180)
        r.raise_for_status()
        body = json.dumps(r.json(), ensure_ascii=False, indent=2)
        return {"content": [{"type": "text", "text": body}]}
    except httpx.HTTPError as e:
        return {
            "content": [{"type": "text", "text": f"aegis engine error at {url}: {e}. Is it running (`aegis up`)?"}],
            "isError": True,
        }


def _handle(msg: dict, url: str) -> None:
    method = msg.get("method")
    rid = msg.get("id")
    is_request = rid is not None

    if method == "initialize":
        client_proto = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        _result(rid, {
            "protocolVersion": client_proto,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "notifications/initialized":
        pass  # notification: no response
    elif method == "ping":
        _result(rid, {})
    elif method == "tools/list":
        _result(rid, {"tools": [LOCATE_TOOL]})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name != "locate_docs":
            _error(rid, -32602, f"unknown tool: {name}")
            return
        _result(rid, _locate(url, params.get("arguments") or {}))
    elif is_request:
        _error(rid, -32601, f"method not found: {method}")
    # else: unknown notification -> ignore


def serve(url: str | None = None) -> None:
    """Run the MCP server, reading JSON-RPC lines from stdin until EOF."""
    url = url or os.getenv("AEGIS_URL", "http://127.0.0.1:8080")
    _log(f"started (stdio); proxying to engine {url}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _log(f"skipping non-JSON line: {line[:80]!r}")
            continue
        try:
            _handle(msg, url)
        except Exception as e:  # noqa: BLE001 — never let one bad message kill the server
            if msg.get("id") is not None:
                _error(msg["id"], -32603, f"internal error: {e}")
            else:
                _log(f"error handling notification: {e}")
