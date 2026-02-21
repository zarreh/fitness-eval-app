"""Unit tests for assessment history and progress tracking.

Tests cover:
- compute_progress() with matching/missing tests and different directions
- Assessment history append behavior in save_assessment()
- Legacy migration for records with last_assessment but no assessment_history
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.client_service import compute_progress, load_clients, save_assessment
from app.models import AssessmentSnapshot, ClientProfile, ClientRecord, MetricResult

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_result(
    test_name: str = "Push-up Test",
    raw_value: float = 25.0,
    rating: str = "Good",
    unit: str = "reps",
    category: str = "strength",
) -> MetricResult:
    """Create a minimal MetricResult for testing."""
    return MetricResult(
        test_name=test_name,
        raw_value=raw_value,
        unit=unit,
        rating=rating,
        category=category,
        description=f"{test_name}: {raw_value} {unit} — {rating}",
    )


# ── compute_progress ─────────────────────────────────────────────────────────


class TestComputeProgress:
    """Tests for the compute_progress function."""

    def test_improved_rating(self) -> None:
        current = [_make_result(rating="Excellent", raw_value=40)]
        previous = [_make_result(rating="Good", raw_value=25)]
        deltas = compute_progress(current, previous)

        assert len(deltas) == 1
        assert deltas[0].direction == "improved"
        assert deltas[0].delta == 15.0
        assert deltas[0].previous_rating == "Good"
        assert deltas[0].current_rating == "Excellent"

    def test_declined_rating(self) -> None:
        current = [_make_result(rating="Fair", raw_value=15)]
        previous = [_make_result(rating="Very Good", raw_value=30)]
        deltas = compute_progress(current, previous)

        assert len(deltas) == 1
        assert deltas[0].direction == "declined"
        assert deltas[0].delta == -15.0

    def test_unchanged_rating(self) -> None:
        current = [_make_result(rating="Good", raw_value=26)]
        previous = [_make_result(rating="Good", raw_value=25)]
        deltas = compute_progress(current, previous)

        assert len(deltas) == 1
        assert deltas[0].direction == "unchanged"
        assert deltas[0].delta == 1.0

    def test_skips_tests_not_in_previous(self) -> None:
        current = [
            _make_result(test_name="Push-up Test", raw_value=30),
            _make_result(test_name="Plank Test", raw_value=60, unit="seconds"),
        ]
        previous = [_make_result(test_name="Push-up Test", raw_value=25)]
        deltas = compute_progress(current, previous)

        assert len(deltas) == 1
        assert deltas[0].test_name == "Push-up Test"

    def test_empty_previous_returns_no_deltas(self) -> None:
        current = [_make_result()]
        deltas = compute_progress(current, [])
        assert deltas == []

    def test_empty_current_returns_no_deltas(self) -> None:
        previous = [_make_result()]
        deltas = compute_progress([], previous)
        assert deltas == []

    def test_multiple_tests_mixed_directions(self) -> None:
        current = [
            _make_result(
                test_name="Push-up Test",
                rating="Excellent",
                raw_value=40,
            ),
            _make_result(
                test_name="Wall Sit Test",
                rating="Fair",
                raw_value=30,
                unit="seconds",
            ),
            _make_result(
                test_name="Plank Test",
                rating="Good",
                raw_value=60,
                unit="seconds",
            ),
        ]
        previous = [
            _make_result(
                test_name="Push-up Test",
                rating="Good",
                raw_value=25,
            ),
            _make_result(
                test_name="Wall Sit Test",
                rating="Very Good",
                raw_value=60,
                unit="seconds",
            ),
            _make_result(
                test_name="Plank Test",
                rating="Good",
                raw_value=55,
                unit="seconds",
            ),
        ]
        deltas = compute_progress(current, previous)

        assert len(deltas) == 3
        delta_map = {d.test_name: d for d in deltas}
        assert delta_map["Push-up Test"].direction == "improved"
        assert delta_map["Wall Sit Test"].direction == "declined"
        assert delta_map["Plank Test"].direction == "unchanged"

    def test_poor_to_excellent(self) -> None:
        current = [_make_result(rating="Excellent", raw_value=50)]
        previous = [_make_result(rating="Poor", raw_value=5)]
        deltas = compute_progress(current, previous)

        assert deltas[0].direction == "improved"
        assert deltas[0].delta == 45.0

    def test_delta_rounding(self) -> None:
        current = [_make_result(raw_value=23.456)]
        previous = [_make_result(raw_value=20.123)]
        deltas = compute_progress(current, previous)

        assert deltas[0].delta == 3.33


# ── Assessment history ────────────────────────────────────────────────────────


class TestSaveAssessment:
    """Tests for assessment history append in save_assessment."""

    def _make_client_record(
        self,
        name: str = "Test Client",
        history: list[AssessmentSnapshot] | None = None,
    ) -> ClientRecord:
        profile = ClientProfile(
            name=name, age=30, gender="male", goals=["general_fitness"]
        )
        return ClientRecord(
            name=name,
            profile=profile,
            saved_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            assessment_history=history or [],
        )

    @patch("app.client_service._write_clients")
    @patch("app.client_service.load_clients")
    def test_appends_to_empty_history(
        self, mock_load: patch, mock_write: patch
    ) -> None:
        record = self._make_client_record()
        mock_load.return_value = [record]

        results = [_make_result()]
        updated = save_assessment("Test Client", results)

        assert len(updated.assessment_history) == 1
        assert updated.assessment_history[0].results == results
        assert updated.last_assessment == results

    @patch("app.client_service._write_clients")
    @patch("app.client_service.load_clients")
    def test_prepends_to_existing_history(
        self, mock_load: patch, mock_write: patch
    ) -> None:
        old_snapshot = AssessmentSnapshot(
            results=[_make_result(raw_value=20)],
            assessed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        record = self._make_client_record(history=[old_snapshot])
        mock_load.return_value = [record]

        new_results = [_make_result(raw_value=30)]
        updated = save_assessment("Test Client", new_results)

        assert len(updated.assessment_history) == 2
        # Newest is first.
        assert updated.assessment_history[0].results[0].raw_value == 30
        assert updated.assessment_history[1].results[0].raw_value == 20

    @patch("app.client_service._write_clients")
    @patch("app.client_service.load_clients")
    def test_raises_for_unknown_client(
        self, mock_load: patch, mock_write: patch
    ) -> None:
        mock_load.return_value = []
        with pytest.raises(ValueError, match="not found"):
            save_assessment("Nobody", [_make_result()])


# ── Legacy migration ─────────────────────────────────────────────────────────


class TestLegacyMigration:
    """Tests for automatic migration of old records without assessment_history."""

    def test_migrates_last_assessment_to_history(self, tmp_path: Path) -> None:
        result_data = _make_result().model_dump(mode="json")
        assessed_at = "2024-06-15T10:00:00+00:00"
        record = {
            "name": "Legacy Client",
            "profile": {
                "name": "Legacy Client",
                "age": 35,
                "gender": "male",
                "goals": ["general_fitness"],
            },
            "saved_at": "2024-01-01T00:00:00+00:00",
            "last_assessment": [result_data],
            "assessed_at": assessed_at,
            # No assessment_history field.
        }

        clients_file = tmp_path / "clients.json"
        clients_file.write_text(json.dumps([record]))

        with patch("app.client_service.CLIENTS_FILE", clients_file):
            records = load_clients()

        assert len(records) == 1
        assert len(records[0].assessment_history) == 1
        assert records[0].assessment_history[0].results[0].test_name == "Push-up Test"

    def test_no_migration_when_history_exists(self, tmp_path: Path) -> None:
        result_data = _make_result().model_dump(mode="json")
        snapshot = {
            "results": [result_data],
            "assessed_at": "2024-06-15T10:00:00+00:00",
        }
        record = {
            "name": "Modern Client",
            "profile": {
                "name": "Modern Client",
                "age": 25,
                "gender": "female",
                "goals": ["weight_loss"],
            },
            "saved_at": "2024-01-01T00:00:00+00:00",
            "last_assessment": [result_data],
            "assessed_at": "2024-06-15T10:00:00+00:00",
            "assessment_history": [snapshot],
        }

        clients_file = tmp_path / "clients.json"
        clients_file.write_text(json.dumps([record]))

        with patch("app.client_service.CLIENTS_FILE", clients_file):
            records = load_clients()

        assert len(records) == 1
        # Should stay at 1, not get doubled.
        assert len(records[0].assessment_history) == 1

    def test_no_migration_when_no_assessment(self, tmp_path: Path) -> None:
        record = {
            "name": "New Client",
            "profile": {
                "name": "New Client",
                "age": 28,
                "gender": "male",
                "goals": ["muscle_gain"],
            },
            "saved_at": "2024-01-01T00:00:00+00:00",
        }

        clients_file = tmp_path / "clients.json"
        clients_file.write_text(json.dumps([record]))

        with patch("app.client_service.CLIENTS_FILE", clients_file):
            records = load_clients()

        assert len(records) == 1
        assert len(records[0].assessment_history) == 0
