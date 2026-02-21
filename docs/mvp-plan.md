# MVP Implementation Plan — fitness-eval-app

## Context

The app is a fully functional POC (Phase 8F complete) with FastAPI backend, Streamlit frontend,
multi-coach JSON-file storage, multi-language (EN/ES/FA), and assessment history tracking.
This plan transitions it to a proper MVP addressing 16 specific feedback items:
better data architecture (SQLite), coach self-service, body composition tracking,
richer progress visualization, RTL fixes, and smarter LLM usage.

---

## Phases (ordered by dependency)

### Phase 1 — Quick Fixes (no dependencies)
**Items: #1 American English, #16 Farsi translation fixes**

- `frontend/utils.py` line 17: change `"flag": "🇬🇧"` → `"flag": "🇺🇸"`
- `backend/data/i18n/fa.json`: fix test name translations — push-up → **شنا سوئدی**,
  plank → **تخته**, wall sit → **نشست دیواری**, sit and reach → **نشست و رسش**,
  plus any other UI strings that read awkwardly in Farsi

---

### Phase 2 — SQLite Database (core infrastructure)
**Items: #2 strict client isolation, #3 proper data relations, #7 trackable measurements**

#### New dependencies (backend `pyproject.toml`)
```
sqlalchemy[asyncio] ^2, aiosqlite ^0.20, passlib[bcrypt] ^1
```

#### New files
- `backend/app/database.py` — async engine (`sqlite+aiosqlite:///data/fitness.db`),
  `AsyncSessionLocal`, `Base`, `create_tables()`, `get_db()` FastAPI dependency
- `backend/app/db_models.py` — 4 SQLAlchemy ORM tables:
  - `coaches(id PK, username UNIQUE, hashed_password, display_name, created_at)`
  - `clients(id PK, coach_id FK→coaches.CASCADE, name, age, gender, goals JSON,
    notes, height_cm, preferred_activities JSON, equipment_available JSON, saved_at)`
    — UNIQUE constraint on `(coach_id, name)` enforces strict isolation
  - `body_measurements(id PK, client_id FK→clients.CASCADE, measured_at,
    weight_kg, waist_cm, hip_cm, neck_cm, bmi, body_fat_pct, body_fat_rating,
    fat_mass_kg, lean_mass_kg)`
  - `assessments(id PK, client_id FK→clients.CASCADE, assessed_at, results_json TEXT)`
- `backend/app/db_service.py` — replaces `client_service.py` + `auth_service.py`;
  async CRUD functions: `get_coach_by_username`, `create_coach`,
  `validate_coach_credentials` (bcrypt), `list_clients_for_coach`, `get_client`,
  `upsert_client`, `delete_client`, `add_measurement`, `get_measurements`,
  `save_assessment`, `get_assessments`
- `backend/app/migrate_json_to_db.py` — one-time migration:
  reads `coaches.json` → hashed passwords → `coaches` table;
  reads `clients.json` → `clients` + `body_measurements` + `assessments` tables;
  skips if coaches table already has rows

#### Modified files
- `backend/app/main.py`:
  - Add `@app.on_event("startup")` → `create_tables()` + `run_migration_if_needed()`
  - Inject `Depends(get_db)` into all client/auth endpoints
  - `coach` query param now **required** on all `/clients/*` endpoints
  - Add `_client_to_record()` converter: ORM `Client` + latest `BodyMeasurement` +
    `list[Assessment]` → existing `ClientRecord` Pydantic shape (backward compat)
- `backend/app/models.py`: add `BodyMeasurementInput`, `BodyMeasurementRecord` Pydantic models
- `docker-compose.yml`: no volume changes needed (fitness.db lands in same `/app/data/` mount)

#### Key design decisions
- `results_json` on `assessments` stores the full `list[MetricResult]` as JSON blob —
  preserves existing Pydantic shape without a complex per-metric table
- Legacy clients (migrated from JSON with empty `coach_username`) assigned to first coach
- `weight_kg`, `waist_cm`, `hip_cm`, `neck_cm` move from `ClientProfile` to `body_measurements`;
  `height_cm` stays on `clients` (static)

---

