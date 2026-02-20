# Fitness Evaluation App — Implementation Plan

**Version:** 0.1 (POC)
**Last Updated:** 2026-02-19
**Status:** Draft
**Developer:** Solo
**Approach:** Vertical Slice — one test end-to-end first, then expand horizontally

---

## 1. Guiding Principles

1. **No speculative code.** Every line serves a clear, immediate purpose.
2. **Vertical slices over horizontal layers.** A working thin feature beats a polished incomplete layer.
3. **POC code should be clean and extensible**, not throwaway.
4. **Test with real-ish data early.** Use a sample client profile from Phase 1 onward.
5. **Commit after each working milestone.** Small, atomic commits.

---

## 2. Prerequisites (Before Phase 1)

### 2.1 Local Dev Environment
- [ ] Python 3.11+ installed
- [ ] VS Code with Claude Code + GitHub Copilot extensions
- [ ] Docker + Docker Compose installed
- [ ] Ollama installed locally (`curl -fsSL https://ollama.com/install.sh | sh`)
- [ ] Pull Llama 3.2 model (`ollama pull llama3.2`)
- [ ] Verify Ollama running (`curl http://localhost:11434/api/tags`)

### 2.2 Project Bootstrap
- [ ] Create GitHub repo: `fitness-eval-app`
- [ ] Initialize project structure (see Architecture Doc §8)
- [ ] Create Python virtual environment (`python -m venv venv`)
- [ ] Create `backend/requirements.txt`:
  ```
  fastapi==0.115.*
  uvicorn[standard]==0.34.*
  pydantic==2.*
  pandas==2.*
  langchain==0.3.*
  langchain-openai==0.3.*
  langchain-ollama==0.3.*
  weasyprint==63.*
  jinja2==3.*
  python-dotenv==1.*
  httpx==0.28.*
  ```
- [ ] Create `frontend/requirements.txt`:
  ```
  streamlit==1.*
  httpx==0.28.*
  ```
- [ ] Create `.env` file (gitignored):
  ```
  LLM_PROVIDER=ollama
  LLM_MODEL=llama3.2
  OLLAMA_BASE_URL=http://localhost:11434
  OPENAI_API_KEY=sk-placeholder
  ```
- [ ] Create `backend/app/config.py` (reads env vars via `pydantic-settings`)
- [ ] Add `CLAUDE.md` and `.github/copilot-instructions.md` (see separate docs)
- [ ] Initial commit

---

## 3. Phase 1 — Vertical Slice (Push-up Test End-to-End)

**Goal:** Coach inputs a client profile + push-up score → backend calculates rating → LLM generates summary → PDF downloads. One test, fully working.

### 3.1 Backend Skeleton

#### 3.1.1 Data Models (`backend/app/models.py`)
- [ ] `ClientProfile` — name, age, gender, goals, notes
- [ ] `AssessmentInput` — client + tests dict
- [ ] `MetricResult` — test_name, raw_value, unit, rating, percentile, category, description
- [ ] `CalculationResponse` — client + list of MetricResult
- [ ] `ReportRequest` — client + results + (optional) coach notes
- [ ] `ReportResponse` — client + results + llm_summary + workout_suggestions + generated_at

#### 3.1.2 FastAPI App (`backend/app/main.py`)
- [ ] Create FastAPI app instance
- [ ] `GET /health` — returns `{"status": "ok"}`
- [ ] `POST /assess/calculate` — accepts `AssessmentInput`, returns `CalculationResponse`
- [ ] `POST /assess/generate-report` — accepts `ReportRequest`, returns `ReportResponse`
- [ ] `POST /assess/generate-pdf` — accepts `ReportResponse`, returns PDF file (StreamingResponse)
- [ ] `GET /tests/battery` — returns list of available tests with metadata
- [ ] CORS middleware enabled (for future React frontend)

#### 3.1.3 Config (`backend/app/config.py`)
- [ ] Use `pydantic-settings` `BaseSettings` to load from `.env`
- [ ] Fields: `llm_provider`, `llm_model`, `ollama_base_url`, `openai_api_key`

