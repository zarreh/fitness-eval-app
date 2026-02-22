# Fitness Evaluation App

A B2B fitness assessment platform for coaches. Input raw test scores → get normalized ratings and percentiles → generate an LLM-powered narrative analysis and professional PDF report for the client.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

---

## What It Does

A coach runs a client through a standardized test battery, enters the scores, and within seconds gets:

- **Ratings** (Excellent → Very Good → Good → Fair → Poor) with percentile benchmarks from normative data (ACSM, YMCA, ACE)
- **Progress tracking** — delta indicators and Plotly charts across multiple sessions
- **LLM-generated narrative** — a readable summary of strengths and areas to work on, tailored to the client's goals and workout preferences
- **A polished PDF report** — ready to hand to the client, in English, Spanish, or Farsi

The LLM only *explains* results. All calculations are deterministic and auditable — no hallucinated numbers.

---

## Screenshots

| Assessment page | PDF report |
|---|---|
| Range bars with zone labels and threshold numbers, progress delta indicators | Cover page, results table, progress charts, RTL support for Farsi |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI (async), Python 3.11+ |
| **Frontend** | Streamlit (thin client — HTTP calls only) |
| **Database** | SQLite via SQLAlchemy async + aiosqlite |
| **LLM — dev** | Ollama + Llama 3.2 (local, free) |
| **LLM — prod** | OpenAI GPT-4o (config-driven, no code change needed) |
| **LLM framework** | LangChain 0.3+ |
| **PDF** | WeasyPrint + Jinja2 HTML template |
| **Charts** | Plotly (interactive in app, PNG-embedded in PDF) |
| **Auth** | bcrypt password hashing (passlib) |
| **i18n** | JSON translation bundles — EN / ES / FA (RTL) |
| **Package manager** | Poetry |
| **Deployment** | Docker Compose |

---

## Features

### Assessment Tests (8 tests, 4 categories)

| Category | Tests |
|---|---|
| Strength | Push-up (reps), Wall Sit (sec), Forearm Plank (sec) |
| Flexibility | Sit-and-Reach (cm), Zipper Test (cm) |
| Cardiovascular | YMCA 3-Min Step Test (BPM) |
| Body Composition | BMI (auto-computed), Body Fat % (US Navy formula), Waist-to-Hip Ratio |

### Platform Features

- **Multi-coach isolation** — each coach sees only their own clients
- **Coach self-service signup** with username/password
- **Body measurements time series** — log weight, waist, hip, neck over time; auto-computes BMI, body fat %, fat/lean mass
- **5-tier rating system** with visual range bars, zone labels, and threshold numbers
- **Progress indicators** — `▲ +8 reps (Good → Very Good)` with color coding
- **Progress charts** — Plotly line charts with colored zone backgrounds across sessions
- **Workout preferences** — preferred activities and available equipment fed into LLM prompt
- **Multi-language UI and PDF** — English, Spanish, Farsi (with full RTL layout)
- **PDF export** — A4 report with cover page, results table, charts, and LLM narrative
- **CSV history export** — full assessment history for a client

---

## Getting Started

### Prerequisites

