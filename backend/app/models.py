from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ClientProfile(BaseModel):
    """Profile information for the client being assessed."""

    name: str
    age: int
    gender: Literal["male", "female"]
    goals: list[str]
    notes: Optional[str] = None


class AssessmentInput(BaseModel):
    """Raw test data submitted by the coach for calculation.

    The tests dict maps test_id to raw value, e.g. {"pushup": 25}.
    """

    client: ClientProfile
    tests: dict[str, float]


class MetricResult(BaseModel):
    """Calculated result for a single fitness test."""

    test_name: str
    raw_value: float
    unit: str
    rating: str  # "Excellent" | "Good" | "Average" | "Below Average" | "Poor"
    percentile: Optional[float] = None
    category: str  # "strength" | "flexibility" | "cardio" | "body_comp"
    description: str


class CalculationResponse(BaseModel):
    """Response from the /assess/calculate endpoint."""

    client: ClientProfile
    results: list[MetricResult]


class ReportRequest(BaseModel):
    """Request body for /assess/generate-report."""

    client: ClientProfile
    results: list[MetricResult]
    coach_notes: Optional[str] = None


class ReportResponse(BaseModel):
    """Full report including LLM-generated narrative."""

    client: ClientProfile
    results: list[MetricResult]
    llm_summary: str
    workout_suggestions: str
    generated_at: datetime


class TestInfo(BaseModel):
    """Metadata for a single test in the battery."""

    test_id: str
    test_name: str
    category: str
    unit: str
    description: str