**Milestone:** `uvicorn backend.app.main:app --reload` starts, Swagger UI accessible at `/docs`, `/health` returns 200.

### 3.2 Push-up Logic (First Test)

#### 3.2.1 Normative Data (`backend/data/norms/pushup.json`)
- [ ] Create JSON structure:
  ```json
  {
    "test_name": "Push-up Test",
    "unit": "reps",
    "category": "strength",
    "target_area": "Upper Body Push",
    "source": "ACSM Guidelines for Exercise Testing and Prescription",
    "norms": {
      "male": {
        "20-29": {"excellent": 36, "good": 29, "average": 22, "below_average": 17, "poor": 0},
        "30-39": {"excellent": 30, "good": 22, "average": 17, "below_average": 12, "poor": 0},
        ...
      },
      "female": { ... }
    }
  }
  ```
- [ ] Research and fill all age brackets (20-29, 30-39, 40-49, 50-59, 60+) for both genders
- [ ] Document data source URL in the JSON metadata

#### 3.2.2 Logic Engine (`backend/app/logic.py`)
- [ ] `load_norms(test_name: str) -> dict` — loads JSON from `backend/data/norms/`
- [ ] `get_age_bracket(age: int) -> str` — maps age to bracket string (e.g., 25 → "20-29")
- [ ] `get_rating(value: float, norms: dict, age: int, gender: str) -> str` — returns rating tier
- [ ] `calculate_single_test(test_name: str, value: float, age: int, gender: str) -> MetricResult`
- [ ] `calculate_all_tests(input: AssessmentInput) -> list[MetricResult]` — iterates all submitted tests

**Milestone:** Call `POST /assess/calculate` with `{"client": {..., "age": 30, "gender": "male"}, "tests": {"pushup": 25}}` → returns `MetricResult` with rating "Good".

### 3.3 LLM Service (First Pass)

#### 3.3.1 LLM Wrapper (`backend/app/llm_service.py`)
- [ ] `get_llm() -> BaseChatModel` — returns `ChatOllama` or `ChatOpenAI` based on config
- [ ] `generate_coach_summary(client: ClientProfile, results: list[MetricResult]) -> str`
  - System prompt: role definition, no medical advice, structured output sections
  - User prompt: inject client profile + calculated results
  - Output sections: Overall Summary, Strengths, Areas for Improvement
- [ ] `generate_workout_suggestions(client: ClientProfile, results: list[MetricResult]) -> str`
  - Separate call (or combined — decide during implementation)
  - Inject client goals into prompt context
  - Output: base workout plan skeleton for coach review

#### 3.3.2 Prompt Templates
- [ ] Create `backend/app/prompts/` directory
- [ ] `system_prompt.txt` — coach assistant persona + guardrails
- [ ] `summary_prompt.txt` — template with `{client_name}`, `{client_age}`, `{results_table}`, `{goals}` placeholders
- [ ] `workout_prompt.txt` — template with goal-aligned workout generation instructions

**Milestone:** Call `POST /assess/generate-report` → returns JSON with `llm_summary` and `workout_suggestions` containing coherent, structured text.

### 3.4 PDF Generation (First Template)

#### 3.4.1 PDF Service (`backend/app/pdf_service.py`)
- [ ] `render_report_pdf(report: ReportResponse) -> bytes`
  - Load Jinja2 template
  - Inject report data
  - Render HTML → PDF via WeasyPrint
  - Return PDF bytes

#### 3.4.2 Report Template (`backend/templates/report.html`)
- [ ] Header: App logo placeholder, report title, date
- [ ] Client Info: Name, age, gender, goals
- [ ] Results Table: Test name, raw value, rating (color-coded)
- [ ] LLM Summary Section: Rendered markdown/text
- [ ] Workout Suggestions Section: Rendered markdown/text
- [ ] Footer: Disclaimer ("This report is for informational purposes only...")
- [ ] Basic CSS: Clean typography, color-coded rating badges, page breaks

