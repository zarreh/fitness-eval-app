# Phase 8 — UX & Experience Improvements

## Context

The POC is functionally complete (Phases 1–7). Coaches can input test data, get ratings, generate LLM narratives, and download PDF reports. However the UX is minimal and several high-value features are missing: no progress tracking between assessments, no visual indicators showing where a client falls within rating ranges, single-language only, single-coach only, and the Streamlit UI lacks polish. This phase addresses all of these to make the app demo-ready and more useful in real coaching sessions.

---

## Sub-Phase 8A: Assessment History & Progress Tracking
**Foundation — must come first. Other sub-phases depend on this.**

### Data Model Changes — `backend/app/models.py`
- Add `AssessmentSnapshot` model: `results: list[MetricResult]`, `assessed_at: datetime`
- Add `assessment_history: list[AssessmentSnapshot] = []` to `ClientRecord` (keep `last_assessment` for backward compat)
- Add `ProgressDelta` model: `test_name`, `previous_value`, `current_value`, `previous_rating`, `current_rating`, `direction` (improved/declined/unchanged), `delta` (signed float)
- Add optional `progress: list[ProgressDelta]` to `ReportRequest` and `ReportResponse`

### Backend — `backend/app/client_service.py`
- Modify `save_assessment()`: append new `AssessmentSnapshot` to `assessment_history` (newest-first) instead of overwriting `last_assessment`
- Add legacy migration in `load_clients()`: if a record has `last_assessment` but empty `assessment_history`, auto-populate history from the existing data
- Add `compute_progress(current, previous) -> list[ProgressDelta]` function: compare two result sets by test name, determine direction via rating-tier comparison

### API — `backend/app/main.py`
- Add `GET /clients/{name}/history` → returns `list[AssessmentSnapshot]`
- Existing `POST /clients/{name}/assessment` returns updated `ClientRecord` with full history

### LLM — `backend/app/llm_service.py`
- Add `_format_progress_table(progress)` helper: formats deltas as text for prompt injection
- Modify `generate_coach_summary()` to accept optional `progress` param and inject progress section into summary prompt
- Modify `generate_workout_suggestions()` similarly — progress informs intensity adjustments

### Prompts — `backend/app/prompts/summary_prompt.txt`, `workout_prompt.txt`
- Add conditional `{progress_section}` placeholder: when progress data exists, instruct LLM to acknowledge improvements/declines with directional language

### Frontend — `frontend/pages/2_assessment.py`
- After calculation, if client has previous assessment in session state, compute and display delta indicators next to each result card (green ↑ / red ↓ / gray →)
- Store full `assessment_history` when loading client from sidebar

### Frontend — `frontend/pages/3_report.py`
- Pass `progress` list to `POST /assess/generate-report`

### PDF — `backend/templates/report.html`, `backend/app/pdf_service.py`
- Add optional "Progress" column to detailed results table (arrow + previous value)
- Add CSS for `.delta-improved`, `.delta-declined`, `.delta-unchanged`

### Tests — `backend/tests/test_progress.py` (new)
- Test `compute_progress()`: matching tests, missing tests, same/different ratings
- Test history append behavior
- Test legacy migration

---

## Sub-Phase 8B: Visual Rating Indicators (Colored Range Bars)
**Can start in parallel with 8A.**

### Backend — `backend/app/models.py`
- Add `thresholds: Optional[dict[str, float]] = None` and `inverted: bool = False` to `MetricResult`

### Backend — `backend/app/logic.py`
- Modify `calculate_single_test()` to include the looked-up thresholds dict and `inverted` flag in returned `MetricResult`
- For computed tests (BMI, WHR): include their hardcoded threshold breakpoints in the result

### Frontend — `frontend/utils.py`
- Add `render_range_bar_html(value, thresholds, unit, inverted)` function:
  - Horizontal bar divided into 5 color-coded zones (Poor=red → Excellent=green)
  - Zone widths proportional to threshold ranges
  - Triangle/line marker at client's value position
  - Zone labels below
  - For inverted tests: reverse color order (left=excellent, right=poor)

### Frontend — `frontend/pages/2_assessment.py`
- Render range bar below each result card via `st.markdown(render_range_bar_html(...), unsafe_allow_html=True)`

