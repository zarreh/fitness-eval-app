# Fitness Evaluation App — Architecture Document

**Version:** 0.1 (POC)
**Last Updated:** 2026-02-19
**Status:** Draft

---

## 1. Overview

### 1.1 What Is This?
A **B2B fitness assessment platform** that turns raw physical test data into intelligent, professional reports for coaches. The core differentiator is an **intelligence layer** ("The Brain") that interprets data — calculating percentiles, generating body age estimates, and producing LLM-driven analysis — rather than simply storing it.

### 1.2 Target Users
- **POC Phase:** Independent fitness coaches / personal trainers
- **Final Phase:** Gyms, wellness clinics, corporate wellness programs (B2B2C + white-labeling)

### 1.3 Core Value Proposition
> Coach inputs raw assessment data → App calculates percentiles & ratings → LLM generates narrative analysis + base workout suggestions → Coach reviews & delivers professional PDF report to client.

The LLM is **invisible to the end-user**. It assists the coach — it does not replace them.

---

## 2. System Architecture

### 2.1 High-Level Data Flow

```
┌─────────────┐     HTTP/REST      ┌─────────────────┐
│  Frontend    │ ──────────────────►│  Backend (API)   │
│  (Streamlit) │◄────────────────── │  (FastAPI)       │
│  Thin Client │                    │                  │
└─────────────┘                    ├─────────────────┤
                                   │  Logic Engine    │
                                   │  (Python/Pandas) │
                                   ├─────────────────┤
                                   │  LLM Service     │
                                   │  (LangChain)     │
                                   │      │           │
                                   │      ▼           │
                                   │  Ollama / OpenAI │
                                   ├─────────────────┤
                                   │  PDF Generator   │
                                   │  (WeasyPrint)    │
                                   └─────────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  Normative   │
                                   │  Data (JSON) │
                                   └─────────────┘
```

### 2.2 Design Principles

1. **Headless Backend:** FastAPI serves as a pure REST API. The frontend is a thin client that only calls endpoints. This enables easy swapping of Streamlit → React later.
2. **LLM Abstraction:** LangChain wraps all LLM calls. Ollama is used for **local development only**; OpenAI API is used for **POC deployment and beyond**. Switching providers requires only a config/env var change.
3. **Separation of Concerns:** The LLM **explains and suggests**. It does **not** perform calculations. All quantitative work (percentiles, ratings) is done by the Python logic engine.
4. **No Medical/Legal Advice:** The LLM is explicitly instructed to avoid medical diagnoses or legal health claims. It provides fitness analysis and base workout plans for the coach's review.

---

## 3. Tech Stack

| Layer            | POC                        | Final Phase            | Rationale                                           |
|------------------|----------------------------|------------------------|-----------------------------------------------------|
| **Frontend**     | Streamlit                  | React                  | Streamlit = fast POC; thin client pattern allows swap |
| **Backend API**  | FastAPI                    | FastAPI                | Async, auto-docs (Swagger), Pydantic validation      |
| **Logic Engine** | Python + Pandas            | Python + Pandas        | Proven for data manipulation, percentile lookups      |
| **LLM Framework**| LangChain                  | LangChain              | Abstraction layer; familiar to team; RAG-ready        |
| **LLM Model (Dev)**| Ollama (Llama 3.2)      | —                      | Free, local, no API costs during development          |
| **LLM Model (Deploy)**| OpenAI API            | OpenAI GPT-4 (or TBD) | Quality + speed for POC demos & production            |
| **Normative Data**| JSON files               | PostgreSQL / JSON      | JSON = simple; DB for multi-tenancy later             |
| **PDF Output**   | WeasyPrint                 | WeasyPrint             | HTML→PDF; supports CSS styling for professional look  |
| **Deployment**   | Docker Compose (Linux)     | Docker Compose + CI/CD | Reproducible; backend + Ollama in containers          |
| **IDE**          | VS Code                    | VS Code                | Claude Code + Copilot integration                     |

---

## 4. Component Details

### 4.1 Frontend (Streamlit — Thin Client)

**Responsibility:** UI only. All business logic lives in the backend.

**Pages / Views (POC):**
- Coach Login (simple auth placeholder)
- Client Profile (name, age, gender, goals)
- Assessment Input (multi-step form by category)
- Report Preview (rendered results from API)
- PDF Download

**Key Rule:** Streamlit makes HTTP calls to FastAPI. It does **not** import backend modules directly.