#### 3.4.3 PDF Endpoint
- [ ] `POST /assess/generate-pdf` returns `StreamingResponse` with `application/pdf` content type

**Milestone:** Call the PDF endpoint → downloads a clean, readable PDF with push-up results + LLM narrative.

### 3.5 Streamlit Frontend (Thin Client — Push-up Only)

#### 3.5.1 Main App (`frontend/app.py`)
- [ ] Configure `API_URL` from environment
- [ ] Sidebar: navigation between pages
- [ ] Utility: `api_call(method, endpoint, data)` wrapper using `httpx`

#### 3.5.2 Pages
- [ ] **Client Profile Page** (`frontend/pages/1_client_profile.py`)
  - Form: name, age, gender, goals (multiselect), notes
  - Save to `st.session_state`
- [ ] **Assessment Input Page** (`frontend/pages/2_assessment.py`)
  - Fetch test battery from `GET /tests/battery`
  - Input fields for push-up only (for now)
  - "Calculate" button → calls `POST /assess/calculate` → displays results
- [ ] **Report Page** (`frontend/pages/3_report.py`)
  - "Generate Report" button → calls `POST /assess/generate-report`
  - Display LLM summary + workout suggestions in expandable sections
  - "Download PDF" button → calls `POST /assess/generate-pdf` → `st.download_button`

**Milestone:** Full flow works in Streamlit: enter client → input push-up score → see rating → generate LLM report → download PDF.

### 3.6 Phase 1 Wrap-up
- [ ] Manual end-to-end test with 3 different sample profiles (young male, middle-aged female, older male)
- [ ] Review LLM output quality — adjust prompts if needed
- [ ] Review PDF layout — adjust CSS if needed
- [ ] Commit + tag: `v0.1.0-vertical-slice`

---

## 4. Phase 2 — Expand Test Battery

**Goal:** Add all remaining 7 tests. Logic + norms only — LLM and PDF already work generically.

### 4.1 Normative Data Collection
For each test, create `backend/data/norms/{test}.json` with full age/gender brackets:

- [ ] `wall_sit.json` — Lower Body Strength (seconds)
- [ ] `plank.json` — Core Strength (seconds)
- [ ] `sit_and_reach.json` — Hamstring/Back Flexibility (cm)
- [ ] `zipper.json` — Shoulder Flexibility (cm, +/- overlap)
- [ ] `step_test.json` — YMCA 3-Min Step Test (heart rate BPM)
- [ ] `bmi.json` — BMI classification (WHO/ACSM ranges)
- [ ] `waist_to_hip.json` — Waist-to-Hip Ratio (WHO ranges)

**Note:** BMI and waist-to-hip may use formula-based calculations rather than pure lookup tables. Handle in logic engine accordingly.

### 4.2 Logic Engine Expansion
- [ ] Ensure `calculate_single_test()` handles all test types
- [ ] Add BMI calculation: `weight_kg / (height_m ** 2)` → then classify
- [ ] Add waist-to-hip ratio calculation: `waist_cm / hip_cm` → then classify
- [ ] Add test-specific input validation (e.g., push-ups must be >= 0, heart rate must be 40-220)
- [ ] Unit tests for each test's rating logic (at least 3 cases per test: low, mid, high)

### 4.3 Frontend Expansion
- [ ] Update Assessment Input page to show all test categories (Strength, Flexibility, Cardio, Body Comp)
- [ ] Group inputs by category with collapsible sections
- [ ] Allow partial submissions (not all tests required)

### 4.4 Phase 2 Wrap-up
- [ ] End-to-end test with full test battery
- [ ] Verify LLM handles multiple results gracefully (prompt may need tuning for 8 tests)
- [ ] Commit + tag: `v0.2.0-full-battery`

---

## 5. Phase 3 — LLM Quality & Prompt Engineering

**Goal:** Refine LLM output to be genuinely useful for coaches. This phase is iterative.

### 5.1 Prompt Refinement
- [ ] Test current prompts with edge cases:
  - All "Excellent" results
  - All "Poor" results
  - Mixed results (excellent cardio, poor flexibility)
  - Multiple conflicting goals (e.g., "weight loss" + "muscle gain")
