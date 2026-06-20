# syntax=docker/dockerfile:1

# ---------- Stage 1: builder (HAS internet) — fetch docs + build the vault ----------
FROM python:3.12-slim AS builder
WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
# Stack is baked at build time. Override: docker build --build-arg STACK="fastapi==0.115, ..."
ARG STACK="fastapi==0.115"
RUN AEGIS_VAULT=/vault python src/ingest.py "$STACK"

# ---------- Stage 2: runtime (air-gap) — serve only, no network needed ----------
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY --from=builder /vault /vault
ENV AEGIS_VAULT=/vault AEGIS_OFFLINE=1
EXPOSE 8080
# Bind 0.0.0.0 inside the container; restrict exposure from the host instead, e.g.:
#   docker run -p 127.0.0.1:8080:8080 aegis-docs
# For true air-gap, run with no outbound network, e.g.: docker run --network none ...
CMD ["uvicorn", "app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]