### 4.2 Backend API (FastAPI)

**Endpoints (POC):**

| Method | Endpoint                  | Description                                    |
|--------|---------------------------|------------------------------------------------|
| GET    | `/health`                 | Health check                                   |
| POST   | `/assess/calculate`       | Accepts raw test data, returns ratings/percentiles |
| POST   | `/assess/generate-report` | Accepts calculated results + client profile, returns LLM narrative |
| POST   | `/assess/generate-pdf`    | Accepts full report data, returns PDF file     |
| GET    | `/tests/battery`          | Returns available test battery with metadata   |

### 4.3 Logic Engine

**Responsibility:** All quantitative calculations — percentile lookups, category ratings, composite scores.

**Normative Data Storage:** JSON files in `backend/data/norms/` directory.

```
backend/data/norms/
├── pushup.json
├── wall_sit.json
├── plank.json
├── sit_and_reach.json
├── zipper.json
├── step_test.json
├── bmi.json
└── waist_to_hip.json
```

Each JSON file contains lookup tables segmented by **age group** and **gender**, sourced from ACSM, YMCA, or equivalent free/public data.

**Rating Scale:** All tests normalize to a common 5-tier scale:
- Excellent → Good → Average → Below Average → Poor

### 4.4 LLM Service (LangChain)

**Responsibility:** Generate narrative text. Two main outputs:

1. **Coach's Summary:** Overall assessment narrative explaining what the numbers mean, highlighting strengths and areas for improvement.
2. **Base Workout Suggestions:** Starter workout plan aligned with the client's stated goals, for the coach to review and modify.

**Provider Switching (via config/env var):**
```
LLM_PROVIDER=ollama  # or "openai"
LLM_MODEL=llama3.2   # or "gpt-4"
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_API_KEY=sk-...
```

**Prompt Engineering Notes:**
- System prompt explicitly prohibits medical/legal advice
- LLM receives pre-calculated results only — never raw data to compute
- Structured output format enforced (sections for summary, strengths, areas for improvement, workout plan)
- Client goals are injected into the prompt context

### 4.5 PDF Generator (WeasyPrint)

**Responsibility:** Convert HTML/CSS template + report data into a professional PDF.

**Approach:** Jinja2 HTML templates styled with CSS → rendered by WeasyPrint.

**Why WeasyPrint over LaTeX?**
- **White-labeling ready:** Swapping CSS themes/logos is trivial vs. editing LaTeX templates
- **Designer-friendly:** Future designers/contractors know HTML/CSS, not LaTeX
- **Lighter Docker footprint:** TeX Live adds ~2-4GB to container images; WeasyPrint is a pip install + minimal system deps
- **Right tool for the job:** LaTeX excels at academic papers with complex math notation; our reports need tables, color-coded ratings, and charts — CSS handles this cleanly
- **CSS Paged Media support:** WeasyPrint handles repeating headers/footers and page breaks for multi-page reports

**POC:** Clean, functional layout.
**Final Phase:** Branded, white-label-ready templates (coach logo, gym branding, color schemes).

---

## 5. Assessment Test Battery (POC)

### 5.1 Strength
| Test           | Target Area      | Data Source        | Input              |
|----------------|------------------|--------------------|---------------------|
| Push-up Test   | Upper Body Push  | ACSM / ACE         | Reps completed      |
| Wall Sit Test  | Lower Body       | General norms       | Time (seconds)      |
| Plank Test     | Core             | General norms       | Time (seconds)      |

### 5.2 Flexibility
| Test           | Target Area         | Data Source    | Input              |
|----------------|---------------------|----------------|---------------------|
| Sit-and-Reach  | Hamstrings / Back   | ACSM           | Distance (cm)       |
| Zipper Test    | Shoulder Flexibility | General norms  | Distance (cm)       |

### 5.3 Cardiovascular
| Test                  | Target Area     | Data Source | Input                        |
|-----------------------|-----------------|-------------|-------------------------------|
| YMCA 3-Min Step Test  | Aerobic Fitness | YMCA        | Heart rate (1 min post-test)  |

### 5.4 Body Composition
| Test           | Target Area     | Data Source | Input                    |
|----------------|-----------------|-------------|---------------------------|
| BMI            | Body Mass Index | WHO / ACSM  | Height (cm), Weight (kg)  |
| Waist-to-Hip   | Fat Distribution| WHO         | Waist (cm), Hip (cm)      |

