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

    # Body measurements — optional; used to auto-compute BMI and WHR.
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None


class AssessmentInput(BaseModel):
    """Raw test data submitted by the coach for calculation.

    The tests dict maps test_id to raw value, e.g. {"pushup": 25}.
    BMI and WHR are computed automatically from ClientProfile body measurements
    when the relevant fields are present — do not include them in tests.
    """

    client: ClientProfile
    tests: dict[str, float]


class MetricResult(BaseModel):
    """Calculated result for a single fitness test."""

    test_name: str
    raw_value: float
    unit: str
    rating: str  # "Excellent" | "Very Good" | "Good" | "Fair" | "Poor"
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
    coach_name: Optional[str] = None
    organization: Optional[str] = None


class ReportResponse(BaseModel):
    """Full report including LLM-generated narrative."""

    client: ClientProfile
    results: list[MetricResult]
    llm_summary: str
    workout_suggestions: str
    generated_at: datetime
    coach_name: Optional[str] = None
    organization: Optional[str] = None


class TestInfo(BaseModel):
    """Metadata for a single test in the battery."""

    test_id: str
    test_name: str
    category: str
    unit: str
    description: str
    computed: bool = False  # True for tests derived from client measurements (BMI, WHR)


class LoginRequest(BaseModel):
    """Credentials submitted to /auth/login."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Response from /auth/login."""

    authenticated: bool


class ClientRecord(BaseModel):
    """A saved client profile stored on the backend."""

    name: str
    profile: ClientProfile
    saved_at: datetime
    last_assessment: Optional[list[MetricResult]] = None
    assessed_at: Optional[datetime] = None
