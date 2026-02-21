# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

B2B fitness assessment platform. Coach inputs raw test data → Python engine calculates ratings/percentiles → LLM generates narrative analysis + workout suggestions → PDF report.

Reference docs:
- `docs/architecture.md` — full technical design
- `docs/implementation-plan.md` — phase-by-phase build order (check current phase before adding features)
- `docs/poc-architecture.md` — POC-specific design details
- `docs/future-vision.md` — long-term product roadmap (12–24 months)
- `docs/business-plan.md` — business model and market strategy

## Architecture

- **Backend:** FastAPI (REST API) in `backend/app/`
- **Frontend:** Streamlit thin client in `frontend/` — calls API only, no direct imports from backend
- **LLM:** LangChain wrapping `ChatOllama` (dev) or `ChatOpenAI` (deploy) — see `backend/app/llm_service.py`
- **PDF:** WeasyPrint with Jinja2 templates in `backend/templates/`
- **Norms:** JSON lookup tables in `backend/data/norms/`
- **Config:** `pydantic-settings` in `backend/app/config.py`

### Key modules

| File | Responsibility |
|------|---------------|
| `backend/app/main.py` | FastAPI app, endpoint handlers (thin — delegate to services) |
| `backend/app/models.py` | All Pydantic schemas (`ClientProfile`, `AssessmentInput`, `MetricResult`, `LoginRequest`, `ClientRecord`, etc.) |
| `backend/app/logic.py` | Normative lookup, rating calculation, test registry |
| `backend/app/llm_service.py` | LangChain LLM abstraction, prompt loading |
| `backend/app/pdf_service.py` | WeasyPrint PDF generation |
| `backend/app/client_service.py` | Client persistence — JSON CRUD backed by `backend/data/clients.json` |
| `backend/app/prompts/` | Prompt templates (edit here, not in Python code) |
| `backend/data/norms/` | One JSON file per test |
| `backend/data/clients.json` | Persisted client records (auto-created; mounted as Docker volume `backend_data`) |

### API endpoints

```
GET  /health
POST /auth/login                → validate credentials, returns 401 on failure
GET  /clients                   → list saved client records
POST /clients                   → upsert client by name
DELETE /clients/{name}          → delete client by name
POST /assess/calculate          → logic engine returns ratings
POST /assess/generate-report    → LLM returns narrative
POST /assess/generate-pdf       → WeasyPrint returns PDF bytes
GET  /tests/battery             → test metadata
```

## Commands

Dependencies are managed with **Poetry**. Each sub-project has its own `pyproject.toml`.

```bash
# Install dependencies
cd backend && poetry install
cd frontend && poetry install

# Backend dev server
cd backend && poetry run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && poetry run streamlit run app.py --server.port 8501

# Docker (full stack)
docker compose up --build

# Run all tests
cd backend && poetry run pytest tests/ -v

# Run a single test file
cd backend && poetry run pytest tests/test_logic.py -v

# Type checking
cd backend && poetry run mypy app/ --strict

# Linting / formatting
cd backend && poetry run ruff check app/ tests/
cd backend && poetry run ruff format app/ tests/
```

### Environment variables

Copy `.env.example` → `backend/.env` for local dev (uvicorn resolves `.env` from `backend/`):

```
LLM_PROVIDER=ollama          # "ollama" or "openai"
LLM_MODEL=llama3.2           # model name
OPENAI_API_KEY=              # only needed when LLM_PROVIDER=openai
OLLAMA_BASE_URL=http://localhost:11434
COACH_USERNAME=admin         # login credentials (change before network exposure)
COACH_PASSWORD=admin
```

## Code Style

- Python 3.11+, type hints on all function signatures
- Pydantic v2 models for all data structures
- Async FastAPI endpoints (`async def`)
- f-strings over `.format()` or `%`
- Imports: stdlib → third-party → local, separated by blank lines
- Docstrings: Google style, required on all public functions
- Max line length: 88 (ruff default)
- No speculative code — every line serves an immediate, stated purpose

## Project Rules

### Separation of Concerns (CRITICAL)

