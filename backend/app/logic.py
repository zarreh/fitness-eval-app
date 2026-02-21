"""Fitness assessment calculation engine.

All quantitative work happens here: normative data loading, rating lookups,
and MetricResult construction. The LLM never touches this layer.
"""

import json
from pathlib import Path

from app.models import AssessmentInput, ClientProfile, MetricResult, TestInfo

NORMS_DIR = Path(__file__).parent.parent / "data" / "norms"

# Rating tiers in descending order — used for top-down threshold checking.
# Source: ACSM's Guidelines for Exercise Testing and Prescription, 11th Edition.
_RATING_ORDER = ["excellent", "very_good", "good", "fair", "poor"]

_RATING_DISPLAY = {
    "excellent": "Excellent",
    "very_good": "Very Good",
    "good": "Good",
    "fair": "Fair",
    "poor": "Poor",
}

# Registry of all tests in the battery.
# Computed tests (BMI, WHR) are derived from ClientProfile body measurements.
TEST_REGISTRY: dict[str, TestInfo] = {
    "pushup": TestInfo(
        test_id="pushup",
        test_name="Push-up Test",
        category="strength",
        unit="reps",
        description=(
            "Measures upper-body push strength and muscular endurance. "
            "Count maximum repetitions with proper form. "
            "Males: standard push-up. Females: modified (knee) push-up."
        ),
    ),
    "wall_sit": TestInfo(
        test_id="wall_sit",
        test_name="Wall Sit Test",
        category="strength",
        unit="seconds",
        description=(
            "Measures lower-body isometric endurance. "
            "Hold a seated position against a wall (90° knee angle) "
            "as long as possible."
        ),
    ),
    "plank": TestInfo(
        test_id="plank",
        test_name="Forearm Plank Test",
        category="strength",
        unit="seconds",
        description=(
            "Measures core stability and endurance. "
            "Hold a forearm plank with straight body alignment until form breaks."
        ),
    ),
    "sit_and_reach": TestInfo(
        test_id="sit_and_reach",
        test_name="Canadian Trunk Forward Flexion",
        category="flexibility",
        unit="cm",
        description=(
            "Measures hamstring and lower-back flexibility. "
            "Sit with feet flat against box, reach forward slowly. "
            "Best of two trials, hold 2 seconds."
        ),
    ),
    "zipper": TestInfo(
        test_id="zipper",
        test_name="Zipper (Back Scratch) Test",
        category="flexibility",
        unit="cm",
        description=(
            "Measures shoulder and upper-arm flexibility. "
            "Reach one hand over shoulder and one behind back. "
            "Positive = overlap (cm); negative = gap (cm)."
        ),
    ),
    "step_test": TestInfo(
        test_id="step_test",
        test_name="YMCA 3-Minute Step Test",
        category="cardio",
        unit="bpm",
        description=(
            "Measures cardiovascular fitness via recovery heart rate. "
            "Step on/off a 12-inch bench at 96 bpm (24 steps/min) for 3 minutes. "
            "Count pulse for 1 minute immediately after. Lower BPM = better."
        ),
    ),
    "bmi": TestInfo(
        test_id="bmi",
        test_name="Body Mass Index (BMI)",
        category="body_comp",
        unit="kg/m²",
        description=(
            "Computed from client height and weight. "
            "WHO classification: Normal 18.5–24.9, Overweight 25–29.9, Obese ≥ 30."
        ),
        computed=True,
    ),
    "waist_to_hip": TestInfo(
        test_id="waist_to_hip",
        test_name="Waist-to-Hip Ratio",
        category="body_comp",
        unit="ratio",
        description=(
            "Computed from client waist and hip circumference. "
            "WHO risk thresholds: Male ≥ 0.90, Female ≥ 0.85 = increased risk."
        ),
        computed=True,
    ),
}


