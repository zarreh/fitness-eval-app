.PHONY: install install-backend install-frontend \
        backend frontend \
        test test-v lint format typecheck check \
        docker-up docker-up-d docker-down docker-pull-model docker-logs \
        env clean

BACKEND  := backend
FRONTEND := frontend

# ── Setup ─────────────────────────────────────────────────────────────────────

install: install-backend install-frontend   ## Install all dependencies

install-backend:                            ## Install backend dependencies
	cd $(BACKEND) && poetry install

install-frontend:                           ## Install frontend dependencies
	cd $(FRONTEND) && poetry install

env:                                        ## Copy .env.example → backend/.env (safe, won't overwrite)
	@if [ ! -f $(BACKEND)/.env ]; then \
		cp .env.example $(BACKEND)/.env; \
		echo "Created $(BACKEND)/.env — fill in your values."; \
	else \
		echo "$(BACKEND)/.env already exists, skipping."; \
	fi

# ── Run ───────────────────────────────────────────────────────────────────────

backend:                                    ## Start the FastAPI dev server (port 8000)
	cd $(BACKEND) && poetry run uvicorn app.main:app --reload --port 8000

frontend:                                   ## Start the Streamlit dev server (port 8501)
	cd $(FRONTEND) && poetry run streamlit run app.py --server.port 8501

# ── Tests ─────────────────────────────────────────────────────────────────────

test:                                       ## Run all tests
	cd $(BACKEND) && poetry run pytest tests/ -v

test-q:                                     ## Run all tests (quiet)
	cd $(BACKEND) && poetry run pytest tests/ -q

# Usage: make test-one FILE=tests/test_logic.py
test-one:                                   ## Run a single test file: make test-one FILE=tests/test_logic.py
	cd $(BACKEND) && poetry run pytest $(FILE) -v

# ── Code quality ──────────────────────────────────────────────────────────────

lint:                                       ## Check for linting issues (ruff)
	cd $(BACKEND) && poetry run ruff check app/ tests/

format:                                     ## Auto-format code (ruff)
	cd $(BACKEND) && poetry run ruff format app/ tests/

format-check:                               ## Check formatting without applying (CI-safe)
	cd $(BACKEND) && poetry run ruff format app/ tests/ --check

typecheck:                                  ## Run strict type checking (mypy)
	cd $(BACKEND) && poetry run mypy app/ --strict

check: lint format-check typecheck test     ## Run all quality checks (lint + format + types + tests)

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:                                  ## Build and start all services (foreground)
	docker compose up --build

docker-up-d:                                ## Build and start all services (detached)
	docker compose up --build -d

docker-down:                                ## Stop all services
	docker compose down

docker-pull-model:                          ## Pull llama3.2 into the running Ollama container (first run)
	docker compose exec ollama ollama pull llama3.2

docker-logs:                                ## Follow logs for all services
	docker compose logs -f

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:                                      ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null || true

help:                                       ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
