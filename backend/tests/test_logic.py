"""Unit tests for the logic engine.

Tests cover normative data lookup, age bracket mapping, rating calculation,
and end-to-end single-test calculation for the push-up test.

Rules:
- No network calls, no LLM, no file I/O beyond reading the norms JSON.
- Each normative function is tested at low, mid, and high values.
- Boundary values are explicitly tested.
- Both genders and multiple age brackets are covered.
"""

import pytest

from app.logic import (
    calculate_all_tests,
    calculate_single_test,
    get_age_bracket,
    get_rating,
    get_test_battery,
    load_norms,
)
from app.models import AssessmentInput, ClientProfile


# ── get_age_bracket ──────────────────────────────────────────────────────────

class TestGetAgeBracket:
    def test_early_twenties(self) -> None:
        assert get_age_bracket(22) == "20-29"

    def test_age_29_is_20s_bracket(self) -> None:
        assert get_age_bracket(29) == "20-29"

    def test_age_30_is_30s_bracket(self) -> None:
        assert get_age_bracket(30) == "30-39"

    def test_mid_thirties(self) -> None:
        assert get_age_bracket(35) == "30-39"

    def test_age_40_is_40s_bracket(self) -> None:
        assert get_age_bracket(40) == "40-49"

    def test_age_50_is_50s_bracket(self) -> None:
        assert get_age_bracket(50) == "50-59"

    def test_age_60_is_60plus_bracket(self) -> None:
        assert get_age_bracket(60) == "60+"

    def test_age_75_is_60plus_bracket(self) -> None:
        assert get_age_bracket(75) == "60+"

    def test_under_20_falls_back_to_20s(self) -> None:
        # Edge: client under 20 — treated as "20-29" (no lower bracket).
        assert get_age_bracket(18) == "20-29"


# ── get_rating ───────────────────────────────────────────────────────────────

class TestGetRating:
    # Thresholds matching pushup.json male 20-29.
    THRESHOLDS = {
        "excellent": 36,
        "good": 29,
        "average": 22,
        "below_average": 17,
        "poor": 0,
    }

    def test_excellent_at_threshold(self) -> None:
        assert get_rating(36.0, self.THRESHOLDS) == "Excellent"

    def test_excellent_above_threshold(self) -> None:
        assert get_rating(50.0, self.THRESHOLDS) == "Excellent"

    def test_good_at_threshold(self) -> None:
        assert get_rating(29.0, self.THRESHOLDS) == "Good"

    def test_good_just_below_excellent(self) -> None:
        assert get_rating(35.0, self.THRESHOLDS) == "Good"

    def test_average_at_threshold(self) -> None:
        assert get_rating(22.0, self.THRESHOLDS) == "Average"

    def test_average_just_below_good(self) -> None:
        assert get_rating(28.0, self.THRESHOLDS) == "Average"

    def test_below_average_at_threshold(self) -> None:
        assert get_rating(17.0, self.THRESHOLDS) == "Below Average"

    def test_poor_at_zero(self) -> None:
        assert get_rating(0.0, self.THRESHOLDS) == "Poor"

    def test_poor_low_value(self) -> None:
        assert get_rating(5.0, self.THRESHOLDS) == "Poor"


# ── load_norms ───────────────────────────────────────────────────────────────

class TestLoadNorms:
    def test_pushup_loads_successfully(self) -> None:
        norms = load_norms("pushup")
        assert norms["test_name"] == "Push-up Test"
        assert "norms" in norms
        assert "male" in norms["norms"]
        assert "female" in norms["norms"]

    def test_pushup_has_all_age_brackets(self) -> None:
        norms = load_norms("pushup")
        expected_brackets = {"20-29", "30-39", "40-49", "50-59", "60+"}
        assert set(norms["norms"]["male"].keys()) == expected_brackets
        assert set(norms["norms"]["female"].keys()) == expected_brackets

    def test_unknown_test_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="No normative data found"):
            load_norms("nonexistent_test")


# ── calculate_single_test (push-up) ─────────────────────────────────────────

class TestCalculateSingleTestPushup:
    """Push-up test: male 30-39 thresholds are Excellent≥30, Good≥22, Average≥17, BA≥12, Poor≥0."""

    # Male, 30-39 bracket
    def test_male_30s_excellent(self) -> None:
        result = calculate_single_test("pushup", 32, age=35, gender="male")
        assert result.rating == "Excellent"
        assert result.test_name == "Push-up Test"
        assert result.unit == "reps"
        assert result.category == "strength"

    def test_male_30s_good(self) -> None:
        result = calculate_single_test("pushup", 25, age=35, gender="male")
        assert result.rating == "Good"

    def test_male_30s_poor(self) -> None:
        result = calculate_single_test("pushup", 5, age=35, gender="male")
        assert result.rating == "Poor"

    def test_male_30s_boundary_excellent(self) -> None:
        result = calculate_single_test("pushup", 30, age=35, gender="male")
        assert result.rating == "Excellent"

    def test_male_30s_boundary_good(self) -> None:
        result = calculate_single_test("pushup", 22, age=35, gender="male")
        assert result.rating == "Good"

    # Female, 20-29 bracket: Excellent≥30, Good≥21, Average≥15, BA≥10, Poor≥0
    def test_female_20s_excellent(self) -> None:
        result = calculate_single_test("pushup", 35, age=25, gender="female")
        assert result.rating == "Excellent"

    def test_female_20s_average(self) -> None:
        result = calculate_single_test("pushup", 17, age=25, gender="female")
        assert result.rating == "Average"

    def test_female_20s_poor(self) -> None:
        result = calculate_single_test("pushup", 3, age=25, gender="female")
        assert result.rating == "Poor"

    # Male, 50-59 bracket: Excellent≥21, Good≥13, Average≥10, BA≥7, Poor≥0
    def test_male_50s_good(self) -> None:
        result = calculate_single_test("pushup", 15, age=55, gender="male")
        assert result.rating == "Good"

    # Male, 60+ bracket
    def test_male_60plus_below_average(self) -> None:
        result = calculate_single_test("pushup", 7, age=65, gender="male")
        assert result.rating == "Below Average"

    def test_invalid_test_id_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_single_test("squat", 50, age=30, gender="male")


# ── calculate_all_tests ──────────────────────────────────────────────────────

class TestCalculateAllTests:
    def _make_input(self, tests: dict[str, float], age: int = 30, gender: str = "male") -> AssessmentInput:
        return AssessmentInput(
            client=ClientProfile(
                name="Test Client",
                age=age,
                gender=gender,  # type: ignore[arg-type]
                goals=["general_fitness"],
            ),
            tests=tests,
        )

    def test_single_test(self) -> None:
        result = calculate_all_tests(self._make_input({"pushup": 25}))
        assert len(result) == 1
        assert result[0].rating == "Good"

    def test_returns_metric_result_objects(self) -> None:
        results = calculate_all_tests(self._make_input({"pushup": 40}))
        assert results[0].test_name == "Push-up Test"
        assert results[0].raw_value == 40.0

    def test_invalid_test_propagates_error(self) -> None:
        with pytest.raises(ValueError):
            calculate_all_tests(self._make_input({"unknown_test": 10}))


# ── get_test_battery ─────────────────────────────────────────────────────────

class TestGetTestBattery:
    def test_returns_list(self) -> None:
        battery = get_test_battery()
        assert isinstance(battery, list)
        assert len(battery) >= 1

    def test_pushup_in_battery(self) -> None:
        battery = get_test_battery()
        test_ids = [t.test_id for t in battery]
        assert "pushup" in test_ids