def load_norms(test_id: str) -> dict:  # type: ignore[type-arg]
    """Load normative data JSON for a given test.

    Args:
        test_id: The test identifier (e.g. "pushup").

    Returns:
        Parsed JSON dict containing test metadata and norms tables.

    Raises:
        ValueError: If no norms file exists for the given test_id.
    """
    path = NORMS_DIR / f"{test_id}.json"
    if not path.exists():
        raise ValueError(f"No normative data found for test: '{test_id}'")
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def get_age_bracket(age: int) -> str:
    """Map an age to the closest normative data bracket.

    Args:
        age: Client age in years. Values below 20 are treated as "20-29".
             Values 70+ are treated as "60-69" (highest available bracket).

    Returns:
        Age bracket string matching keys in the norms JSON (e.g. "30-39").
    """
    if age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    elif age < 60:
        return "50-59"
    else:
        return "60-69"


def get_rating(
    value: float,
    thresholds: dict[str, float],
    inverted: bool = False,
) -> str:
    """Determine the rating tier for a given value against a threshold table.

    For standard tests (higher = better): checks tiers top-down (excellent first),
    returns the highest tier whose threshold is met (value >= threshold).

    For inverted tests (lower = better, e.g. heart rate): returns the highest tier
    whose threshold is not exceeded (value <= threshold).

    Args:
        value: The raw test result.
        thresholds: Dict mapping tier keys to threshold values for that tier.
        inverted: If True, lower values are better (e.g. step test BPM).

    Returns:
        Display string for the matched tier (e.g. "Good").
    """
    for tier in _RATING_ORDER:
        threshold = thresholds[tier]
        if inverted:
            if value <= threshold:
                return _RATING_DISPLAY[tier]
        else:
            if value >= threshold:
                return _RATING_DISPLAY[tier]
    return _RATING_DISPLAY["poor"]


def classify_bmi(bmi: float) -> str:
    """Classify a BMI value using WHO categories mapped to the 5-tier rating system.

    Args:
        bmi: Body mass index value (kg/m²).

    Returns:
        Rating string ("Excellent" through "Poor").
    """
    if bmi < 18.5:
        return "Poor"  # Underweight
    elif bmi < 23.0:
        return "Excellent"  # Normal weight, optimal range
    elif bmi < 25.0:
        return "Very Good"  # Normal weight, upper range
    elif bmi < 27.5:
        return "Good"  # Slightly overweight
    elif bmi < 30.0:
        return "Fair"  # Overweight
    else:
        return "Poor"  # Obese


def classify_whr(whr: float, gender: str) -> str:
    """Classify a waist-to-hip ratio using WHO risk thresholds.

    Args:
        whr: Waist-to-hip ratio (waist_cm / hip_cm).
        gender: "male" or "female".

    Returns:
        Rating string ("Excellent" through "Poor").
    """
    if gender == "male":
        if whr < 0.85:
            return "Excellent"
        elif whr < 0.90:
            return "Very Good"
        elif whr < 0.95:
            return "Good"
        elif whr < 1.00:
            return "Fair"
        else:
            return "Poor"
    else:  # female
        if whr < 0.75:
            return "Excellent"
        elif whr < 0.80:
            return "Very Good"
        elif whr < 0.85:
            return "Good"
        elif whr < 0.90:
            return "Fair"
        else:
            return "Poor"


def calculate_single_test(
    test_id: str,
    value: float,
    age: int,
    gender: str,
) -> MetricResult:
    """Calculate the rating for a single fitness test via normative data lookup.

    Args:
        test_id: Test identifier matching a norms JSON file (e.g. "pushup").
        value: Raw test result value.
        age: Client age in years.
        gender: "male" or "female".

    Returns:
        MetricResult with rating and description populated.

    Raises:
        ValueError: If test_id has no normative data, or gender/bracket is missing.
    """
    norms = load_norms(test_id)
    bracket = get_age_bracket(age)
    inverted: bool = norms.get("inverted", False)

    gender_norms = norms["norms"].get(gender)
    if gender_norms is None:
        raise ValueError(f"No norms for gender '{gender}' in test '{test_id}'")

    thresholds = gender_norms.get(bracket)
    if thresholds is None:
        raise ValueError(
            f"No norms for age bracket '{bracket}' in test '{test_id}' ({gender})"
        )

    rating = get_rating(value, thresholds, inverted=inverted)

    return MetricResult(
        test_name=norms["test_name"],
        raw_value=value,
        unit=norms["unit"],
        rating=rating,
        category=norms["category"],
        description=f"{norms['test_name']}: {value} {norms['unit']} — {rating}",
        thresholds=thresholds,
        inverted=inverted,
    )


