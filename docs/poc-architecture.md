# Fitness Evaluation App — POC Architecture Document

**Version:** 0.1 (POC)
**Last Updated:** 2026-02-19
**Audience:** Development Team & Project Lead

---

## 1. Project Overview

### 1.1 What Is This?
A **"Super-Coach" intelligence layer** for fitness professionals. Coaches input client assessment data, the app calculates percentiles/ratings against normative tables, an LLM drafts a professional summary, and the output is a downloadable PDF report.

### 1.2 Core Value Proposition
Unlike platforms that merely store data (Trainerize, CoachRx, Exercise.com), this app **interprets** it — producing Body Age estimates, population percentiles, written analysis, and base workout suggestions. The coach remains the expert; the app is their smart assistant.

### 1.3 Business Model (POC Context)
- **Path A: B2B ("Super-Coach Utility")**
- Coach is the user. End-client never sees the app directly.
- Coach inputs data → App generates report → Coach reviews/edits → Delivers to client.
- Future: B2B2C, white-labeling for gyms, longitudinal tracking.

### 1.4 POC Goals
1. Prove the core loop: **Input → Calculate → LLM Summary → PDF**
2. Validate that LLM-generated analysis adds real value for coaches.
3. Build a clean, extensible codebase — not throwaway code.
4. Test with a meaningful (but limited) battery of fitness assessments.

---

## 2. Test Battery (POC Scope)

### 2.1 Assessment Categories & Tests

| Category | Test | What It Measures | Norms Source |
|---|---|---|---|
| **Strength — Upper Body Push** | Push-up Test | Muscular endurance (chest, shoulders, triceps) | ACSM / ACE public tables |
| **Strength — Lower Body** | Wall Sit Test | Isometric leg endurance (quads) | Topend Sports / BrianMac |
| **Strength — Core** | Plank Test | Core isometric endurance | Public normative tables |
| **Flexibility — Posterior Chain** | Sit-and-Reach Test | Hamstring & lower back flexibility | ACSM public tables |
| **Flexibility — Shoulder** | Zipper Test (Back Scratch) | Shoulder flexibility | Public normative tables |
| **Cardio** | YMCA 3-Minute Step Test | Aerobic fitness (estimated VO2) | YMCA standard recovery HR tables |
| **Body Composition** | BMI + Waist-to-Hip Ratio | General body composition indicators | WHO / CDC public tables |

### 2.2 Data Input Approach
- **Manual entry only** (no sensors, no computer vision).
- Input organized by category (e.g., Strength page, Flexibility page).
- Coach enters raw values (reps, seconds, cm, HR, etc.).
- All calculations are done by the Python logic layer, **not the LLM**.

### 2.3 Normative Data Storage
- Stored as **JSON files** in `backend/data/norms/`.
- One JSON file per test (e.g., `pushup_norms.json`, `wall_sit_norms.json`).
- Keyed by **age group** and **gender**.
- Example structure:

```json
{
  "male": {
    "20-29": {
      "excellent": [36, null],
      "good": [29, 35],
      "above_average": [22, 28],
      "average": [17, 21],
      "below_average": [12, 16],
      "poor": [null, 11]
    }
  }
}
```

- **POC uses simplified/public versions of norms.** Production will use full ACSM licensed tables.

---

## 3. Technical Architecture

### 3.1 Design Principles
1. **Headless Backend:** FastAPI serves as a REST API. The frontend is a thin client. Any frontend (Streamlit now, React later) can be swapped without touching business logic.
2. **LLM Abstraction:** LangChain abstracts the LLM provider. Switching from Ollama/Llama3.2 to OpenAI/GPT-4 is a config change, not a code change.
3. **Separation of Concerns:** Calculations happen in Python. The LLM only interprets and explains pre-calculated results — it never performs math or gives medical/legal advice.
4. **Clean & Extensible:** POC code should be production-refactorable, not rewritable.

