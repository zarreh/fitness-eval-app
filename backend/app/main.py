"""FastAPI application entry point.

Defines the REST API endpoints. Handlers are thin — all business logic
is delegated to logic.py, llm_service.py, and pdf_service.py.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app import (
    auth_service,
    client_service,
    i18n_service,
    llm_service,
    logic,
    pdf_service,
)
from app.models import (
    AssessmentInput,
    AssessmentSnapshot,
    CalculationResponse,
    ClientProfile,
    ClientRecord,
    LoginRequest,
    LoginResponse,
    MetricResult,
    ReportRequest,
    ReportResponse,
    TestInfo,
)

app = FastAPI(
    title="Fitness Evaluation API",
    description=(
        "B2B fitness assessment platform. "
        "Coach submits raw test data → ratings calculated "
        "→ LLM generates narrative → PDF report."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production; open for POC / React swap
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(request: LoginRequest) -> LoginResponse:
    """Validate coach credentials.

    Checks ``coaches.json`` first, then falls back to env-var credentials.
    Returns HTTP 401 if credentials do not match.
    """
    coach = auth_service.validate_credentials(request.username, request.password)
    if not coach:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return LoginResponse(
        authenticated=True,
        username=coach["username"],
        display_name=coach["display_name"],
    )


@app.get("/clients", response_model=list[ClientRecord], tags=["clients"])
async def list_clients(coach: str | None = None) -> list[ClientRecord]:
    """Return saved client records, optionally filtered by coach username."""
    return client_service.load_clients(coach_username=coach)


@app.post("/clients", response_model=ClientRecord, tags=["clients"])
async def save_client(
    profile: ClientProfile, coach: str | None = None
) -> ClientRecord:
    """Create or update a client record (upsert by name).

    Accepts a ``ClientProfile`` directly; the backend generates ``saved_at``.
    The optional ``coach`` query param assigns ownership.
    """
    return client_service.upsert_client(profile, coach_username=coach or "")


@app.delete("/clients/{name}", tags=["clients"])
async def remove_client(name: str) -> dict[str, bool]:
    """Delete a client by name. Returns {deleted: false} if not found."""
    deleted = client_service.delete_client(name)
    return {"deleted": deleted}


@app.post("/clients/{name}/assessment", response_model=ClientRecord, tags=["clients"])
async def save_client_assessment(
    name: str, results: list[MetricResult]
) -> ClientRecord:
    """Attach the latest assessment results to an existing client record.

    Call this after /assess/calculate to persist results for future sessions.
    Returns HTTP 404 if the client does not exist (save the profile first).
    """
    try:
        return client_service.save_assessment(name, results)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/clients/{name}/history",
    response_model=list[AssessmentSnapshot],
    tags=["clients"],
)
async def get_client_history(name: str) -> list[AssessmentSnapshot]:
    """Return full assessment history for a client (newest first).

    Returns HTTP 404 if the client does not exist.
    """
    records = client_service.load_clients()
    for r in records:
        if r.name == name:
            return r.assessment_history
    raise HTTPException(status_code=404, detail=f"Client '{name}' not found.")


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