- **LLM explains and suggests. It does NOT calculate.** All percentiles, ratings, and scores come from `backend/app/logic.py`. The LLM receives only pre-calculated `MetricResult` objects — never raw test scores.
- **Streamlit is a thin client.** It calls FastAPI endpoints via HTTP. It never imports backend modules directly.
- **Normative data lives in JSON files**, not hardcoded in `logic.py`.
- **Don't use LangChain for tasks that don't need it** (e.g., simple string formatting belongs in plain Python).

### LLM Guardrails (CRITICAL)

- LLM must NEVER provide medical diagnoses or legal health claims
- LLM must NEVER recommend supplements or medications
- LLM must NEVER perform calculations
- LLM must always defer to the coach's professional judgment
- System prompt enforces guardrails — see `backend/app/prompts/system_prompt.txt`. Never weaken them.

### Error Handling

- FastAPI endpoints return proper HTTP status codes with descriptive error messages
- LLM failures are caught gracefully — the report still generates with a fallback message if the LLM is unavailable

### LLM Provider Switching

- Config-driven: `LLM_PROVIDER` + `LLM_MODEL` env vars
- Dev: `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.2`
- Deploy: `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4`
- Abstracted in `llm_service.py` — never call LLM APIs directly

## Test Battery

8 tests across 4 categories. Each normalizes to 5-tier rating: Excellent → Good → Average → Below Average → Poor.

| Category | Tests |
|----------|-------|
| Strength | Push-up (reps), Wall Sit (sec), Plank (sec) |
| Flexibility | Sit-and-Reach (cm), Zipper (cm) |
| Cardio | YMCA 3-Min Step Test (BPM) |
| Body Comp | BMI (calculated), Waist-to-Hip Ratio (calculated) |

## Normative Data JSON Schema

Each file in `backend/data/norms/` follows this structure:

```json
{
  "test_name": "Push-up Test",
  "unit": "reps",
  "category": "strength",
  "source": "ACSM",
  "norms": {
    "male": {
      "20-29": {"excellent": 36, "good": 29, "average": 22, "below_average": 17, "poor": 0}
    }
  }
}
```

Rating logic: value >= threshold for that tier. Check tiers top-down (excellent first).

## Testing

**POC scope: test the logic layer only** (`backend/app/logic.py`). Do NOT write tests for LLM output, Streamlit UI, or PDF rendering during POC.

- Use `pytest` with `pytest-asyncio` for async endpoint tests
- Mock LLM responses — do not call a real LLM in unit tests
- Test files mirror source files: `logic.py` → `tests/test_logic.py`
- Tests must be pure and fast — no network calls, no file I/O
- Every normative lookup must cover:
  - At least 3 rating levels per test (low, mid, high)
  - Boundary values (edge of rating thresholds)
  - Both genders and multiple age ranges
  - Invalid/missing inputs (expect graceful errors, not crashes)

## Common Patterns

### Adding a new fitness test

1. Create `backend/data/norms/{test_name}.json` following the schema above
2. Add test metadata to the test registry in `backend/app/logic.py`
3. The generic `calculate_single_test()` handles lookup — no new logic needed unless the test requires a formula (like BMI or WHR)
4. LLM and PDF adapt automatically — they consume `MetricResult` objects

### Modifying LLM behavior

1. Edit prompt templates in `backend/app/prompts/` — not in Python code
2. Test with sample profiles before committing
3. Never weaken the medical/legal guardrails in the system prompt

## Common Patterns (continued)

### Adding / changing auth behavior

- Credentials come from `COACH_USERNAME` / `COACH_PASSWORD` env vars (read via `backend/app/config.py`)
- Never read env vars directly in Streamlit — always call `POST /auth/login`
- `require_login()` in `frontend/utils.py` guards every page — add it as the first call after imports

### Persisting client data

- All client CRUD goes through `backend/app/client_service.py` (load/upsert/delete backed by `backend/data/clients.json`)
- The frontend calls `/clients` endpoints, never writes files directly
- The `backend_data` Docker volume keeps `clients.json` across container rebuilds

## Don't

- Don't add features not in the current phase of `docs/implementation-plan.md`
- Don't install new dependencies without explicit approval
- Don't bypass the FastAPI layer from Streamlit — always go through HTTP endpoints
- Don't hardcode normative data in Python — it belongs in JSON files
- Don't let the LLM see raw test scores — only pre-calculated `MetricResult` objects
