# syntax=docker/dockerfile:1
# Build has internet (installs deps, bakes the embedding model, fetches docs).
# Runtime needs NO network: everything is baked in. Hardened: non-root, read-only vault.
ARG STACK="fastapi==0.115"

FROM python:3.12-slim
ARG STACK
WORKDIR /app
ENV FASTEMBED_CACHE_PATH=/models AEGIS_VAULT=/vault AEGIS_AUDIT_LOG=/data/audit.log
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[engine]" \
 && python -c "from fastembed import TextEmbedding; TextEmbedding()" \
 && aegis ingest "$STACK" --vault /vault \
 # non-root runtime user; /data writable for the audit log; /vault stays read-only
 && useradd --create-home --uid 10001 aegis \
 && mkdir -p /data && chown aegis:aegis /data /models \
 && chmod -R a+rX /vault

USER aegis
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://127.0.0.1:8080/health',timeout=2).status_code==200 else 1)"

# LLM judge OFF by default. Auth/identity: add --user <email> [--api-key KEY].
# Enable judge later: --llm true --llm-host http://ollama:11434 --llm-model qwen2.5:7b-instruct
CMD ["aegis", "serve", "--host", "0.0.0.0", "--port", "8080", "--vault", "/vault", "--offline"]