### 3.2 Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend API** | FastAPI (Python) | Async, auto-docs (Swagger), Pydantic models, easy React migration later |
| **Frontend (POC)** | Streamlit | Rapid prototyping, team familiarity. Thin client — only calls FastAPI endpoints |
| **LLM Framework** | LangChain | Team expertise, provider abstraction, future RAG/agent support |
| **LLM Provider (POC)** | Ollama + Llama 3.2 (local) | Free, no API keys, good for dev. Swappable to OpenAI/Anthropic |
| **PDF Generation** | WeasyPrint | HTML/CSS to PDF, good styling control, Python-native |
| **Data Storage (POC)** | JSON files (norms), SQLite or JSON (client data) | No DB setup overhead for POC |
| **Deployment** | Docker Compose on Linux server | Reproducible, bundles backend + Ollama + frontend |

### 3.3 Project Structure

```
fitness-eval-app/
├── docker-compose.yml
├── .env
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, router mounting
│   │   ├── config.py            # Settings (LLM provider, model name, etc.)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Pydantic models (input/output)
│   │   │   └── enums.py         # Rating levels, test types, etc.
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── assessment.py    # /assess/* endpoints
│   │   │   └── report.py        # /report/* endpoints
│   │   ├── logic/
│   │   │   ├── __init__.py
│   │   │   ├── calculator.py    # Core calculation engine
│   │   │   ├── norms_loader.py  # Loads & queries JSON norm tables
│   │   │   └── body_comp.py     # BMI, WHR calculations
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── service.py       # LangChain LLM abstraction
│   │   │   ├── prompts.py       # Prompt templates
│   │   │   └── chains.py        # LangChain chains (summary, workout)
│   │   ├── pdf/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py     # WeasyPrint PDF generation
│   │   │   └── templates/       # HTML/CSS templates for PDF
│   │   │       └── report.html
│   │   └── data/
│   │       └── norms/
│   │           ├── pushup_norms.json
│   │           ├── wall_sit_norms.json
│   │           ├── plank_norms.json
│   │           ├── sit_and_reach_norms.json
│   │           ├── zipper_norms.json
│   │           ├── step_test_norms.json
│   │           ├── bmi_norms.json
│   │           └── whr_norms.json
│
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                   # Streamlit main app
│   ├── pages/
│   │   ├── 1_client_profile.py
│   │   ├── 2_strength.py
│   │   ├── 3_flexibility.py
│   │   ├── 4_cardio.py
│   │   ├── 5_body_comp.py
│   │   └── 6_report.py
│   └── utils/
│       └── api_client.py        # HTTP calls to FastAPI backend
│
└── docs/
    ├── architecture.md          # This document
    └── future_vision.md         # Future architecture doc
```

