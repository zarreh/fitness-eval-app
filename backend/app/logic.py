"""Fitness assessment calculation engine.

All quantitative work happens here: normative data loading, rating lookups,
and MetricResult construction. The LLM never touches this layer.
"""

import json
from pathlib import Path

from app.models import AssessmentInput, MetricResult, TestInfo

NORMS_DIR = Path(__file__).parent.parent / "data" / "norms"

# Rating tiers in descending order — used for top-down threshold checking.
_RATING_ORDER = ["excellent", "good", "average", "below_average", "poor"]

_RATING_DISPLAY = {
    "excellent": "Excellent",
    "good": "Good",
    "average": "Average",
    "below_average": "Below Average",
    "poor": "Poor",
}

# Registry of all tests available in Phase 1 (push-up only).
# Each entry maps test_id → metadata. Expand in Phase 2.
TEST_REGISTRY: dict[str, TestInfo] = {
    "pushup": TestInfo(
        test_id="pushup",
        test_name="Push-up Test",
        category="strength",
        unit="reps",
        description=(
            "Measures upper body push strength and muscular endurance. "
            "Count maximum repetitions completed with proper form. "
            "Males use standard push-up; females use modified (knee) push-up."
        ),
    ),
}


def load_norms(test_id: str) -> dict:
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
        return json.load(f)


def get_age_bracket(age: int) -> str:
    """Map an age to the closest normative data bracket.

    Args:
        age: Client age in years. Values below 20 are treated as "20-29".

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
        return "60+"


def get_rating(value: float, thresholds: dict[str, float]) -> str:
    """Determine the rating tier for a given value against threshold table.

    Checks tiers top-down (excellent first). Returns the highest tier whose
    threshold is met (value >= threshold).

    Args:
        value: The raw test result.
        thresholds: Dict mapping tier keys to minimum values for that tier.

    Returns:
        Display string for the matched tier (e.g. "Good").
    """
    for tier in _RATING_ORDER:
        if value >= thresholds[tier]:
            return _RATING_DISPLAY[tier]
    return _RATING_DISPLAY["poor"]


def calculate_single_test(
    test_id: str,
    value: float,
    age: int,
    gender: str,
) -> MetricResult:
    """Calculate the rating for a single fitness test.

    Loads normative data, resolves the age bracket, and returns a
    fully-populated MetricResult. For formula-based tests (BMI, WHR),
    override this function's caller or extend with a pre-calculation step.

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

    gender_norms = norms["norms"].get(gender)
    if gender_norms is None:
        raise ValueError(f"No norms for gender '{gender}' in test '{test_id}'")

    thresholds = gender_norms.get(bracket)
    if thresholds is None:
        raise ValueError(
            f"No norms for age bracket '{bracket}' in test '{test_id}' ({gender})"
        )

    rating = get_rating(value, thresholds)

    return MetricResult(
        test_name=norms["test_name"],
        raw_value=value,
        unit=norms["unit"],
        rating=rating,
        category=norms["category"],
        description=f"{norms['test_name']}: {value} {norms['unit']} — {rating}",
    )


def calculate_all_tests(input: AssessmentInput) -> list[MetricResult]:
    """Calculate ratings for all submitted tests in an AssessmentInput.

    Args:
        input: AssessmentInput containing client profile and raw test values.

    Returns:
        List of MetricResult objects, one per submitted test.

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
    return results


def get_test_battery() -> list[TestInfo]:
    """Return metadata for all registered tests.

    Returns:
        List of TestInfo objects for the current test battery.
    """
    return list(TEST_REGISTRY.values())
