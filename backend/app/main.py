"""FastAPI application entry point.

Defines the REST API endpoints. Handlers are thin — all business logic
is delegated to logic.py, llm_service.py, pdf_service.py, and db_service.py.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import (
    db_service,
    i18n_service,
    llm_service,
    logic,
    pdf_service,
)
from app.database import AsyncSessionLocal, create_tables, get_db
from app.models import (
    AssessmentInput,
    AssessmentSnapshot,
    BodyMeasurementInput,
    BodyMeasurementRecord,
    CalculationResponse,
    ClientProfile,
    ClientRecord,
    LoginRequest,
    LoginResponse,
    MetricResult,
    ReportRequest,
    ReportResponse,
    SignupRequest,
    SignupResponse,
    TestInfo,
)

# Import ORM models so Base.metadata is populated before create_tables() runs.
import app.db_models  # noqa: F401
import app.migrate_json_to_db as _migrate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — create tables and run JSON→SQLite migration."""
    await create_tables()
    async with AsyncSessionLocal() as db:
        await _migrate.run_migration_if_needed(db)
    yield


app = FastAPI(
    title="Fitness Evaluation API",
    description=(
        "B2B fitness assessment platform. "
        "Coach submits raw test data → ratings calculated "
        "→ LLM generates narrative → PDF report."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production; open for POC / React swap
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── System ────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Confirm the API is running."""
    return {"status": "ok"}


@app.get("/i18n/{lang}", tags=["system"])
async def get_translations(lang: str) -> dict[str, object]:
    """Return the UI translation bundle for the given language code.

    Supported: ``en``, ``es``, ``fa``. Falls back to English for unknown codes.
    """
    return i18n_service.load_translations(lang)


@app.get("/i18n", tags=["system"])
async def list_languages() -> list[dict[str, str]]:
    """Return the list of supported language options."""
    return i18n_service.get_supported_languages()


# ── Auth ──────────────────────────────────────────────────────────────────────


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(
    request: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """Validate coach credentials against the SQLite coaches table.

    Returns HTTP 401 if the username is not found or the password is wrong.
    """
    coach = await db_service.validate_coach_credentials(
        db, request.username, request.password
    )
    if not coach:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return LoginResponse(
        authenticated=True,
        username=coach["username"],
        display_name=coach["display_name"],
    )


@app.post("/auth/signup", response_model=SignupResponse, tags=["auth"])
async def signup(
    request: SignupRequest, db: AsyncSession = Depends(get_db)
) -> SignupResponse:
    """Register a new coach account.

    Validates username format (``^[a-zA-Z0-9_]{3,32}$``) and minimum
    password length (8 chars).  Returns HTTP 409 if the username is already
    taken, HTTP 422 if validation fails.
    """
    import re

    if not re.fullmatch(r"[a-zA-Z0-9_]{3,32}", request.username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3–32 characters: letters, digits, underscores only.",
        )
    if len(request.password) < 8:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters.",
        )
    if not request.display_name.strip():
        raise HTTPException(status_code=422, detail="Display name is required.")

    existing = await db_service.get_coach_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken.")

    coach = await db_service.create_coach(
        db,
        username=request.username,
        password=request.password,
        display_name=request.display_name.strip(),
    )
    return SignupResponse(
        success=True,
        username=coach["username"],
        display_name=coach["display_name"],
    )


# ── Clients ───────────────────────────────────────────────────────────────────


@app.get("/clients", response_model=list[ClientRecord], tags=["clients"])
async def list_clients(
    coach: str, db: AsyncSession = Depends(get_db)
) -> list[ClientRecord]:
    """Return saved client records for the given coach.

    ``coach`` (the coach's username) is required — clients are strictly
    isolated per coach.
    """
    return await db_service.list_clients_for_coach(db, coach)


@app.post("/clients", response_model=ClientRecord, tags=["clients"])
async def save_client(
    profile: ClientProfile,
    coach: str,
    db: AsyncSession = Depends(get_db),
) -> ClientRecord:
    """Create or update a client record (upsert by coach + name).

    ``coach`` is required and determines client ownership.
    """
    try:
        return await db_service.upsert_client(db, profile, coach)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/clients/{name}", tags=["clients"])
async def remove_client(
    name: str, coach: str, db: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    """Delete a client by coach + name. Returns ``{deleted: false}`` if not found."""
    deleted = await db_service.delete_client(db, coach, name)
    return {"deleted": deleted}


@app.post("/clients/{name}/assessment", response_model=ClientRecord, tags=["clients"])
async def save_client_assessment(
    name: str,
    results: list[MetricResult],
    coach: str,
    db: AsyncSession = Depends(get_db),
) -> ClientRecord:
    """Attach the latest assessment results to an existing client record.

    Call this after ``/assess/calculate`` to persist results for future
    sessions. Returns HTTP 404 if the client does not exist.
    """
    try:
        return await db_service.save_assessment(db, coach, name, results)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/clients/{name}/history",
    response_model=list[AssessmentSnapshot],
    tags=["clients"],
)
async def get_client_history(
    name: str, coach: str, db: AsyncSession = Depends(get_db)
) -> list[AssessmentSnapshot]:
    """Return full assessment history for a client (newest first).

    Returns HTTP 404 if the client does not exist for this coach.
    """
    history = await db_service.get_assessment_history(db, coach, name)
    if not history:
        raise HTTPException(status_code=404, detail=f"Client '{name}' not found.")
    return history


@app.get("/clients/{name}/history/csv", tags=["clients"])
async def export_client_history_csv(
    name: str, coach: str, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Export a client's full assessment history as a downloadable CSV.

    Columns: date, test_name, raw_value, unit, rating, category.
    Returns HTTP 404 if the client does not exist for this coach.
    """
    history = await db_service.get_assessment_history(db, coach, name)
    if not history:
        raise HTTPException(status_code=404, detail=f"Client '{name}' not found.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "test_name", "raw_value", "unit", "rating", "category"])
    for snapshot in history:
        date_str = snapshot.assessed_at.strftime("%Y-%m-%d %H:%M")
        for result in snapshot.results:
            writer.writerow([
                date_str,
                result.test_name,
                result.raw_value,
                result.unit,
                result.rating,
                result.category,
            ])

    filename = f"history_{name.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get(
    "/clients/{name}/measurements",
    response_model=list[BodyMeasurementRecord],
    tags=["clients"],
)
async def list_measurements(
    name: str, coach: str, db: AsyncSession = Depends(get_db)
) -> list[BodyMeasurementRecord]:
    """Return all body-measurement snapshots for a client, newest first.

    Returns an empty list (not 404) if no measurements have been logged yet.
    Returns HTTP 404 if the client does not exist for this coach.
    """
    client_row = await db_service._get_client_row(db, coach, name)
    if client_row is None:
        raise HTTPException(status_code=404, detail=f"Client '{name}' not found.")
    return await db_service.get_measurements(db, coach, name)


@app.post(
    "/clients/{name}/measurements",
    response_model=BodyMeasurementRecord,
    tags=["clients"],
)
async def log_measurement(
    name: str,
    measurement: BodyMeasurementInput,
    coach: str,
    db: AsyncSession = Depends(get_db),
) -> BodyMeasurementRecord:
    """Log a new body-measurement snapshot for an existing client.

    Auto-computes BMI, body fat % (US Navy formula), fat mass, and lean mass
    from the submitted values combined with the client's stored height.
    Returns HTTP 404 if the client does not exist for this coach.
    """
    try:
        return await db_service.add_measurement(db, coach, name, measurement)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Tests & Assessment ────────────────────────────────────────────────────────


@app.get("/tests/battery", response_model=list[TestInfo], tags=["assessment"])
async def get_test_battery() -> list[TestInfo]:
    """Return metadata for all tests in the current assessment battery."""
    return logic.get_test_battery()


@app.post("/assess/calculate", response_model=CalculationResponse, tags=["assessment"])
async def calculate(input: AssessmentInput) -> CalculationResponse:
    """Accept raw test scores and return ratings from the normative lookup tables.

    The logic engine performs all calculations. No LLM is involved here.
    """
    try:
        results = logic.calculate_all_tests(input)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CalculationResponse(client=input.client, results=results)


@app.post("/assess/generate-report", response_model=ReportResponse, tags=["assessment"])
async def generate_report(request: ReportRequest) -> ReportResponse:
    """Generate an LLM narrative for a set of pre-calculated results.

    The LLM receives only MetricResult objects — never raw scores.
    If the LLM is unavailable, fallback text is returned so the report
    can still be generated.
    """
    llm_summary = llm_service.generate_coach_summary(
        client=request.client,
        results=request.results,
        coach_notes=request.coach_notes,
        progress=request.progress,
        language=request.language,
    )
    workout_suggestions = llm_service.generate_workout_suggestions(
        client=request.client,
        results=request.results,
        progress=request.progress,
        language=request.language,
    )

    return ReportResponse(
        client=request.client,
        results=request.results,
        progress=request.progress,
        llm_summary=llm_summary,
        workout_suggestions=workout_suggestions,
        generated_at=datetime.now(tz=timezone.utc),
        coach_name=request.coach_name,
        organization=request.organization,
        language=request.language,
    )


@app.post("/assess/generate-pdf", tags=["assessment"])
async def generate_pdf(report: ReportResponse) -> Response:
    """Convert a full ReportResponse to a downloadable PDF.

    Returns a streaming PDF response with the appropriate content-type header.
    """
    try:
        pdf_bytes = pdf_service.render_report_pdf(report)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {exc}",
        ) from exc

    filename = f"fitness_report_{report.client.name.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