- [ ] Refine system prompt guardrails:
  - No specific medical conditions mentioned
  - No supplement recommendations
  - No specific injury diagnoses
  - Always defer to coach's professional judgment
- [ ] Add few-shot examples in prompt if needed for output consistency
- [ ] Test output structure consistency (headings, bullet points, formatting)

### 5.2 Workout Suggestion Quality
- [ ] Ensure workout suggestions align with client goals
- [ ] Ensure suggestions address "Areas for Improvement" from the assessment
- [ ] Add intensity/volume scaling based on overall fitness level
- [ ] Structure: Warm-up → Main Workout (by goal) → Cool-down/Flexibility
- [ ] Include frequency recommendation (days per week)

### 5.3 OpenAI Testing
- [ ] Switch `LLM_PROVIDER=openai` in `.env`
- [ ] Compare output quality: Ollama (Llama 3.2) vs. OpenAI
- [ ] Benchmark response time
- [ ] Adjust prompts if needed for different model behavior
- [ ] Document model-specific prompt tweaks if any

### 5.4 Phase 3 Wrap-up
- [ ] Create a "golden dataset" of 5-10 sample profiles with expected output quality benchmarks
- [ ] Review all outputs with a fitness professional if possible
- [ ] Commit + tag: `v0.3.0-llm-refined`

---

## 6. Phase 4 — PDF Template Polish

**Goal:** Make the PDF report look professional — something a coach would proudly hand to a client.

### 6.1 Design & Layout
- [ ] Color-coded rating badges (green → red gradient for Excellent → Poor)
- [ ] Category summary cards (Strength, Flexibility, Cardio, Body Comp)
- [ ] Results table with clean typography
- [ ] Visual hierarchy: client info → results overview → detailed breakdown → LLM narrative → workout plan
- [ ] Proper page breaks between major sections
- [ ] Header on every page (report title + client name)
- [ ] Footer on every page (disclaimer + page number + generation date)

### 6.2 Branding Placeholders
- [ ] Logo placeholder area (top of first page)
- [ ] CSS variables for primary/secondary colors (prep for white-labeling)
- [ ] Coach name/organization field

### 6.3 Content Sections
- [ ] Cover page: Client name, assessment date, coach/org name
- [ ] Executive summary (1 paragraph from LLM)
- [ ] Detailed results by category
- [ ] Strengths & areas for improvement (from LLM)
- [ ] Workout plan section
- [ ] Disclaimer page

### 6.4 Phase 4 Wrap-up
- [ ] Generate PDFs for sample profiles, review layout
- [ ] Test with long LLM outputs (does it paginate correctly?)
- [ ] Test with minimal data (only 2-3 tests submitted)
- [ ] Commit + tag: `v0.4.0-pdf-polished`

---

## 7. Phase 5 — Streamlit Full UI

**Goal:** Complete the Streamlit frontend with all pages, proper flow, and basic UX polish.

### 7.1 UI Enhancements
- [ ] Multi-step assessment wizard (step indicator showing progress)
- [ ] Input validation with clear error messages
- [ ] Results dashboard: summary cards + individual test results
- [ ] Report preview before PDF download (render LLM text in Streamlit)
- [ ] Loading states while waiting for API responses (especially LLM generation)

