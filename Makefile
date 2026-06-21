# Aegis Docs — one-command front door for local dev (macOS / Linux).
#
# Quick start:
#   make install     # create .venv + install deps ([semantic])
#   make demo        # install (if needed) + index a stack + serve  ← all-in-one
#   make help        # list every target
#
# Tunable (override on the command line, e.g. `make demo STACK="pydantic==2.9"`):
PYTHON ?= python3
VENV   ?= .venv
VAULT  ?= vault
HOST   ?= 127.0.0.1
PORT   ?= 8080
STACK  ?= fastapi==0.115

AEGIS := $(VENV)/bin/aegis
URL   := http://$(HOST):$(PORT)

# Colors (disabled automatically when stdout is not a TTY).
BOLD  := \033[1m
DIM   := \033[2m
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help
.PHONY: help install demo serve ingest config locate health libs verify docker clean distclean

help: ## Show this help
	@printf "$(BOLD)🛡  Aegis Docs$(RESET) — local, air-gappable docs for AI agents\n\n"
	@printf "$(BOLD)Usage:$(RESET) make $(CYAN)<target>$(RESET)\n\n"
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  $(CYAN)%-10s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n$(DIM)Vars: STACK=$(STACK)  PORT=$(PORT)  VAULT=$(VAULT)$(RESET)\n"

# Build the venv + install the package (editable, with the semantic layer).
# Rebuilds only when pyproject.toml changes — `make install` is cheap to re-run.
$(AEGIS): pyproject.toml
	@printf "$(DIM)→ creating venv + installing deps (this runs once)$(RESET)\n"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(VENV)/bin/python -m pip install --quiet --upgrade pip
	@$(VENV)/bin/python -m pip install --quiet -e '.[server,semantic]'
	@touch $(AEGIS)
	@printf "$(GREEN)✓$(RESET) deps installed (CLI + engine: FastAPI + BM25 + embeddings)\n"

install: $(AEGIS) ## Create .venv and install all requirements
	@printf "$(GREEN)✓ ready$(RESET) — now run $(CYAN)make demo$(RESET)\n"

demo: install ## All-in-one: index a stack, then start the service
	@$(AEGIS) ingest "$(STACK)" --vault $(VAULT) >/dev/null && printf "$(GREEN)✓$(RESET) indexed $(STACK)\n"
	@printf "\n  $(BOLD)🛡  Aegis is up$(RESET) → $(CYAN)$(URL)$(RESET)\n"
	@printf "  $(DIM)in another shell: make locate q=\"how do I stream a response\" LIB=fastapi$(RESET)\n\n"
	@$(AEGIS) serve --host $(HOST) --port $(PORT) --vault $(VAULT)

serve: install ## Start the service (uses aegis.yaml if present, else defaults)
	@if [ -f aegis.yaml ]; then $(AEGIS) serve --config aegis.yaml; \
	else $(AEGIS) serve --host $(HOST) --port $(PORT) --vault $(VAULT); fi

ingest: install ## Fetch + index a stack: make ingest STACK="fastapi==0.115"
	@$(AEGIS) ingest "$(STACK)" --vault $(VAULT)

config: install ## Write an aegis.yaml config template
	@$(AEGIS) init && printf "$(DIM)edit aegis.yaml, then: make serve$(RESET)\n"

# --- client targets (talk to a running service) ---
locate: ## Query a running service: make locate q="..." [LIB=fastapi]
	@$(AEGIS) locate "$(q)" $(if $(LIB),--lib $(LIB),) --url $(URL)

health: ## Show service status + integrity
	@$(AEGIS) health --url $(URL)

libs: ## List indexed libraries
	@$(AEGIS) libs --url $(URL)

# --- compliance ---
verify: ## Verify doc signatures + the audit hash-chain
	@$(AEGIS) verify --vault $(VAULT) || true
	@$(AEGIS) audit-verify || true

# --- engine container, driven by the thin CLI (needs Docker) ---
up: install ## Pull + run the engine container (control plane)
	@$(AEGIS) up --port $(PORT)

down: install ## Stop + remove the engine container
	@$(AEGIS) down

status: install ## Show the engine container state
	@$(AEGIS) status

doctor: install ## Check Docker + image are ready
	@$(AEGIS) doctor

docker: ## Build + run via docker compose (capped, loopback, offline)
	@docker compose up --build

# --- Homebrew packaging ---
brew: ## Audit the Homebrew formula (needs brew): make brew
	@brew audit --formula --strict packaging/homebrew/aegis.rb || \
	  printf "$(DIM)install Homebrew to audit: https://brew.sh$(RESET)\n"

# --- cleanup ---
clean: ## Remove the built index (keeps fetched docs + venv)
	@rm -f $(VAULT)/chunks.jsonl $(VAULT)/meta.json $(VAULT)/manifest.signed.json
	@printf "$(GREEN)✓$(RESET) index cleaned\n"

distclean: ## Remove venv + the entire vault (full reset)
	@rm -rf $(VENV) $(VAULT)
	@printf "$(GREEN)✓$(RESET) full reset (venv + vault removed)\n"
