# GitHub Copilot Instructions — Fitness Evaluation App

## Project Overview
**Phase: POC** — B2B fitness assessment platform. Coach inputs raw test scores → Python logic engine calculates ratings from normative tables → LLM drafts narrative analysis → coach downloads branded PDF report.

## Architecture

| Layer | Tech | Location |
|-------|------|----------|
| Backend API | FastAPI + Uvicorn | `backend/app/` |
| Frontend | Streamlit (thin client) | `frontend/app.py` |
| LLM | LangChain (Ollama dev / OpenAI prod) | `backend/app/llm_service.py` |
| PDF | WeasyPrint + Jinja2 | `backend/app/pdf_service.py`, `backend/templates/` |
| Normative data | JSON files loaded at startup | `backend/data/norms/*.json` |
| Config | `pydantic-settings` | `backend/app/config.py` |

## Data Flow
```
POST /assess/calculate      → logic.py returns List[MetricResult]
POST /assess/generate-report → llm_service.py returns narrative (receives MetricResult only)
POST /assess/generate-pdf    → pdf_service.py returns PDF bytes
```

## Code Style
- Python 3.11+, type hints on all signatures, Google-style docstrings on public functions
- Pydantic v2 models for all request/response shapes — defined in `backend/app/models.py`
- `async def` FastAPI endpoints; keep handlers thin, delegate to service modules
- f-strings; imports: stdlib → third-party → local; max line length 88 (ruff)
- Naming: `snake_case` files/functions/vars, `PascalCase` classes, `snake_case_norms.json` data files

## Normative Data Schema (`backend/data/norms/*.json`)
```json
{
  "test_name": "Push-up Test", "unit": "reps", "category": "strength", "source": "ACSM",
  "norms": {
    "male": { "20-29": {"excellent": 36, "good": 29, "average": 22, "below_average": 17, "poor": 0} }
  }
}
```
Rating lookup: check tiers top-down (excellent first); `value >= threshold` wins. The generic `calculate_single_test()` in `logic.py` handles all lookups — only add custom logic for formula-based tests (BMI, waist-to-hip ratio).

## Critical Rules
- **LLM never calculates.** It receives pre-computed `MetricResult` objects and generates explanations only.
- **LLM never gives medical/legal advice.** Guardrails live in `backend/app/prompts/system_prompt.txt` — never weaken them.
- **Streamlit never imports backend modules.** All data operations go through HTTP endpoints.
- **No speculative code.** Only build what's in the current POC phase (`docs/implementation-plan.md`).
- **LLM provider is config-driven** — never hardcode. Switch via `LLM_PROVIDER=ollama|openai`.

## Build & Test Commands
Dependencies managed with Poetry (`backend/pyproject.toml`, `frontend/pyproject.toml`).
```bash
# Install
cd backend && poetry install
cd frontend && poetry install

# Backend dev server
cd backend && poetry run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && poetry run streamlit run app.py --server.port 8501

# Full stack
docker compose up --build

# Tests (logic layer only in POC)
cd backend && poetry run pytest tests/ -v

# Lint / format
cd backend && poetry run ruff check app/ tests/
cd backend && poetry run ruff format app/ tests/

# Type check
cd backend && poetry run mypy app/ --strict
```

## Testing Scope (POC)
Tests cover `backend/app/logic.py` only — no LLM, UI, or PDF tests. Each normative lookup function needs: boundary values, all 5 rating tiers, both genders, multiple age ranges, and invalid inputs. Mirror structure: `logic.py` → `tests/test_logic.py`.

## Environment Variables
```
LLM_PROVIDER=ollama          # "ollama" | "openai"
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_API_KEY=              # prod only
```

## Adding a New Fitness Test
1. Create `backend/data/norms/{test_name}.json` following the schema above
2. Register test metadata in `backend/app/logic.py`
3. `calculate_single_test()` handles lookup automatically — no new logic unless a formula is needed
4. LLM and PDF adapt automatically — they consume `MetricResult` objects

## Out of Scope (POC)
No auth (single-user assumed), no RAG, no longitudinal tracking. Design endpoints so JWT auth can be added as middleware later without touching business logic.