### 7.2 Coach Workflow
- [ ] Simple session-based "client list" (in-memory for POC — no DB)
- [ ] Ability to go back and edit inputs before generating report
- [ ] Option to add coach notes that get included in the report
- [ ] "Regenerate" button for LLM sections (if coach isn't satisfied with output)

### 7.3 Error Handling
- [ ] Graceful handling of API failures (backend down, LLM timeout)
- [ ] Informative error messages (not raw stack traces)
- [ ] Retry logic for LLM calls (LangChain retry or manual)

### 7.4 Phase 5 Wrap-up
- [ ] Full walkthrough: create client → input all tests → review → generate → download
- [ ] Test on different screen sizes (Streamlit is responsive by default, but verify)
- [ ] Commit + tag: `v0.5.0-full-ui`

---

## 8. Phase 6 — Docker Compose & Deployment

**Goal:** Containerize everything and deploy to a Linux server.

### 8.1 Docker Configuration

#### 8.1.1 Backend Dockerfile (`backend/Dockerfile`)
- [ ] Base image: `python:3.11-slim`
- [ ] Install WeasyPrint system dependencies (`libpango`, `libcairo`, etc.)
- [ ] Copy requirements + install
- [ ] Copy app code
- [ ] CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

#### 8.1.2 Frontend Dockerfile (`frontend/Dockerfile`)
- [ ] Base image: `python:3.11-slim`
- [ ] Copy requirements + install
- [ ] Copy app code
- [ ] CMD: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`

#### 8.1.3 Docker Compose (`docker-compose.yml`)
- [ ] Three services: `backend`, `frontend`, `ollama`
- [ ] Environment variable passthrough via `.env` file
- [ ] Ollama volume for persistent model storage
- [ ] Health checks for all services
- [ ] Network configuration

### 8.2 Deployment Steps
- [ ] Provision Linux server (Ubuntu 22.04+, 8GB+ RAM)
- [ ] Install Docker + Docker Compose
- [ ] Clone repo
- [ ] Configure `.env` for production:
  - `LLM_PROVIDER=openai`
  - `LLM_MODEL=gpt-4` (or chosen model)
  - Set `OPENAI_API_KEY`
- [ ] `docker compose up -d`
- [ ] Verify all services healthy
- [ ] Pull Ollama model if using locally: `docker exec ollama ollama pull llama3.2`

### 8.3 Production Considerations (Minimal for POC)
- [ ] Basic logging (structured JSON logs from FastAPI)
- [ ] Environment-based config (dev vs. prod)
- [ ] `.env.example` committed (without secrets)
- [ ] README with deployment instructions

### 8.4 Phase 6 Wrap-up
- [ ] Deploy to server
- [ ] Full end-to-end test on deployed instance
- [ ] Commit + tag: `v0.6.0-deployed`
- [ ] 🎉 **POC Complete**

---

## 9. Post-POC Roadmap (Final Phase — High Level)

These are **not** part of the POC implementation. Listed for planning awareness only.

| Priority | Feature | Dependency |
|----------|---------|------------|
| 1 | PostgreSQL + client persistence | DB setup |
| 2 | Authentication (JWT) | DB |
| 3 | Longitudinal tracking (assessment history) | DB + auth |
| 4 | React frontend | API already exists |
| 5 | White-labeling (branded PDFs) | CSS theming |
| 6 | RAG pipeline (scientific paper grounding) | LangChain + vector DB |
| 7 | Body Age composite score | Research + logic |
| 8 | Progress dashboard (charts) | Longitudinal data |
| 9 | B2B2C client portal | Auth + new frontend routes |
| 10 | CI/CD pipeline | GitHub Actions |

---

## 10. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Normative data accuracy | Incorrect ratings → credibility loss | Cross-reference 2+ sources per test; document sources |
| LLM hallucination | Bad advice → liability | Pre-calculated data only; strict system prompt; coach reviews all output |
| LLM latency (Ollama on CPU) | Slow UX during dev | Accept for dev; OpenAI for deployment solves this |
| WeasyPrint CSS limitations | PDF layout issues | Test early (Phase 1); simpler layout beats complex broken one |
| Scope creep | POC never ships | Strict phase gates; no features without explicit approval |
| Solo developer bottleneck | Slow progress if stuck | Claude Code for implementation; document decisions for future onboarding |

---

## 11. Definition of Done (POC)

The POC is complete when:

- [ ] A coach can input a client profile with all 8 test scores
- [ ] The system calculates ratings/percentiles for all tests
- [ ] An LLM generates a coherent summary + workout suggestions
- [ ] A professional PDF report is downloadable
- [ ] The app runs in Docker Compose on a Linux server
- [ ] OpenAI API is used for deployed LLM calls
- [ ] Code is clean, documented, and in a GitHub repo