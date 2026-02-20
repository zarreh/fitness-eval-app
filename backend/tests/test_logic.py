"""Unit tests for the logic engine.

Tests cover normative data lookup, age bracket mapping, rating calculation,
and end-to-end single-test calculation for all Phase 2 tests.

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
    classify_bmi,
    classify_whr,
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

    def test_age_60_is_60s_bracket(self) -> None:
        assert get_age_bracket(60) == "60-69"

    def test_age_65_is_60s_bracket(self) -> None:
        assert get_age_bracket(65) == "60-69"

    def test_age_75_falls_back_to_60s(self) -> None:
        # Ages 70+ use the 60-69 bracket (highest available).
        assert get_age_bracket(75) == "60-69"

    def test_under_20_falls_back_to_20s(self) -> None:
        # Edge: client under 20 — treated as "20-29" (no lower bracket).
        assert get_age_bracket(18) == "20-29"


# ── get_rating ───────────────────────────────────────────────────────────────


class TestGetRating:
    # Thresholds matching pushup.json male 20-29.
    THRESHOLDS = {
        "excellent": 36,
        "very_good": 29,
        "good": 22,
        "fair": 17,
        "poor": 16,
    }

    def test_excellent_at_threshold(self) -> None:
        assert get_rating(36.0, self.THRESHOLDS) == "Excellent"

    def test_excellent_above_threshold(self) -> None:
        assert get_rating(50.0, self.THRESHOLDS) == "Excellent"

    def test_very_good_at_threshold(self) -> None:
        assert get_rating(29.0, self.THRESHOLDS) == "Very Good"

    def test_very_good_just_below_excellent(self) -> None:
        assert get_rating(35.0, self.THRESHOLDS) == "Very Good"

    def test_good_at_threshold(self) -> None:
        assert get_rating(22.0, self.THRESHOLDS) == "Good"

    def test_good_just_below_very_good(self) -> None:
        assert get_rating(28.0, self.THRESHOLDS) == "Good"

    def test_fair_at_threshold(self) -> None:
        assert get_rating(17.0, self.THRESHOLDS) == "Fair"

    def test_poor_at_threshold(self) -> None:
        assert get_rating(16.0, self.THRESHOLDS) == "Poor"

    def test_poor_fallback_below_all_thresholds(self) -> None:
        # Below the poor threshold — fallback returns "Poor".
        assert get_rating(5.0, self.THRESHOLDS) == "Poor"


class TestGetRatingInverted:
    """Inverted rating — lower value is better (e.g. step test BPM)."""

    THRESHOLDS = {
        "excellent": 70,
        "very_good": 79,
        "good": 83,
        "fair": 89,
        "poor": 200,
    }

    def test_excellent_at_threshold(self) -> None:
        assert get_rating(70.0, self.THRESHOLDS, inverted=True) == "Excellent"

    def test_excellent_below_threshold(self) -> None:
        assert get_rating(60.0, self.THRESHOLDS, inverted=True) == "Excellent"

    def test_very_good(self) -> None:
        assert get_rating(75.0, self.THRESHOLDS, inverted=True) == "Very Good"

    def test_good(self) -> None:
        assert get_rating(81.0, self.THRESHOLDS, inverted=True) == "Good"

    def test_fair(self) -> None:
        assert get_rating(85.0, self.THRESHOLDS, inverted=True) == "Fair"

    def test_poor(self) -> None:
        assert get_rating(100.0, self.THRESHOLDS, inverted=True) == "Poor"

    def test_poor_fallback_above_all_thresholds(self) -> None:
        assert get_rating(999.0, self.THRESHOLDS, inverted=True) == "Poor"


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
        expected_brackets = {"20-29", "30-39", "40-49", "50-59", "60-69"}
        assert set(norms["norms"]["male"].keys()) == expected_brackets
        assert set(norms["norms"]["female"].keys()) == expected_brackets

    def test_unknown_test_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="No normative data found"):
            load_norms("nonexistent_test")


# ── classify_bmi ─────────────────────────────────────────────────────────────


class TestClassifyBmi:
    def test_underweight_is_poor(self) -> None:
        assert classify_bmi(17.0) == "Poor"

    def test_normal_optimal_is_excellent(self) -> None:
        assert classify_bmi(22.0) == "Excellent"

    def test_normal_upper_is_very_good(self) -> None:
        assert classify_bmi(24.0) == "Very Good"

    def test_slightly_overweight_is_good(self) -> None:
        assert classify_bmi(26.0) == "Good"

    def test_overweight_is_fair(self) -> None:
        assert classify_bmi(28.0) == "Fair"

    def test_obese_is_poor(self) -> None:
        assert classify_bmi(32.0) == "Poor"

    def test_boundary_normal_to_excellent(self) -> None:
        assert classify_bmi(18.5) == "Excellent"

    def test_boundary_overweight(self) -> None:
        assert classify_bmi(30.0) == "Poor"


# ── classify_whr ─────────────────────────────────────────────────────────────


class TestClassifyWhr:
    def test_male_excellent(self) -> None:
        assert classify_whr(0.80, "male") == "Excellent"

    def test_male_very_good(self) -> None:
        assert classify_whr(0.87, "male") == "Very Good"

    def test_male_good(self) -> None:
        assert classify_whr(0.92, "male") == "Good"

    def test_male_fair(self) -> None:
        assert classify_whr(0.96, "male") == "Fair"

    def test_male_poor(self) -> None:
        assert classify_whr(1.05, "male") == "Poor"

    def test_female_excellent(self) -> None:
        assert classify_whr(0.70, "female") == "Excellent"

    def test_female_very_good(self) -> None:
        assert classify_whr(0.77, "female") == "Very Good"

    def test_female_poor(self) -> None:
        assert classify_whr(0.92, "female") == "Poor"


# ── calculate_single_test (push-up) ─────────────────────────────────────────


class TestCalculateSingleTestPushup:
    """Push-up test: male 30-39 thresholds.

    Excellent≥30, VeryGood≥22, Good≥17, Fair≥12, Poor≥11.
    """

    def test_male_30s_excellent(self) -> None:
        result = calculate_single_test("pushup", 32, age=35, gender="male")
        assert result.rating == "Excellent"
        assert result.test_name == "Push-up Test"
        assert result.unit == "reps"
        assert result.category == "strength"

    def test_male_30s_very_good(self) -> None:
        result = calculate_single_test("pushup", 25, age=35, gender="male")
        assert result.rating == "Very Good"

    def test_male_30s_good(self) -> None:
        result = calculate_single_test("pushup", 18, age=35, gender="male")
        assert result.rating == "Good"

    def test_male_30s_poor(self) -> None:
        result = calculate_single_test("pushup", 5, age=35, gender="male")
        assert result.rating == "Poor"

    def test_male_30s_boundary_excellent(self) -> None:
        result = calculate_single_test("pushup", 30, age=35, gender="male")
        assert result.rating == "Excellent"

    def test_male_30s_boundary_very_good(self) -> None:
        result = calculate_single_test("pushup", 22, age=35, gender="male")
        assert result.rating == "Very Good"

    # Female, 20-29 bracket: Excellent≥30, VeryGood≥21, Good≥15, Fair≥10, Poor≥9
    def test_female_20s_excellent(self) -> None:
        result = calculate_single_test("pushup", 35, age=25, gender="female")
        assert result.rating == "Excellent"

    def test_female_20s_good(self) -> None:
        result = calculate_single_test("pushup", 17, age=25, gender="female")
        assert result.rating == "Good"

    def test_female_20s_poor(self) -> None:
        result = calculate_single_test("pushup", 3, age=25, gender="female")
        assert result.rating == "Poor"

    # Male, 50-59 bracket: Excellent≥21, VeryGood≥13, Good≥9, Fair≥6, Poor≥5
    def test_male_50s_very_good(self) -> None:
        result = calculate_single_test("pushup", 15, age=55, gender="male")
        assert result.rating == "Very Good"

    # Male, 60-69 bracket: Excellent≥18, VeryGood≥11, Good≥8, Fair≥5, Poor≥4
    def test_male_60s_fair(self) -> None:
        result = calculate_single_test("pushup", 7, age=65, gender="male")
        assert result.rating == "Fair"

    def test_invalid_test_id_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_single_test("squat", 50, age=30, gender="male")


# ── calculate_single_test (sit_and_reach) ────────────────────────────────────


class TestCalculateSingleTestSitAndReach:
    """Sit-and-reach: male 20-29 — Excellent≥40, VeryGood≥34, Good≥30, Fair≥25."""

    def test_male_20s_excellent(self) -> None:
        result = calculate_single_test("sit_and_reach", 42, age=25, gender="male")
        assert result.rating == "Excellent"
        assert result.category == "flexibility"
        assert result.unit == "cm"

    def test_male_20s_very_good(self) -> None:
        result = calculate_single_test("sit_and_reach", 36, age=25, gender="male")
        assert result.rating == "Very Good"

    def test_male_20s_good(self) -> None:
        result = calculate_single_test("sit_and_reach", 31, age=25, gender="male")
        assert result.rating == "Good"

    def test_male_20s_poor(self) -> None:
        result = calculate_single_test("sit_and_reach", 20, age=25, gender="male")
        assert result.rating == "Poor"

    def test_female_50s_excellent(self) -> None:
        # Female 50-59: Excellent≥39
        result = calculate_single_test("sit_and_reach", 40, age=55, gender="female")
        assert result.rating == "Excellent"


# ── calculate_single_test (step_test — inverted) ─────────────────────────────


class TestCalculateSingleTestStepTest:
    """YMCA step test — lower BPM is better (inverted). Male 20-29: Excellent≤70."""

    def test_male_20s_excellent(self) -> None:
        result = calculate_single_test("step_test", 65, age=25, gender="male")
        assert result.rating == "Excellent"
        assert result.category == "cardio"
        assert result.unit == "bpm"

    def test_male_20s_very_good(self) -> None:
        result = calculate_single_test("step_test", 75, age=25, gender="male")
        assert result.rating == "Very Good"

    def test_male_20s_poor(self) -> None:
        result = calculate_single_test("step_test", 95, age=25, gender="male")
        assert result.rating == "Poor"

    def test_female_40s_good(self) -> None:
        # Female 40-49: Good≤97
        result = calculate_single_test("step_test", 94, age=45, gender="female")
        assert result.rating == "Good"


# ── calculate_single_test (zipper) ───────────────────────────────────────────


class TestCalculateSingleTestZipper:
    """Zipper test: male 20-29 — Excellent≥5, VeryGood≥1, Good≥-3, Fair≥-7, Poor≥-8."""

    def test_male_20s_excellent(self) -> None:
        result = calculate_single_test("zipper", 7, age=25, gender="male")
        assert result.rating == "Excellent"
        assert result.category == "flexibility"

    def test_male_20s_very_good(self) -> None:
        result = calculate_single_test("zipper", 2, age=25, gender="male")
        assert result.rating == "Very Good"

    def test_male_20s_fair(self) -> None:
        result = calculate_single_test("zipper", -5, age=25, gender="male")
        assert result.rating == "Fair"

    def test_male_20s_poor(self) -> None:
        result = calculate_single_test("zipper", -12, age=25, gender="male")
        assert result.rating == "Poor"

    def test_female_more_flexible(self) -> None:
        # Female 20-29: Excellent≥10
        result = calculate_single_test("zipper", 11, age=25, gender="female")
        assert result.rating == "Excellent"


# ── calculate_all_tests ──────────────────────────────────────────────────────


class TestCalculateAllTests:
    def _make_input(
        self,
        tests: dict[str, float],
        age: int = 30,
        gender: str = "male",
        height_cm: float | None = None,
        weight_kg: float | None = None,
        waist_cm: float | None = None,
        hip_cm: float | None = None,
    ) -> AssessmentInput:
        return AssessmentInput(
            client=ClientProfile(
                name="Test Client",
                age=age,
                gender=gender,  # type: ignore[arg-type]
                goals=["general_fitness"],
                height_cm=height_cm,
                weight_kg=weight_kg,
                waist_cm=waist_cm,
                hip_cm=hip_cm,
            ),
            tests=tests,
        )

    def test_single_test(self) -> None:
        result = calculate_all_tests(self._make_input({"pushup": 25}))
        assert len(result) == 1
        assert result[0].rating == "Very Good"

    def test_returns_metric_result_objects(self) -> None:
        results = calculate_all_tests(self._make_input({"pushup": 40}))
        assert results[0].test_name == "Push-up Test"
        assert results[0].raw_value == 40.0

    def test_bmi_auto_computed_from_measurements(self) -> None:
        # 70 kg, 175 cm → BMI = 22.9 → Excellent
        results = calculate_all_tests(
            self._make_input({}, height_cm=175.0, weight_kg=70.0)
        )
        bmi_result = next(r for r in results if r.test_name == "Body Mass Index (BMI)")
        assert bmi_result.category == "body_comp"
        assert bmi_result.unit == "kg/m²"
        assert bmi_result.rating in {"Excellent", "Very Good"}

    def test_whr_auto_computed_from_measurements(self) -> None:
        # Waist 87, Hip 100 → WHR = 0.87 → male: Very Good (0.85–0.89)
        results = calculate_all_tests(
            self._make_input({}, gender="male", waist_cm=87.0, hip_cm=100.0)
        )
        whr_result = next(r for r in results if r.test_name == "Waist-to-Hip Ratio")
        assert whr_result.category == "body_comp"
        assert whr_result.rating == "Very Good"

    def test_bmi_not_computed_without_measurements(self) -> None:
        results = calculate_all_tests(self._make_input({"pushup": 20}))
        names = [r.test_name for r in results]
        assert "Body Mass Index (BMI)" not in names

    def test_multiple_tests(self) -> None:
        results = calculate_all_tests(
            self._make_input({"pushup": 25, "sit_and_reach": 32})
        )
        assert len(results) == 2

    def test_invalid_test_propagates_error(self) -> None:
        with pytest.raises(ValueError):
            calculate_all_tests(self._make_input({"unknown_test": 10}))


# ── get_test_battery ─────────────────────────────────────────────────────────


class TestGetTestBattery:
    def test_returns_list(self) -> None:
        battery = get_test_battery()
        assert isinstance(battery, list)
        assert len(battery) == 8

    def test_all_eight_tests_present(self) -> None:
        battery = get_test_battery()
        test_ids = {t.test_id for t in battery}
        assert test_ids == {
            "pushup",
            "wall_sit",
            "plank",
            "sit_and_reach",
            "zipper",
            "step_test",
            "bmi",
            "waist_to_hip",
        }

    def test_computed_tests_flagged(self) -> None:
        battery = get_test_battery()
        computed = {t.test_id for t in battery if t.computed}
        assert computed == {"bmi", "waist_to_hip"}

    def test_non_computed_tests_not_flagged(self) -> None:
        battery = get_test_battery()
        for t in battery:
            if t.test_id not in {"bmi", "waist_to_hip"}:
                assert t.computed is False