### PDF — `backend/app/pdf_service.py`
- Add `compute_range_bar_data(result)` helper: returns zone widths (%) and marker position (%) from MetricResult thresholds
- Pass bar data to template context

### PDF — `backend/templates/report.html`
- Add CSS-only range bar component (flexbox zones + absolute-positioned marker)
- Render below each test in the detailed results section

---

## Sub-Phase 8C: Multi-Language Support (English, Spanish, Farsi)

### Translation Files — `backend/data/i18n/` (new directory)
- `en.json`, `es.json`, `fa.json` — each containing:
  - `lang_code`, `lang_name`, `direction` (ltr/rtl)
  - `ui.*` — all frontend labels
  - `ratings.*` — translated rating names
  - `categories.*` — translated category names
  - `goals.*` — translated goal labels
  - `pdf.*` — cover page text, disclaimer, section headings

### Backend i18n Service — `backend/app/i18n_service.py` (new)
- `load_translations(lang)` — cached JSON loading
- `t(lang, key_path)` — dot-notation key lookup

### API — `backend/app/main.py`
- Add `GET /i18n/{lang}` → returns full translation dict for frontend
- Add `language: str = "en"` to `ReportRequest`

### LLM — `backend/app/llm_service.py`
- Append language instruction to prompts: `"Generate your entire response in {language_name}."`
- Language name mapping: `{"en": "English", "es": "Spanish", "fa": "Farsi/Persian"}`

### PDF RTL Support — `backend/templates/report.html`
- Add `lang` and `dir` attributes to `<html>` tag from template context
- Add RTL CSS overrides: `direction: rtl`, `text-align: right`, border/margin flips
- Add `@font-face` for Vazirmatn (Farsi font)
- Place font file at `backend/templates/fonts/Vazirmatn-Regular.woff2`

### PDF — `backend/app/pdf_service.py`
- Pass `lang_code`, `direction`, and `translations` dict to template context
- Translate section headings, rating labels, disclaimer text via translations dict

### Frontend — `frontend/utils.py`
- Add language selector in sidebar (top, above client list)
- `load_ui_strings(api_url, lang)` — fetch translations from backend, cache in session state
- All pages use `strings["ui"]["key"]` instead of hardcoded English

### Frontend — all page files
- Replace hardcoded English labels with translation lookups
- Pass `language` to report generation API call

---

## Sub-Phase 8D: Multi-Coach Support

### Auth Service — `backend/app/auth_service.py` (new)
- `validate_credentials(username, password) -> dict | None`
- Loads from `backend/data/coaches.json` if it exists; falls back to single env-var credentials for backward compat

### Coaches File — `backend/data/coaches.json` (new)
- Array of `{username, password, display_name}` objects
- Ships with default `admin` entry

### Config — `backend/app/config.py`
- Add `coaches_file: str = ""` setting (path to coaches.json; empty = legacy single-user mode)

### Models — `backend/app/models.py`
- Add `coach_username: str = ""` to `ClientRecord`
- Update `LoginResponse` to include `username` and `display_name`

### Client Isolation — `backend/app/client_service.py`
- `load_clients(coach_username=None)` — filter by coach when provided (legacy records with empty coach shown to all)
- `upsert_client()` — accept and store `coach_username`

### API — `backend/app/main.py`
- `GET /clients?coach=username` — pass filter to service
- `POST /auth/login` — use `auth_service.validate_credentials()`, return display name
- `POST /clients` — accept `coach_username` in request or header

### Frontend — `frontend/utils.py`
- `_refresh_client_list()` passes `coach=current_user` query param
- `require_login()` stores `display_name` from login response
- Show coach display name in sidebar header

---

## Sub-Phase 8E: Frontend UI/UX Polish

### Custom CSS — `frontend/utils.py`
- Add `inject_custom_css()` function called on every page via `st.markdown(<style>...)`:
  - Brand color palette (dark navy primary, accent blues)
  - Card-style metric containers (background, border, border-radius, subtle shadow)
  - Professional gradient header component
  - Better sidebar styling (background, spacing)
  - Improved form styling (borders, padding)
  - Step indicator visual refresh
  - Consistent button styling

### Dashboard Landing — `frontend/app.py`
- Replace plain 3-step text with styled card components
- When active client exists: show summary dashboard with metric cards (total tests taken, overall rating, last assessed date, progress summary)
- Show coach greeting with display name