### 3.4 Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Streamlit   │────▶│   FastAPI     │────▶│  Logic Engine  │
│  (Frontend)  │◀────│   (REST API)  │◀────│  (Python)      │
│              │     │               │     │  - calculator   │
│  Thin client │     │  /assess/*    │     │  - norms_loader │
│  HTTP calls  │     │  /report/*    │     │  - body_comp    │
│  only        │     │               │     └────────────────┘
└─────────────┘     │               │              │
                    │               │              ▼
                    │               │     ┌────────────────┐
                    │               │────▶│  LLM Service   │
                    │               │◀────│  (LangChain)   │
                    │               │     │  - Ollama (POC) │
                    │               │     │  - OpenAI (Prod)│
                    │               │     └────────────────┘
                    │               │              │
                    │               │              ▼
                    │               │     ┌────────────────┐
                    │               │────▶│  PDF Generator  │
                    │               │◀────│  (WeasyPrint)   │
                    └──────────────┘     └────────────────┘
```

**Step-by-step flow:**
1. Coach opens Streamlit → Creates/selects client profile.
2. Coach navigates category pages → Enters raw assessment data.
3. Streamlit sends data to `POST /assess/calculate`.
4. FastAPI logic engine loads norms, calculates ratings/percentiles.
5. Calculated results returned to Streamlit for preview.
6. Coach clicks "Generate Report" → Streamlit calls `POST /report/generate`.
7. FastAPI sends calculated results to LangChain LLM service.
8. LLM generates: overall summary, per-category analysis, base workout suggestions.
9. FastAPI passes LLM output + calculated data to WeasyPrint.
10. PDF returned to Streamlit → Coach previews and downloads.

---

## 4. API Design

### 4.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/assess/calculate` | Accepts raw assessment data, returns calculated ratings |
| `POST` | `/report/generate` | Accepts calculated results + client info, returns PDF |
| `POST` | `/report/preview` | Returns LLM-generated text without PDF (for review) |

### 4.2 Core Data Models (Pydantic)

```python
# --- Input Models ---

class ClientProfile(BaseModel):
    name: str
    age: int
    gender: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    goals: Optional[str] = None  # Free text: "lose weight", "run 5k", etc.

class AssessmentInput(BaseModel):
    client: ClientProfile
    pushup_reps: Optional[int] = None
    wall_sit_seconds: Optional[float] = None
    plank_seconds: Optional[float] = None
    sit_and_reach_cm: Optional[float] = None
    zipper_test_cm: Optional[float] = None        # Positive = overlap, negative = gap
    step_test_recovery_hr: Optional[int] = None    # 1-min post-exercise HR
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None

# --- Output Models ---

class MetricResult(BaseModel):
    test_name: str
    category: str                    # "strength", "flexibility", "cardio", "body_comp"
    raw_value: float
    rating: str                      # "excellent", "good", "average", "below_average", "poor"
    percentile_range: Optional[str]  # "Top 20%", etc.
    note: Optional[str] = None       # Edge case flags

class CalculationResponse(BaseModel):
    client: ClientProfile
    results: list[MetricResult]
    bmi: Optional[float] = None
    waist_to_hip_ratio: Optional[float] = None

class ReportResponse(BaseModel):
    summary: str                     # LLM-generated overall summary
    category_analyses: dict          # Per-category LLM text
    workout_suggestions: str         # Base workout plan (coach reviews)
    pdf_bytes: Optional[bytes]       # PDF file content
```

---

## 5. LLM Integration

### 5.1 Provider Abstraction

```python
# config.py
class Settings(BaseModel):
    llm_provider: Literal["ollama", "openai"] = "ollama"
    llm_model: str = "llama3.2"
    ollama_base_url: str = "http://ollama:11434"
    openai_api_key: Optional[str] = None
```

LangChain's `ChatOllama` / `ChatOpenAI` is selected at startup based on config. Switching providers = changing `.env` values.

### 5.2 LLM Responsibilities & Boundaries

**The LLM DOES:**
- Write a professional summary of pre-calculated results.
- Explain what ratings mean in plain language.
- Suggest a base workout plan aligned with client goals.
- Highlight areas of concern and areas of strength.

**The LLM DOES NOT:**
- Perform any calculations (all math is Python).
- Provide medical diagnoses or legal health advice.
- Recommend specific supplements, medications, or treatments.
- Access external data (no RAG in POC — future feature).

### 5.3 Prompt Strategy (POC)
- **System prompt:** Defines the LLM's role as a fitness analysis assistant for coaches. Includes strict guardrails against medical advice.
- **User prompt:** Structured template injected with calculated results, client profile, and goals.
- **Output format:** Structured sections (Summary, Strength Analysis, Flexibility Analysis, Cardio Analysis, Body Comp Analysis, Workout Suggestions).

### 5.4 Prompt Template (Simplified)

```
You are a professional fitness assessment analyst writing a report for a certified coach.

CLIENT PROFILE:
{client_name}, {age}yo {gender}, {height_cm}cm, {weight_kg}kg
Goals: {goals}

CALCULATED RESULTS:
{formatted_results_table}

INSTRUCTIONS:
1. Write a professional overall summary (3-5 sentences).
2. For each category, explain the results and their implications.
3. Suggest a base 4-week workout framework aligned with the client's goals.
4. Flag any areas that need attention.
5. DO NOT provide medical advice. If blood pressure or BMI is in a concerning range, recommend the coach advise a medical consultation.
6. Use professional but accessible language.
```

---

## 6. PDF Output

### 6.1 Approach
- HTML/CSS template in `backend/app/pdf/templates/report.html`.
- Jinja2 templating to inject data + LLM text.
- WeasyPrint converts to PDF.
- POC: Clean, professional, minimal branding.
- Future: White-label templates with coach/gym branding.

### 6.2 Report Sections
1. **Header:** Report title, date, coach name, client name.
2. **Client Overview:** Profile info, stated goals.
3. **Results Dashboard:** Table/visual summary of all test ratings.
4. **Category Breakdowns:** Per-category analysis (LLM-generated).
5. **Workout Plan:** Base suggestions (LLM-generated, coach-reviewed).
6. **Disclaimer:** Standard "not medical advice" footer.

---

## 7. Deployment (POC)

### 7.1 Docker Compose Setup

```yaml
version: "3.8"
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

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
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend

volumes:
  ollama_data:
```

### 7.2 Server Requirements (POC)
- **OS:** Linux (Ubuntu 22.04+ recommended)
- **RAM:** 8GB minimum (Llama 3.2 ~4GB), 16GB recommended
- **Storage:** 10GB+ for Ollama models
- **CPU:** 4+ cores (GPU optional but speeds up LLM inference)

### 7.3 Initial Setup Commands

```bash
# Clone repo
git clone <repo-url> && cd fitness-eval-app

# Start services
docker compose up -d

# Pull the LLM model (first time only)
docker compose exec ollama ollama pull llama3.2

# Verify
curl http://localhost:8000/health
```

---

## 8. Key Constraints & Decisions

| Decision | Choice | Rationale |
|---|---|---|
| No database (POC) | JSON/SQLite | Avoid DB setup overhead; data volume is tiny |
| Manual data entry only | No sensors/CV | Reduce POC scope; prove core value first |
| LLM = interpreter, not calculator | Separation of concerns | Avoid hallucinated numbers; Python is deterministic |
| Public normative data (POC) | Free ACSM/ACE/YMCA tables | Sufficient for POC; licensed data in production |
| Streamlit (POC frontend) | Team familiarity | Thin client pattern ensures easy React swap |
| No authentication (POC) | Simplify scope | Add auth in production phase |

---

## 9. Development Phases (POC)

### Phase 1: Foundation
- [ ] Project scaffolding (folder structure, Docker setup)
- [ ] Pydantic models (`schemas.py`, `enums.py`)
- [ ] Normative data JSON files (all 8 tests)
- [ ] `norms_loader.py` — generic loader for JSON norms

### Phase 2: Logic Engine
- [ ] `calculator.py` — rating lookup for all tests
- [ ] `body_comp.py` — BMI + WHR calculations
- [ ] Unit tests for all calculations

### Phase 3: API Layer
- [ ] FastAPI endpoints (`/assess/calculate`, `/report/preview`, `/report/generate`)
- [ ] Input validation & error handling
- [ ] Swagger docs verification

### Phase 4: LLM Integration
- [ ] LangChain service with Ollama provider
- [ ] Prompt templates & chains
- [ ] Test LLM output quality; iterate on prompts

### Phase 5: PDF Output
- [ ] HTML/CSS report template
- [ ] WeasyPrint integration
- [ ] PDF endpoint wiring

### Phase 6: Frontend (Streamlit)
- [ ] `api_client.py` — HTTP wrapper for FastAPI calls
- [ ] Multi-page Streamlit app (profile, strength, flex, cardio, body comp, report)
- [ ] Report preview & PDF download

### Phase 7: Integration & Polish
- [ ] End-to-end testing (full flow)
- [ ] Docker Compose deployment test on Linux
- [ ] Basic error handling & edge cases
- [ ] Documentation & README

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM output quality inconsistent | Report quality varies | Iterate prompts; add output validation; coach reviews before delivery |
| Normative data accuracy | Wrong ratings = lost credibility | Cross-reference multiple sources; unit test edge cases |
| Ollama resource consumption | Slow inference on small servers | Test with quantized models; set timeout limits |
| Scope creep | POC never ships | Strict test battery; no new features without explicit approval |
| Streamlit limitations | UI doesn't meet expectations | Accept limitations for POC; React is the production path |