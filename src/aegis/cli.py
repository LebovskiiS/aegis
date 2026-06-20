"""Aegis Docs CLI.

Setup:
  aegis init                                   # write an aegis.yaml config template
  aegis serve --config aegis.yaml              # run with all settings from the file
  aegis ingest "fastapi==0.115" [--vault DIR]  # fetch + index docs

Service flags (override the config):
  aegis serve [--port N] [--llm true|false] [--llm-host URL] [--threads N]
              [--vault DIR] [--offline] [--user EMAIL] [--api-key KEY]
              [--pubkey aegis_pub.pem] [--log-level DEBUG]

Client (talks to a running service over HTTP):
  aegis locate "how to stream a response" [--lib fastapi] [--url ...] [--api-key KEY]
  aegis add fastapi [--version 0.115] [--api-key KEY]
  aegis health | aegis libs   [--url ...]

Compliance:
  aegis keygen / sign / verify          # ed25519 signed manifest
  aegis audit-verify [--log audit.log]  # check the hash-chain
  aegis audit-ship  [--config ...]      # ship the audit log to a bucket
  aegis apikey                          # generate a random API key
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

DEFAULT_URL = os.getenv("AEGIS_URL", "http://127.0.0.1:8080")


def _bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _serve(a: argparse.Namespace) -> None:
    if a.config:
        from aegis import config

        config.apply(a.config)
    # CLI flags override the config (only when explicitly provided)
    if a.vault:
        os.environ["AEGIS_VAULT"] = a.vault
    os.environ.setdefault("AEGIS_VAULT", "vault")
    if a.llm is not None:
        os.environ["AEGIS_JUDGE"] = "1" if a.llm else "0"
    if a.llm_host:
        os.environ["OLLAMA_HOST"] = a.llm_host
    if a.llm_model:
        os.environ["AEGIS_JUDGE_MODEL"] = a.llm_model
    if a.threads:
        os.environ["AEGIS_OLLAMA_THREADS"] = str(a.threads)
    if a.offline:
        os.environ["AEGIS_OFFLINE"] = "1"
    if a.stack:
        os.environ["AEGIS_STACK"] = a.stack
    if a.user:
        key = a.api_key or secrets.token_urlsafe(32)
        os.environ["AEGIS_API_KEYS"] = f"{a.user}:{key}"
        if not a.api_key:
            print(f"auth: user={a.user}\n      API key (clients send as X-API-Key): {key}")
    elif a.api_keys:
        os.environ["AEGIS_API_KEYS"] = a.api_keys
    if a.pubkey:
        os.environ["AEGIS_PUBKEY"] = a.pubkey
    if a.log_level:
        os.environ["AEGIS_LOG_LEVEL"] = a.log_level

    host = a.host or os.getenv("AEGIS_HOST", "127.0.0.1")
    port = a.port or int(os.getenv("AEGIS_PORT", "8080"))
    import uvicorn

    judge = os.environ.get("AEGIS_JUDGE", "0") not in ("0", "false", "False")
    mode = f"LLM judge ON ({os.environ.get('AEGIS_JUDGE_MODEL', 'default')})" if judge else "no LLM (cosine + agent)"
    print(f"aegis serve -> http://{host}:{port}  [{mode}]")
    uvicorn.run("aegis.app:app", host=host, port=port, log_level="warning")


def _init(a: argparse.Namespace) -> None:
    from aegis import config

    out = Path(a.out)
    if out.exists() and not a.force:
        raise SystemExit(f"{out} already exists (use --force to overwrite)")
    out.write_text(config.EXAMPLE_CONFIG, encoding="utf-8")
    print(f"wrote {out}. Edit it, then: aegis serve --config {out}")


def _ingest(a: argparse.Namespace) -> None:
    os.environ.setdefault("AEGIS_VAULT", a.vault)
    from aegis import ingest

    print(json.dumps(ingest.ingest(ingest.parse_stack(a.stack)), indent=2, ensure_ascii=False))


def _call(url: str, method: str, path: str, payload: dict | None, api_key: str | None) -> None:
    import httpx

    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        r = httpx.request(method, url.rstrip("/") + path, json=payload, headers=headers, timeout=180)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except httpx.HTTPError as e:
        raise SystemExit(f"error talking to {url}: {e}. Is `aegis serve` running?")


def _locate(a):
    _call(a.url, "POST", "/locate", {"query": a.query, "lib": a.lib, "version": a.version}, a.api_key)


def _add(a):
    _call(a.url, "POST", "/add", {"lib": a.lib, "version": a.version}, a.api_key)


def _health(a):
    _call(a.url, "GET", "/health", None, None)


def _libs(a):
    _call(a.url, "GET", "/libs", None, None)


def _keygen(a):
    from aegis import provenance

    provenance.keygen(Path(a.priv), Path(a.pub))
    print(f"private key -> {a.priv} (keep secret!)\npublic key  -> {a.pub}")


def _sign(a):
    os.environ.setdefault("AEGIS_VAULT", a.vault)
    from aegis import provenance

    print(f"signed manifest -> {provenance.sign(Path(a.priv))}")


def _verify(a):
    os.environ.setdefault("AEGIS_VAULT", a.vault)
    from aegis import provenance

    ok, msg = provenance.verify(Path(a.pub))
    print(("OK: " if ok else "FAIL: ") + msg)
    raise SystemExit(0 if ok else 1)


def _audit_verify(a):
    os.environ["AEGIS_AUDIT_LOG"] = a.log
    from aegis import audit

    ok, n, msg = audit.verify()
    print(f"{'OK' if ok else 'FAIL'}: {msg} ({n} entries)")
    raise SystemExit(0 if ok else 1)


def _audit_ship(a):
    if a.config:
        from aegis import config

        config.apply(a.config)
    from aegis import audit_sink

    print(audit_sink.ship())


def _apikey(a):
    print(secrets.token_urlsafe(32))


def main() -> None:
    p = argparse.ArgumentParser(prog="aegis", description="Aegis Docs — local docs for AI agents")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init", help="write an aegis.yaml config template")
    ini.add_argument("--out", default="aegis.yaml")
    ini.add_argument("--force", action="store_true")
    ini.set_defaults(func=_init)

    s = sub.add_parser("serve", help="run the HTTP service")
    s.add_argument("--config", default=None, help="path to aegis.yaml")
    s.add_argument("--host", default=None)
    s.add_argument("--port", type=int, default=None)
    s.add_argument("--llm", type=_bool, default=None, metavar="true|false", help="enable the LLM judge")
    s.add_argument("--llm-host", default=None, help="external Ollama URL (separate LLM container)")
    s.add_argument("--llm-model", default=None)
    s.add_argument("--threads", type=int, default=None, help="cap model CPU threads")
    s.add_argument("--stack", default=None, help="index this stack on first start")
    s.add_argument("--vault", default=None)
    s.add_argument("--offline", action="store_true", help="forbid network at runtime (air-gap)")
    s.add_argument("--user", default=None, help="operator email -> bound to an API key; logged as identity")
    s.add_argument("--api-key", default=None, help="explicit API key for --user (else auto-generated)")
    s.add_argument("--api-keys", default=None, help='advanced: multiple keys "claude:KEY,ci:KEY"')
    s.add_argument("--pubkey", default=None, help="verify the signed manifest with this public key")
    s.add_argument("--log-level", default=None, help="DEBUG / INFO / WARNING")
    s.set_defaults(func=_serve)

    i = sub.add_parser("ingest", help="fetch + index a stack")
    i.add_argument("stack")
    i.add_argument("--vault", default="vault")
    i.set_defaults(func=_ingest)

    l = sub.add_parser("locate", help="query docs via a running service")
    l.add_argument("query")
    l.add_argument("--lib", default=None)
    l.add_argument("--version", default=None)
    l.add_argument("--url", default=DEFAULT_URL)
    l.add_argument("--api-key", default=os.getenv("AEGIS_API_KEY"))
    l.set_defaults(func=_locate)

    ad = sub.add_parser("add", help="fetch + index a library on a running service")
    ad.add_argument("lib")
    ad.add_argument("--version", default="latest")
    ad.add_argument("--url", default=DEFAULT_URL)
    ad.add_argument("--api-key", default=os.getenv("AEGIS_API_KEY"))
    ad.set_defaults(func=_add)

    for name, fn, hl in [("health", _health, "service status"), ("libs", _libs, "list indexed libs")]:
        c = sub.add_parser(name, help=hl)
        c.add_argument("--url", default=DEFAULT_URL)
        c.set_defaults(func=fn)

    kg = sub.add_parser("keygen", help="generate an ed25519 signing keypair")
    kg.add_argument("--priv", default="aegis_priv.pem")
    kg.add_argument("--pub", default="aegis_pub.pem")
    kg.set_defaults(func=_keygen)

    sg = sub.add_parser("sign", help="sign the vault manifest")
    sg.add_argument("--priv", default="aegis_priv.pem")
    sg.add_argument("--vault", default="vault")
    sg.set_defaults(func=_sign)

    vf = sub.add_parser("verify", help="verify the signed manifest + vault")
    vf.add_argument("--pub", default="aegis_pub.pem")
    vf.add_argument("--vault", default="vault")
    vf.set_defaults(func=_verify)

    av = sub.add_parser("audit-verify", help="verify the audit log hash-chain")
    av.add_argument("--log", default="audit.log")
    av.set_defaults(func=_audit_verify)

    sh = sub.add_parser("audit-ship", help="ship the audit log to a bucket")
    sh.add_argument("--config", default=None, help="path to aegis.yaml (for the sink config)")
    sh.set_defaults(func=_audit_ship)

    ak = sub.add_parser("apikey", help="generate a random API key")
    ak.set_defaults(func=_apikey)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