### Page Improvements
- **Profile page**: Better form layout with grouped sections, visual hierarchy
- **Assessment page**: Result cards with range bars (from 8B), progress deltas (from 8A), cleaner grid
- **Report page**: Better tab styling, report preview with professional formatting

### Consistent Header/Footer — `frontend/utils.py`
- `render_page_header(title, subtitle)` — gradient header with branding
- `render_page_footer()` — subtle footer with app version

---

## Sub-Phase 8F: Additional POC+ Improvements

### Client Search — `frontend/utils.py`
- Text input above client list in sidebar
- Filter client buttons by name match (case-insensitive)

### Assessment History View — `frontend/pages/2_assessment.py`
- When client has 2+ assessments: show date dropdown to compare current vs. historical
- Side-by-side display of two assessment dates

### CSV Export — `backend/app/main.py`
- `GET /clients/{name}/history/csv` → StreamingResponse with columns: date, test_name, raw_value, unit, rating
- Download button in frontend report page

### Session Timeout — `frontend/utils.py`
- Store `login_time` in session state
- Check in `require_login()` — force re-login after 60 minutes

---

## Execution Order & Dependencies

```
8A (Progress Tracking) ─┬──> 8C (i18n — needs progress translations)
                        │
8B (Range Bars) ────────┼──> 8E (UI Polish — integrates bars + deltas)
                        │
8D (Multi-Coach) ───────┘──> 8E (UI shows coach name)
                                │
                                └──> 8F (Extras — last)
```

**Recommended order:** 8A → 8B → 8D → 8C → 8E → 8F

8A and 8B can be done in parallel. 8D is independent of 8B.

---

## Files Modified (Summary)

| File | Sub-Phases |
|------|-----------|
| `backend/app/models.py` | 8A, 8B, 8D |
| `backend/app/client_service.py` | 8A, 8D |
| `backend/app/main.py` | 8A, 8C, 8D, 8F |
| `backend/app/logic.py` | 8B |
| `backend/app/llm_service.py` | 8A, 8C |
| `backend/app/config.py` | 8D |
| `backend/app/pdf_service.py` | 8A, 8B, 8C |
| `backend/templates/report.html` | 8A, 8B, 8C |
| `backend/app/prompts/summary_prompt.txt` | 8A |
| `backend/app/prompts/workout_prompt.txt` | 8A |
| `frontend/app.py` | 8E |
| `frontend/utils.py` | 8A, 8B, 8C, 8D, 8E, 8F |
| `frontend/pages/1_client_profile.py` | 8C, 8E |
| `frontend/pages/2_assessment.py` | 8A, 8B, 8C, 8E, 8F |
| `frontend/pages/3_report.py` | 8A, 8C, 8E, 8F |

## New Files

| File | Sub-Phase |
|------|-----------|
| `backend/app/i18n_service.py` | 8C |
| `backend/app/auth_service.py` | 8D |
| `backend/data/i18n/en.json` | 8C |
| `backend/data/i18n/es.json` | 8C |
| `backend/data/i18n/fa.json` | 8C |
| `backend/data/coaches.json` | 8D |
| `backend/templates/fonts/Vazirmatn-Regular.woff2` | 8C |
| `backend/tests/test_progress.py` | 8A |

---

## Verification Plan

After each sub-phase:

1. **8A**: Run `poetry run pytest tests/ -v`. Manually: create client → assess → assess again → verify history stored and deltas shown. Check LLM narrative mentions progress. Check PDF shows previous values.
2. **8B**: Assess a client → verify colored range bars appear in UI under each result. Generate PDF → verify bars render in PDF. Test with inverted test (step test).
3. **8C**: Switch language to Spanish → verify all UI labels change. Generate report in Spanish → verify LLM output is Spanish. Generate PDF in Farsi → verify RTL layout and Farsi font renders.
4. **8D**: Add second coach to `coaches.json`. Login as each → verify each sees only their own clients. Legacy clients (no coach) visible to all.
5. **8E**: Visual inspection of all pages — cards, header, colors, spacing. Check mobile/narrow viewport.
6. **8F**: Test client search filter. Test CSV download. Test session timeout (set to 1 min for testing).

Run full suite after all sub-phases: `cd backend && poetry run pytest tests/ -v && poetry run ruff check app/ tests/ && poetry run mypy app/ --strict`
