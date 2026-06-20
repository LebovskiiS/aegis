"""Load an aegis.yaml config and apply it as environment variables.

The whole app reads settings from env vars, so a config file simply becomes env.
Precedence: built-in defaults < config file < explicit CLI flags.
`apply()` sets env for everything the config specifies; the CLI overrides afterwards.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml


def _set(key: str, val) -> None:
    if val is not None and val != "":
        os.environ[key] = str(val)


def apply(path: str | Path) -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    s = cfg.get("server", {}) or {}
    _set("AEGIS_HOST", s.get("host"))
    _set("AEGIS_PORT", s.get("port"))
    _set("AEGIS_VAULT", s.get("vault"))
    if s.get("offline"):
        _set("AEGIS_OFFLINE", "1")
    _set("AEGIS_LOG_LEVEL", s.get("log_level"))

    stack = cfg.get("stack")
    if stack:
        _set("AEGIS_STACK", ", ".join(stack) if isinstance(stack, list) else stack)

    se = cfg.get("search", {}) or {}
    _set("AEGIS_TOP_K", se.get("top_k"))
    _set("AEGIS_SNIPPET_MAX", se.get("snippet_max"))
    _set("AEGIS_MIN_SCORE", se.get("min_score"))

    llm = cfg.get("llm", {}) or {}
    _set("AEGIS_JUDGE", "1" if llm.get("enabled") else "0")
    _set("OLLAMA_HOST", llm.get("host"))
    _set("AEGIS_JUDGE_MODEL", llm.get("model"))
    _set("AEGIS_OLLAMA_THREADS", llm.get("threads"))
    _set("AEGIS_OLLAMA_KEEP_ALIVE", llm.get("keep_alive"))
    _set("AEGIS_MIN_GRADE", llm.get("min_grade"))

    auth = cfg.get("auth", {}) or {}
    if auth.get("user") and auth.get("api_key"):
        _set("AEGIS_API_KEYS", f"{auth['user']}:{auth['api_key']}")
    elif auth.get("api_keys"):
        _set("AEGIS_API_KEYS", auth.get("api_keys"))

    prov = cfg.get("provenance", {}) or {}
    _set("AEGIS_PUBKEY", prov.get("pubkey"))

    audit = cfg.get("audit", {}) or {}
    _set("AEGIS_AUDIT_LOG", audit.get("log"))
    sink = audit.get("sink", {}) or {}
    _set("AEGIS_AUDIT_SINK", sink.get("type"))
    _set("AEGIS_AUDIT_BUCKET", sink.get("bucket"))
    _set("AEGIS_AUDIT_PREFIX", sink.get("prefix"))

    return cfg


# Canonical config template, written by `aegis init`.
EXAMPLE_CONFIG = """\
# Aegis Docs configuration. Load it with:  aegis serve --config aegis.yaml
# Generate this file with:                 aegis init
# Precedence: defaults < this file < explicit CLI flags.

server:
  host: 127.0.0.1          # bind address; use 0.0.0.0 inside a container
  port: 8080
  vault: ./vault           # where indexed docs live
  offline: false           # true = forbid all network at runtime (air-gap)
  log_level: INFO          # DEBUG | INFO | WARNING (verbose ops logging)

# Libraries to fetch + index on first start (if the vault is empty).
stack:
  - "fastapi==0.115"

search:
  top_k: 3                 # how many results /locate returns
  snippet_max: 1500        # max chars of doc text per result
  min_score: 0.35          # below this cosine score -> found:false

# Optional LLM relevance judge. OFF by default (small models grade poorly; use 7b+).
# Best run as a SEPARATE container on real hardware, not a laptop.
llm:
  enabled: false
  host: http://localhost:11434     # Ollama endpoint (a separate LLM container)
  model: qwen2.5:7b-instruct
  threads: 2               # cap CPU threads so it cannot lag the host
  keep_alive: "0"          # unload the model right after each call -> free RAM
  min_grade: 4             # below this 1-10 grade -> found:false

# Access control. If user+api_key are set, clients must send X-API-Key (else 401).
auth:
  user: ""                 # operator email -> recorded as the audit identity
  api_key: ""              # the secret clients present (generate: aegis apikey)
  # api_keys: "claude:KEY,ci:KEY"   # advanced: multiple keys

# Verify the signed provenance manifest at startup (see: aegis keygen / sign).
provenance:
  pubkey: ""               # path to the public key, e.g. aegis_pub.pem

# Tamper-evident audit log + optional shipping to long-term storage.
audit:
  log: ./audit.log
  sink:
    type: none             # none | local | s3 | gcs
    bucket: ""             # bucket name (or a directory for type: local)
    prefix: "aegis/audit/"
"""