- Docker & Docker Compose **or** Python 3.11+ with Poetry
- For local dev: [Ollama](https://ollama.com) installed and running

### Option 1 — Docker (recommended)

```bash
# Clone the repo
git clone <repo-url>
cd fitness-eval-app

# Configure environment
cp .env.example backend/.env
# Edit backend/.env if needed (defaults work for local Ollama dev)

# Start the full stack (backend + frontend + Ollama)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Pull the LLM model (first time only)
docker compose exec ollama ollama pull llama3.2
```

Open [http://localhost:8501](http://localhost:8501) to use the app.
FastAPI docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

### Option 2 — Local dev (Poetry)

```bash
# Install dependencies
cd backend && poetry install
cd ../frontend && poetry install

# Copy environment config
cp .env.example backend/.env

# Start Ollama in a separate terminal
ollama serve
ollama pull llama3.2

# Start the backend (port 8000)
cd backend && poetry run uvicorn app.main:app --reload --port 8000

# Start the frontend (port 8501)
cd frontend && poetry run streamlit run app.py --server.port 8501
```

### Option 3 — Production with OpenAI

```bash
# In backend/.env:
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Start production stack (no Ollama needed)
docker compose up --build
```

---

## Environment Variables

Copy `.env.example` → `backend/.env`:

```env
LLM_PROVIDER=ollama          # "ollama" or "openai"
LLM_MODEL=llama3.2           # model name
OPENAI_API_KEY=              # required when LLM_PROVIDER=openai
OLLAMA_BASE_URL=http://localhost:11434
COACH_USERNAME=admin         # legacy single-user fallback
COACH_PASSWORD=admin
```

> **Note:** Multi-coach mode uses the database. The `COACH_USERNAME`/`COACH_PASSWORD` variables act as a seed admin account on first startup.

---

## Project Structure

```
fitness-eval-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints
│   │   ├── models.py            # Pydantic schemas
│   │   ├── logic.py             # Normative lookup + rating engine
│   │   ├── llm_service.py       # LangChain wrapper (Ollama / OpenAI)
│   │   ├── pdf_service.py       # WeasyPrint PDF + chart embedding
│   │   ├── db_service.py        # SQLite CRUD
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── db_models.py         # ORM tables
│   │   ├── i18n_service.py      # Translation loading
│   │   ├── config.py            # pydantic-settings
│   │   └── prompts/             # LLM prompt templates (edit here)
│   ├── data/
│   │   ├── norms/               # Per-test normative JSON files
│   │   └── i18n/                # en.json, es.json, fa.json
│   ├── templates/
│   │   ├── report.html          # Jinja2 PDF template
│   │   └── fonts/               # Bundled Vazirmatn (Farsi PDF font)
│   └── tests/                   # pytest test suite
├── frontend/
│   ├── app.py                   # Login + navigation
│   ├── pages/
│   │   ├── 0_signup.py          # Coach registration
│   │   ├── 1_client_profile.py  # Client details + measurements
│   │   ├── 2_assessment.py      # Test input + results
│   │   └── 3_report.py          # LLM report + PDF download
│   └── utils.py                 # Shared components: range bars, charts, i18n
├── docs/                        # Architecture and planning docs
├── docker-compose.yml           # Production stack
├── docker-compose.dev.yml       # Dev override (adds Ollama service)
├── Makefile                     # Helper commands
└── .env.example                 # Config template
```

---

## API Reference

```
GET  /health
POST /auth/login                 → authenticate coach
POST /auth/signup                → register new coach

GET  /clients?coach=             → list coach's clients
POST /clients?coach=             → create / update client
DELETE /clients/{name}?coach=    → delete client
GET  /clients/{name}/history/csv → export assessment history

GET  /clients/{name}/measurements?coach=   → body measurement history
POST /clients/{name}/measurements?coach=   → log new measurement

POST /assess/calculate           → run normative lookup, return ratings
POST /assess/generate-report     → LLM narrative + workout plan
POST /assess/generate-pdf        → PDF bytes

GET  /tests/battery              → test metadata (names, units, categories)
GET  /i18n/{lang}                → translation bundle
```

---

## Development

```bash
# Run tests
cd backend && poetry run pytest tests/ -v

# Type checking
cd backend && poetry run mypy app/ --strict

# Lint / format
cd backend && poetry run ruff check app/ tests/
cd backend && poetry run ruff format app/ tests/
```

### Adding a New Fitness Test

1. Create `backend/data/norms/{test_id}.json` following the schema:
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
2. Register the test in `backend/app/logic.py`
3. The generic calculation engine, LLM prompts, and PDF template all adapt automatically

### Switching LLM Providers

Set `LLM_PROVIDER` and `LLM_MODEL` in `backend/.env` — no code changes needed:

```env
# Local development
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2

# Production
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
```

### Modifying LLM Behavior

Edit the prompt templates in `backend/app/prompts/` directly. The system prompt enforces medical/legal guardrails — never weaken them.

---

## Architecture Decisions

**LLM never calculates.** All percentiles, ratings, and body composition values are computed in `logic.py` using normative lookup tables. The LLM receives only pre-calculated `MetricResult` objects and is instructed never to recalculate.

**Streamlit is a thin client.** It calls the FastAPI backend over HTTP. It never imports backend modules directly.

**Normative data is version-controlled JSON.** No ratings are hardcoded in Python. Adding or adjusting norms is a data change, not a code change.

---

## License

MIT
