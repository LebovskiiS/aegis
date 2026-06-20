"""Aegis Docs CLI.

Usage:
  aegis serve  [--port 8080] [--llm true|false] [--llm-host URL] [--threads N]
               [--stack "fastapi==0.115"] [--vault DIR] [--offline]
  aegis ingest "fastapi==0.115" [--vault DIR]
  aegis locate "how to stream a response" [--lib fastapi] [--url ...]
  aegis add fastapi [--version 0.115] [--url ...]
  aegis health [--url ...]
  aegis libs   [--url ...]

`serve`/`ingest` run in-process; `locate`/`add`/`health`/`libs` talk to a running
service over HTTP (so users interact with the program through a simple CLI).
"""
from __future__ import annotations

import argparse
import json
import os

DEFAULT_URL = os.getenv("AEGIS_URL", "http://127.0.0.1:8080")


def _bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _serve(a: argparse.Namespace) -> None:
    os.environ.setdefault("AEGIS_VAULT", a.vault)
    os.environ["AEGIS_JUDGE"] = "1" if a.llm else "0"  # the --llm true/false toggle
    if a.llm_host:
        os.environ["OLLAMA_HOST"] = a.llm_host  # point at a separate LLM container
    if a.llm_model:
        os.environ["AEGIS_JUDGE_MODEL"] = a.llm_model
    if a.threads:
        os.environ["AEGIS_OLLAMA_THREADS"] = str(a.threads)
    if a.offline:
        os.environ["AEGIS_OFFLINE"] = "1"
    if a.stack:
        os.environ["AEGIS_STACK"] = a.stack
    import uvicorn

    mode = f"LLM judge ON ({os.environ.get('AEGIS_JUDGE_MODEL', 'default')})" if a.llm else "no LLM (cosine + agent)"
    print(f"aegis serve -> http://{a.host}:{a.port}  [{mode}]")
    uvicorn.run("aegis.app:app", host=a.host, port=a.port, log_level="warning")


def _ingest(a: argparse.Namespace) -> None:
    os.environ.setdefault("AEGIS_VAULT", a.vault)
    from aegis import ingest

    meta = ingest.ingest(ingest.parse_stack(a.stack))
    print(json.dumps(meta, indent=2, ensure_ascii=False))


def _call(url: str, method: str, path: str, payload: dict | None = None) -> None:
    import httpx

    try:
        r = httpx.request(method, url.rstrip("/") + path, json=payload, timeout=180)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except httpx.HTTPError as e:
        raise SystemExit(f"error talking to {url}: {e}. Is `aegis serve` running?")


def _locate(a):
    _call(a.url, "POST", "/locate", {"query": a.query, "lib": a.lib, "version": a.version})


def _add(a):
    _call(a.url, "POST", "/add", {"lib": a.lib, "version": a.version})


def _health(a):
    _call(a.url, "GET", "/health")


def _libs(a):
    _call(a.url, "GET", "/libs")


def main() -> None:
    p = argparse.ArgumentParser(prog="aegis", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the HTTP service")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--llm", type=_bool, default=False, metavar="true|false",
                   help="enable the LLM judge (default false). Needs a 7b+ model.")
    s.add_argument("--llm-host", default=None, help="external Ollama URL (separate LLM container)")
    s.add_argument("--llm-model", default=None, help="judge model, e.g. qwen2.5:7b-instruct")
    s.add_argument("--threads", type=int, default=None, help="cap model CPU threads")
    s.add_argument("--stack", default=None, help="index this stack on first start")
    s.add_argument("--vault", default="vault")
    s.add_argument("--offline", action="store_true", help="forbid network at runtime (air-gap)")
    s.set_defaults(func=_serve)

    i = sub.add_parser("ingest", help="fetch + index a stack")
    i.add_argument("stack", help='e.g. "fastapi==0.115, pydantic==2.9"')
    i.add_argument("--vault", default="vault")
    i.set_defaults(func=_ingest)

    l = sub.add_parser("locate", help="query docs via a running service")
    l.add_argument("query")
    l.add_argument("--lib", default=None)
    l.add_argument("--version", default=None)
    l.add_argument("--url", default=DEFAULT_URL)
    l.set_defaults(func=_locate)

    a_ = sub.add_parser("add", help="fetch + index a library on a running service")
    a_.add_argument("lib")
    a_.add_argument("--version", default="latest")
    a_.add_argument("--url", default=DEFAULT_URL)
    a_.set_defaults(func=_add)

    for name, fn, hl in [("health", _health, "service status"), ("libs", _libs, "list indexed libraries")]:
        c = sub.add_parser(name, help=hl)
        c.add_argument("--url", default=DEFAULT_URL)
        c.set_defaults(func=fn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