### Phase 3 — Coach Signup
**Items: #4 signup page**
**Depends on: Phase 2**

#### Backend
- `backend/app/models.py`: add `SignupRequest(username, password, display_name)`,
  `SignupResponse(success, username, display_name, error)`
- `backend/app/main.py`: `POST /auth/signup` — validates username regex
  `^[a-zA-Z0-9_]{3,32}$`, min 8 char password, HTTP 409 on duplicate username,
  calls `db_service.create_coach()`
- `POST /auth/login`: updated to query SQLite + bcrypt verify via `db_service`

#### Frontend
- New `frontend/pages/0_signup.py` — centered form (display_name, username,
  password, confirm); success → "Account created, sign in"; 409 → "username taken";
  redirect to app.py if already logged in
- `frontend/utils.py`: add "New coach? Create an account" link below login form
- i18n: add `signup_*` keys to `en.json`, `es.json`, `fa.json`

---

### Phase 4 — Body Measurements Time Series
**Items: #7 weight/waist/hip trackable, #9 body fat + weight as progress metrics**
**Depends on: Phase 2, Phase 5**

#### Backend
- `backend/app/main.py`:
  - `GET /clients/{name}/measurements?coach=` → list measurements newest first
  - `POST /clients/{name}/measurements?coach=` → logs new snapshot, auto-computes
    BMI, body fat % (US Navy), fat_mass_kg, lean_mass_kg via `db_service.add_measurement()`

#### Frontend (`frontend/pages/1_client_profile.py`)
- Below existing profile form (only when client is loaded): "Body Measurements" section
- Expander "Log New Measurement" with form: weight, waist, hip, neck inputs
  (neck includes help text: "Required for body fat % estimate")
- Measurement history as `st.dataframe`: Date, Weight, Waist, Hip, Neck, BMI, Body Fat %, Rating, Fat Mass, Lean Mass

---

### Phase 5 — Body Fat % Formula
**Items: #8 body fat estimation, #9 body fat as progress metric**
**Depends on: Phase 2 (for `neck_cm` field)**

#### Backend (`backend/app/logic.py`)
New functions:
```python
def compute_body_fat_pct(gender, height_cm, waist_cm, neck_cm, hip_cm=None) -> float | None:
    # Male:   86.010 × log10(waist - neck) - 70.041 × log10(height) + 36.76
    # Female: 163.205 × log10(waist + hip - neck) - 97.684 × log10(height) - 78.387
    # Returns None if waist <= neck (invalid log input)

def classify_body_fat(body_fat_pct, gender, age) -> str:
    # ACE classification with age adjustment (+1% per decade over 30)
    # Male tiers: <6 Poor, 6-13 Excellent, 13-17 Very Good, 17-24 Good, 24-30 Fair, >30 Poor
    # Female: <14 Poor, 14-20 Excellent, 20-24 Very Good, 24-31 Good, 31-38 Fair, >38 Poor
```

- Add `neck_cm: Optional[float] = None` to `ClientProfile` in `models.py`
- Add `body_fat` to `TEST_REGISTRY` (computed=True, inverted=True)
- In `calculate_all_tests()`: auto-compute body fat when `height_cm + waist_cm + neck_cm` present
- New `backend/data/norms/body_fat.json` (documents thresholds by gender/age for range bar)
- Frontend `1_client_profile.py`: add neck_cm input in body measurements section

---

### Phase 6 — Progress Bars with Threshold Numbers + RTL Fix
**Items: #10 app progress bars, #11 PDF progress bars, #14 RTL bar direction fix**
**Depends on: none (purely visual)**

#### Frontend (`frontend/utils.py` — `render_range_bar_html()`)
- Add `is_rtl: bool = False` parameter
- Below the colored zone bar: add a threshold-number row with absolute-positioned
  spans at cumulative zone widths: shows actual values (e.g. `17`, `22`, `29`, `36`)
- Inside each colored zone: abbreviated label ("Poor", "Fair", "Good", "V.Good", "Exc.")
- **RTL fix**: when `is_rtl=True`, reverse `zones` list order AND flip
  `marker_pct = 100.0 - marker_pct`