def _compute_bmi(client: ClientProfile) -> MetricResult:
    """Compute BMI from client height and weight and return a rated MetricResult.

    Args:
        client: ClientProfile with height_cm and weight_kg populated.

    Returns:
        MetricResult for BMI.
    """
    height_m = client.height_cm / 100.0  # type: ignore[operator]
    bmi = client.weight_kg / (height_m**2)  # type: ignore[operator]
    rating = classify_bmi(bmi)
    bmi_rounded = round(bmi, 1)
    bmi_thresholds = {
        "excellent": 23.0,
        "very_good": 25.0,
        "good": 27.5,
        "fair": 30.0,
        "poor": 50.0,
    }
    return MetricResult(
        test_name="Body Mass Index (BMI)",
        raw_value=bmi_rounded,
        unit="kg/m²",
        rating=rating,
        category="body_comp",
        description=f"BMI: {bmi_rounded} kg/m² — {rating}",
        thresholds=bmi_thresholds,
        inverted=True,
    )


def _compute_whr(client: ClientProfile) -> MetricResult:
    """Compute waist-to-hip ratio from client measurements and return a MetricResult.

    Args:
        client: ClientProfile with waist_cm and hip_cm populated.

    Returns:
        MetricResult for WHR.
    """
    whr = client.waist_cm / client.hip_cm  # type: ignore[operator]
    rating = classify_whr(whr, client.gender)
    whr_rounded = round(whr, 3)
    if client.gender == "male":
        whr_thresholds = {
            "excellent": 0.85,
            "very_good": 0.90,
            "good": 0.95,
            "fair": 1.00,
            "poor": 1.50,
        }
    else:
        whr_thresholds = {
            "excellent": 0.75,
            "very_good": 0.80,
            "good": 0.85,
            "fair": 0.90,
            "poor": 1.50,
        }
    return MetricResult(
        test_name="Waist-to-Hip Ratio",
        raw_value=whr_rounded,
        unit="ratio",
        rating=rating,
        category="body_comp",
        description=f"Waist-to-Hip Ratio: {whr_rounded} — {rating}",
        thresholds=whr_thresholds,
        inverted=True,
    )


def calculate_all_tests(input: AssessmentInput) -> list[MetricResult]:
    """Calculate ratings for all submitted tests in an AssessmentInput.

    Standard tests are looked up in the norms JSON. Computed tests (BMI, WHR)
    are derived automatically from ClientProfile body measurements when present.

    Args:
        input: AssessmentInput containing client profile and raw test values.

    Returns:
        List of MetricResult objects, one per submitted test plus any
        auto-computed body composition metrics.

    Raises:
        ValueError: If any test_id is unknown or inputs are out of valid range.
    """
    results: list[MetricResult] = []

    for test_id, value in input.tests.items():
        result = calculate_single_test(
            test_id=test_id,
            value=value,
            age=input.client.age,
            gender=input.client.gender,
        )
        results.append(result)

    # Auto-compute BMI if height and weight are provided.
    if input.client.height_cm and input.client.weight_kg:
        results.append(_compute_bmi(input.client))

    # Auto-compute WHR if waist and hip measurements are provided.
    if input.client.waist_cm and input.client.hip_cm:
        results.append(_compute_whr(input.client))

    return results


def get_test_battery() -> list[TestInfo]:
    """Return metadata for all registered tests.

    Returns:
        List of TestInfo objects for the current test battery.
    """
    return list(TEST_REGISTRY.values())
