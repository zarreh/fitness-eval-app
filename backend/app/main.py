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

from app import llm_service, logic, pdf_service
from app.models import (
    AssessmentInput,
    CalculationResponse,
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
    version="0.1.0",
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
    )
    workout_suggestions = llm_service.generate_workout_suggestions(
        client=request.client,
        results=request.results,
    )

    return ReportResponse(
        client=request.client,
        results=request.results,
        llm_summary=llm_summary,
        workout_suggestions=workout_suggestions,
        generated_at=datetime.now(tz=timezone.utc),
        coach_name=request.coach_name,
        organization=request.organization,
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