- Callers in `2_assessment.py` pass `is_rtl = st.session_state.get("lang") == "fa"`

#### Backend PDF (`backend/app/pdf_service.py` — `_compute_range_bar_data()`)
- Add `direction: str = "ltr"` parameter
- Return `threshold_labels: list[{pct, val}]` — cumulative % positions + formatted values
- Return `label_abbr` on each zone dict
- When `direction == "rtl"`: reverse zones list, flip `marker_pct = 100 - marker_pct`
- `render_report_pdf()` passes `direction` from i18n bundle

#### PDF template (`backend/templates/report.html`)
- Replace 3-label "Poor | Good | Excellent" footer with:
  - Zone name abbrs centered inside each colored zone div
  - Threshold value labels absolutely positioned at zone boundaries (small grey text)
- RTL handled server-side in `pdf_service.py` (zones already reversed before template render)

---

### Phase 7 — Numeric Progress Indicators
**Items: #12 progress indicators show delta numbers with color**
**Depends on: none**

- `backend/app/models.py` `ProgressDelta`: add `unit: str = ""`
- `backend/app/client_service.py` (and DB equivalent): set `unit` from `curr.unit` in
  `_compute_progress_deltas()`
- `frontend/pages/2_assessment.py` `_delta_indicator_html()`: change from
  `"▲ Improved"` → `"▲ +7 reps (Good → Very Good)"` in green;
  `"▼ -4 bpm (Good → Fair)"` in red; `"— Unchanged"` in grey
- `backend/templates/report.html`: update delta column to show sign + value + unit +
  rating transition (when rating changed)

---

### Phase 8 — Progress Charts
**Items: #13 progress graphs in app and PDF**
**Depends on: Phase 2 (for rich history)**

#### New dependencies
```
frontend/pyproject.toml: plotly ^5, kaleido ^0.2
backend/pyproject.toml:  plotly ^5, kaleido ^0.2
```

#### Frontend (`frontend/utils.py`)
- New `render_metric_chart(test_name, history, thresholds, inverted, unit)`:
  Plotly `go.Figure` line chart + `add_hrect()` zone background bands (same colors as
  range bar); only renders when metric appears in 2+ history snapshots
- `frontend/pages/2_assessment.py`: add "📈 Progress Charts" expander (shown when
  `len(history) >= 2`); iterates results and calls `render_metric_chart()` for each
  metric that has `thresholds`

#### PDF (`backend/app/pdf_service.py`)
- New `_render_chart_png(test_name, history, thresholds, inverted, unit) -> str | None`:
  builds same Plotly figure, exports via `plotly.io.to_image()`, returns base64 PNG;
  returns `None` gracefully if kaleido unavailable
- `render_report_pdf()`: builds `chart_images: dict[test_name, base64_str]`, passes to template
- `backend/templates/report.html`: after each result row, embed chart if available:
  `<img src="data:image/png;base64,{{ chart_images[result.test_name] }}">`

---

### Phase 9 — Enhanced LLM Workout Preferences
**Items: #15 workout suggestions consider trainee preferences**
**Depends on: Phase 2 (DB columns)**

- `backend/app/models.py` `ClientProfile`: add `preferred_activities: list[str] = []`,
  `equipment_available: list[str] = []`
- `frontend/pages/1_client_profile.py`: add two `st.multiselect` inputs for activities
  (gym, outdoor, home, swimming, yoga, HIIT, cycling, pilates) and equipment
  (barbell, dumbbells, resistance_bands, kettlebell, pull-up bar, cable machine, none)
- `backend/app/prompts/workout_prompt.txt`: add section:
  ```
  CLIENT PREFERENCES:
  - Preferred activities: {preferred_activities}
  - Equipment available: {equipment_available}
  Prioritize these when designing the workout. Only suggest exercises
  feasible with the listed equipment.
  ```
- `backend/app/llm_service.py` `generate_workout_suggestions()`: format and inject
  `preferred_activities` + `equipment_available` from `ClientProfile`
- i18n: add `profile_preferred_activities`, `profile_equipment` keys

---

