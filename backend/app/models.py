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

    # Body measurements — optional; used to auto-compute BMI, WHR, and body fat %.
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None

    # Workout preferences — used to tailor LLM workout suggestions.
    preferred_activities: list[str] = []
    equipment_available: list[str] = []


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
    thresholds: Optional[dict[str, float]] = None
    inverted: bool = False


class CalculationResponse(BaseModel):
    """Response from the /assess/calculate endpoint."""

    client: ClientProfile
    results: list[MetricResult]


class ProgressDelta(BaseModel):
    """Change indicator for a single test between two assessments."""

    test_name: str
    previous_value: float
    current_value: float
    previous_rating: str
    current_rating: str
    direction: Literal["improved", "declined", "unchanged"]
    delta: float  # current - previous (signed)
    unit: str = ""


class AssessmentSnapshot(BaseModel):
    """A single timestamped assessment for history tracking."""

    results: list[MetricResult]
    assessed_at: datetime


class ReportRequest(BaseModel):
    """Request body for /assess/generate-report."""

    client: ClientProfile
    results: list[MetricResult]
    progress: Optional[list[ProgressDelta]] = None
    coach_notes: Optional[str] = None
    coach_name: Optional[str] = None
    organization: Optional[str] = None
    language: str = "en"


class ReportResponse(BaseModel):
    """Full report including LLM-generated narrative."""

    client: ClientProfile
    results: list[MetricResult]
    progress: Optional[list[ProgressDelta]] = None
    llm_summary: str
    workout_suggestions: str
    generated_at: datetime
    coach_name: Optional[str] = None
    organization: Optional[str] = None
    language: str = "en"
    # Assessment history snapshots for chart generation (optional; set by frontend
    # when calling /assess/generate-pdf so PDF can embed time-series charts).
    assessment_history: list[dict] = []


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
    username: str = ""
    display_name: str = ""


class ClientRecord(BaseModel):
    """A saved client profile stored on the backend."""

    name: str
    profile: ClientProfile
    saved_at: datetime
    last_assessment: Optional[list[MetricResult]] = None
    assessed_at: Optional[datetime] = None
    assessment_history: list[AssessmentSnapshot] = []
    coach_username: str = ""


class SignupRequest(BaseModel):
    """Credentials and display name submitted to /auth/signup."""

    username: str
    password: str
    display_name: str


class SignupResponse(BaseModel):
    """Response from /auth/signup."""

    success: bool
    username: str = ""
    display_name: str = ""
    error: str = ""


class BodyMeasurementInput(BaseModel):
    """Input for logging a new body measurement snapshot (Phase 4)."""

    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None


class BodyMeasurementRecord(BaseModel):
    """A stored body measurement snapshot with computed values (Phase 4)."""

    id: int
    measured_at: datetime
    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_pct: Optional[float] = None
    body_fat_rating: Optional[str] = None
    fat_mass_kg: Optional[float] = None
    lean_mass_kg: Optional[float] = None