---

## 6. Data Models (Pydantic)

### 6.1 Client Profile
```python
class ClientProfile(BaseModel):
    name: str
    age: int
    gender: Literal["male", "female"]
    goals: list[str]  # e.g., ["weight_loss", "muscle_gain", "endurance"]
    notes: Optional[str] = None
```

### 6.2 Assessment Input
```python
class AssessmentInput(BaseModel):
    client: ClientProfile
    tests: dict[str, float]
    # Example: {"pushup": 25, "wall_sit": 60, "plank": 90, ...}
```

### 6.3 Metric Result
```python
class MetricResult(BaseModel):
    test_name: str
    raw_value: float
    unit: str
    rating: str          # "Excellent" | "Good" | "Average" | "Below Average" | "Poor"
    percentile: Optional[float] = None
    category: str        # "strength" | "flexibility" | "cardio" | "body_comp"
    description: str     # Human-readable explanation
```

### 6.4 Report Response
```python
class ReportResponse(BaseModel):
    client: ClientProfile
    results: list[MetricResult]
    llm_summary: str
    workout_suggestions: str
    generated_at: datetime
```

---

## 7. Deployment (POC)

### 7.1 Docker Compose Topology

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - LLM_PROVIDER=ollama
      - LLM_MODEL=llama3.2
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://backend:8000

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

### 7.2 Server Requirements (POC)
- **OS:** Linux (Ubuntu 22.04+)
- **RAM:** 8GB minimum (Llama 3.2 needs ~4-6GB)
- **Storage:** 10GB+ (for Ollama model files)
- **GPU:** Not required for POC (CPU inference acceptable for demo)

---

## 8. Project Structure

```
fitness-eval-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app + endpoints
│   │   ├── models.py         # Pydantic data models
│   │   ├── logic.py          # Calculation engine
│   │   ├── llm_service.py    # LangChain LLM wrapper
│   │   ├── pdf_service.py    # WeasyPrint PDF generation
│   │   └── config.py         # Environment/settings
│   ├── data/
│   │   └── norms/            # JSON normative tables
│   ├── templates/
│   │   └── report.html       # Jinja2 PDF template
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app.py                # Streamlit thin client
│   ├── pages/                # Multi-page Streamlit app
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── CLAUDE.md
├── .github/
│   └── copilot-instructions.md
├── README.md
└── docs/
    ├── architecture.md       # This document
    └── implementation-plan.md
```

---

## 9. Future Extensibility (Out of POC Scope)

These are documented for architectural awareness — **not to be built in POC**:

- **Longitudinal Tracking:** Store assessment history per client; visualize progress over time
- **Database:** PostgreSQL for multi-tenancy, client records, coach accounts
- **Authentication:** OAuth2 / JWT for coach login
- **White-Labeling:** Custom branding, logos, color themes per gym/organization
- **RAG Pipeline:** Ground LLM responses in vetted scientific papers (ACSM guidelines, etc.)
- **React Frontend:** Replace Streamlit with full React SPA
- **B2B2C Model:** Client-facing portal for self-assessments, upselling to coach
- **Body Age Score:** Composite metric aggregating all test results into a single "fitness age"
- **Progress Dashboard:** Visual charts showing improvement over assessment sessions

---

## 10. Key Decisions Log

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Frontend (POC) | Streamlit | Jinja2 templates, React | Familiar to team; thin client pattern allows swap |
| Backend | FastAPI | Flask, Django | Async, auto-docs, Pydantic-native |
| LLM Framework | LangChain | Raw HTTP calls, LiteLLM | Team expertise; RAG-ready for final phase |
| LLM (Local Dev) | Ollama + Llama 3.2 | — | Free, local, no API costs during development |
| LLM (POC Deploy) | OpenAI API | Anthropic, Ollama cloud | Quality + reliability for demos; easy swap via LangChain |
| Norms Storage | JSON files | SQLite, hardcoded dicts | Simple, version-controllable, easy to update |
| PDF Engine | WeasyPrint | LaTeX, ReportLab, FPDF | HTML/CSS = designer-friendly, white-label ready, lighter Docker footprint vs LaTeX |
| Deployment | Docker Compose | Bare metal, K8s | Reproducible; right-sized for POC |
| Calculations | Python logic engine | LLM-computed | Deterministic, auditable, no hallucination risk |