## New API Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /auth/signup` | **New** |
| `POST /auth/login` | Now uses SQLite + bcrypt |
| `GET /clients` | `coach` required, strict isolation |
| `POST /clients` | `coach` required |
| `DELETE /clients/{name}` | `coach` required + ownership check |
| `GET /clients/{name}/measurements` | **New** |
| `POST /clients/{name}/measurements` | **New** |

---

## Critical Files

| File | Changes |
|------|---------|
| `backend/app/database.py` | **New** — async engine + session |
| `backend/app/db_models.py` | **New** — 4 ORM tables |
| `backend/app/db_service.py` | **New** — replaces client_service + auth_service |
| `backend/app/migrate_json_to_db.py` | **New** — one-time JSON→SQLite migration |
| `backend/app/models.py` | Add `neck_cm`, `preferred_activities`, `equipment_available` to `ClientProfile`; add `unit` to `ProgressDelta`; add `BodyMeasurementInput`, `BodyMeasurementRecord`, `SignupRequest` |
| `backend/app/logic.py` | Add `compute_body_fat_pct()`, `classify_body_fat()`, body_fat test registry entry, auto-compute in `calculate_all_tests()` |
| `backend/app/main.py` | Startup hook, `Depends(get_db)` injection, new endpoints |
| `backend/app/prompts/workout_prompt.txt` | Add preferences section |
| `backend/app/pdf_service.py` | RTL zone flip, threshold labels, chart PNG embedding |
| `backend/templates/report.html` | Zone labels with numbers, chart images, numeric deltas |
| `backend/data/norms/body_fat.json` | **New** — body fat thresholds |
| `backend/data/i18n/fa.json` | Fix push-up (شنا سوئدی) + other Farsi terms |
| `frontend/utils.py` | Flag fix (line 17), RTL bar fix, threshold numbers in range bar, `render_metric_chart()` |
| `frontend/pages/0_signup.py` | **New** — signup page |
| `frontend/pages/1_client_profile.py` | Measurement history section, neck + preferences inputs |
| `frontend/pages/2_assessment.py` | Numeric delta indicators, progress charts expander |
| `frontend/pyproject.toml` | Add plotly, kaleido |
| `backend/pyproject.toml` | Add sqlalchemy[asyncio], aiosqlite, passlib[bcrypt], plotly, kaleido |

---

## Execution Order

```
Phase 1 (quick fixes) ──┐
Phase 5 (body fat)   ───┤
Phase 6 (bar numbers)───┤──> Phase 2 (SQLite) ──> Phase 3 (signup)
Phase 7 (delta nums) ───┘         │                Phase 4 (measurements)
                                  └──────────────> Phase 8 (charts)
                                                   Phase 9 (workout prefs)
```

Phases 1, 5, 6, 7 can be implemented in parallel with Phase 2.
Phases 3, 4, 8, 9 require Phase 2 to be complete first.

---

## Verification

1. **Start stack**: `docker compose up --build`
2. **Signup flow**: open http://localhost:8501, click "Create an account", register two coaches,
   confirm each can log in; verify coach A cannot see coach B's clients
3. **Body fat**: load a client with height/weight/waist/hip/neck, run assessment,
   confirm Body Fat % metric appears in results with rating and range bar
4. **Measurements**: log multiple body measurements on different dates for a client,
   confirm history table shows all entries with computed BMI, BF%, fat/lean mass
5. **Progress bars**: verify threshold numbers (e.g. 17 | 22 | 29 | 36) appear below bar
   and zone abbreviations inside colored zones
6. **Progress indicators**: run two assessments for same client, confirm delta shows
   e.g. "▲ +8 reps (Good → Very Good)" in green
7. **Charts**: with 2+ assessments, open "📈 Progress Charts" expander — verify Plotly charts
   with zone backgrounds appear
8. **RTL bar**: switch to Farsi, run assessment, verify Poor is on right and Excellent on left
9. **PDF**: generate PDF and verify: threshold numbers on range bars, numeric deltas,
   charts embedded (if kaleido available)
10. **Workout prefs**: set preferred activities = "swimming, outdoor" for a client,
    generate workout suggestions, verify LLM output reflects those preferences
11. **Tests**: `cd backend && poetry run pytest tests/ -v` — all existing tests pass
