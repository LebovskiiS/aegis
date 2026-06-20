# syntax=docker/dockerfile:1
# Build has internet (installs deps, bakes the embedding model, fetches docs).
# At runtime the container needs NO network: everything is baked in.
ARG STACK="fastapi==0.115"

FROM python:3.12-slim
ARG STACK
WORKDIR /app
# Embedding model + vault baked into the image so runtime is offline.
ENV FASTEMBED_CACHE_PATH=/models AEGIS_VAULT=/vault
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[semantic]" \
 && python -c "from fastembed import TextEmbedding; TextEmbedding()" \
 && aegis ingest "$STACK" --vault /vault

EXPOSE 8080
# LLM judge is OFF by default (BM25 + embeddings + the calling agent do the work).
# Enable later by pointing at a separate LLM container:
#   aegis serve --llm true --llm-host http://ollama:11434 --llm-model qwen2.5:7b-instruct
# Restrict host exposure: docker run -p 127.0.0.1:8080:8080 aegis-docs
# True air-gap: docker run --network none ... (docs + model are already inside)
CMD ["aegis", "serve", "--host", "0.0.0.0", "--port", "8080", "--vault", "/vault", "--offline"]
