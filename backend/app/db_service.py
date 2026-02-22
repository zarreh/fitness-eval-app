"""Database service layer — async CRUD for coaches, clients, and assessments.

Replaces the JSON-file-backed ``client_service`` and ``auth_service`` modules.
All functions are async and require a SQLAlchemy ``AsyncSession`` injected
via the ``get_db`` FastAPI dependency.
"""

import json
from datetime import datetime, timezone
from typing import Literal

import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Assessment, BodyMeasurement, Client, Coach
from app.logic import classify_body_fat, compute_body_fat_pct
from app.models import (
    AssessmentSnapshot,
    BodyMeasurementInput,
    BodyMeasurementRecord,
    ClientProfile,
    ClientRecord,
    MetricResult,
    ProgressDelta,
)
_RATING_ORDER = ["Poor", "Fair", "Good", "Very Good", "Excellent"]


# ── Coach auth ────────────────────────────────────────────────────────────────


async def get_coach_by_username(db: AsyncSession, username: str) -> Coach | None:
    """Look up a coach by username.

    Args:
        db: Active async database session.
        username: Coach's login username.

    Returns:
        ``Coach`` ORM object or ``None`` if not found.
    """
    result = await db.execute(select(Coach).where(Coach.username == username))
    return result.scalar_one_or_none()


async def create_coach(
    db: AsyncSession, username: str, password: str, display_name: str
) -> Coach:
    """Create a new coach account with a bcrypt-hashed password.

    Args:
        db: Active async database session.
        username: Unique login username (validated by caller).
        password: Plaintext password to hash and store.
        display_name: Human-readable name shown in the UI.

    Returns:
        The newly created ``Coach`` ORM object.
    """
    coach = Coach(
        username=username,
        hashed_password=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
        display_name=display_name,
    )
    db.add(coach)
    await db.commit()
    await db.refresh(coach)
    return coach


async def validate_coach_credentials(
    db: AsyncSession, username: str, password: str
) -> dict[str, str] | None:
    """Verify login credentials and return coach info on success.

    Args:
        db: Active async database session.
        username: Submitted username.
        password: Submitted plaintext password.

    Returns:
        Dict with ``username`` and ``display_name`` on success, or ``None``
        if the username is not found or the password is wrong.
    """
    coach = await get_coach_by_username(db, username)
    if not coach:
        return None
    if not _bcrypt.checkpw(password.encode(), coach.hashed_password.encode()):
        return None
    return {"username": coach.username, "display_name": coach.display_name}


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _client_to_record(
    db: AsyncSession, client: Client, coach_username: str
) -> ClientRecord:
    """Convert an ORM ``Client`` row to a ``ClientRecord`` Pydantic model.

    Loads the latest ``BodyMeasurement`` (for weight/waist/hip on the profile)
    and all ``Assessment`` rows (for history) via explicit async queries.

    Args:
        db: Active async database session.
        client: The ORM ``Client`` row to convert.
        coach_username: Username of the owning coach.

    Returns:
        A fully populated ``ClientRecord`` ready for the API response.
    """
    # Latest body measurement — provides weight/waist/hip for the profile.
    meas_result = await db.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.client_id == client.id)
        .order_by(BodyMeasurement.measured_at.desc())
        .limit(1)
    )
    latest_meas = meas_result.scalar_one_or_none()

    # All assessments newest-first.
    assess_result = await db.execute(
        select(Assessment)
        .where(Assessment.client_id == client.id)
        .order_by(Assessment.assessed_at.desc())
    )
    assessments = list(assess_result.scalars().all())

    profile = ClientProfile(
        name=client.name,
        age=client.age,
        gender=client.gender,  # type: ignore[arg-type]
        goals=json.loads(client.goals),
        notes=client.notes,
        height_cm=client.height_cm,
        weight_kg=latest_meas.weight_kg if latest_meas else None,
        waist_cm=latest_meas.waist_cm if latest_meas else None,
        hip_cm=latest_meas.hip_cm if latest_meas else None,
    )

    snapshots: list[AssessmentSnapshot] = [
        AssessmentSnapshot(
            results=[MetricResult.model_validate(r) for r in json.loads(a.results_json)],
            assessed_at=a.assessed_at,
        )
        for a in assessments
    ]

    return ClientRecord(
        name=client.name,
        profile=profile,
        saved_at=client.saved_at,
        last_assessment=snapshots[0].results if snapshots else None,
        assessed_at=snapshots[0].assessed_at if snapshots else None,
        assessment_history=snapshots,
        coach_username=coach_username,
    )


async def _get_client_row(
    db: AsyncSession, coach_username: str, name: str
) -> Client | None:
    """Fetch the raw ORM Client row for a given coach and client name.

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        name: Client name (case-sensitive).

    Returns:
        ``Client`` ORM row or ``None``.
    """
    coach = await get_coach_by_username(db, coach_username)
    if not coach:
        return None
    result = await db.execute(
        select(Client).where(Client.coach_id == coach.id, Client.name == name)
    )
    return result.scalar_one_or_none()


# ── Client CRUD ───────────────────────────────────────────────────────────────


async def list_clients_for_coach(
    db: AsyncSession, coach_username: str
) -> list[ClientRecord]:
    """Return all clients belonging to a coach, newest saved first.

    Args:
        db: Active async database session.
        coach_username: The owning coach's username.

    Returns:
        List of ``ClientRecord`` objects, or empty list if coach not found.
    """
    coach = await get_coach_by_username(db, coach_username)
    if not coach:
        return []
    result = await db.execute(
        select(Client)
        .where(Client.coach_id == coach.id)
        .order_by(Client.saved_at.desc())
    )
    clients = list(result.scalars().all())
    return [await _client_to_record(db, c, coach_username) for c in clients]


async def upsert_client(
    db: AsyncSession, profile: ClientProfile, coach_username: str
) -> ClientRecord:
    """Create or update a client (upsert by coach + name).

    ``height_cm`` is stored on the ``clients`` row.  When any of
    ``weight_kg``, ``waist_cm``, or ``hip_cm`` is provided a new
    ``BodyMeasurement`` snapshot is recorded.

    Args:
        db: Active async database session.
        profile: The ``ClientProfile`` submitted by the coach.
        coach_username: Username of the owning coach.

    Returns:
        The saved ``ClientRecord``.

    Raises:
        ValueError: If the coach does not exist in the database.
    """
    coach = await get_coach_by_username(db, coach_username)
    if not coach:
        raise ValueError(f"Coach '{coach_username}' not found.")

    now = datetime.now(tz=timezone.utc)
    existing = await _get_client_row(db, coach_username, profile.name)

    if existing:
        existing.age = profile.age
        existing.gender = profile.gender
        existing.goals = json.dumps(profile.goals)
        existing.notes = profile.notes
        existing.height_cm = profile.height_cm
        existing.saved_at = now
        client = existing
    else:
        client = Client(
            coach_id=coach.id,
            name=profile.name,
            age=profile.age,
            gender=profile.gender,
            goals=json.dumps(profile.goals),
            notes=profile.notes,
            height_cm=profile.height_cm,
            saved_at=now,
        )
        db.add(client)
        await db.flush()  # Populate client.id before creating the measurement row.

    # Log a body-measurement snapshot whenever measurement values are present.
    if any([profile.weight_kg, profile.waist_cm, profile.hip_cm, profile.neck_cm]):
        bmi: float | None = None
        if profile.height_cm and profile.weight_kg:
            h_m = profile.height_cm / 100.0
            bmi = round(profile.weight_kg / (h_m * h_m), 1)

        bf_pct: float | None = None
        bf_rating: str | None = None
        if profile.height_cm and profile.waist_cm and profile.neck_cm:
            bf_pct = compute_body_fat_pct(
                gender=profile.gender,
                height_cm=profile.height_cm,
                waist_cm=profile.waist_cm,
                neck_cm=profile.neck_cm,
                hip_cm=profile.hip_cm,
            )
            if bf_pct is not None:
                bf_rating = classify_body_fat(bf_pct, profile.gender)

        fat_mass: float | None = None
        lean_mass: float | None = None
        if profile.weight_kg and bf_pct is not None:
            fat_mass = round(profile.weight_kg * bf_pct / 100, 1)
            lean_mass = round(profile.weight_kg - fat_mass, 1)

        db.add(
            BodyMeasurement(
                client_id=client.id,
                measured_at=now,
                weight_kg=profile.weight_kg,
                waist_cm=profile.waist_cm,
                hip_cm=profile.hip_cm,
                neck_cm=profile.neck_cm,
                bmi=bmi,
                body_fat_pct=bf_pct,
                body_fat_rating=bf_rating,
                fat_mass_kg=fat_mass,
                lean_mass_kg=lean_mass,
            )
        )

    await db.commit()
    return await _client_to_record(db, client, coach_username)


async def delete_client(
    db: AsyncSession, coach_username: str, name: str
) -> bool:
    """Delete a client (and all related data) by coach + name.

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        name: Client name to delete (case-sensitive).

    Returns:
        ``True`` if found and deleted, ``False`` otherwise.
    """
    client = await _get_client_row(db, coach_username, name)
    if not client:
        return False
    await db.delete(client)
    await db.commit()
    return True


async def save_assessment(
    db: AsyncSession,
    coach_username: str,
    name: str,
    results: list[MetricResult],
) -> ClientRecord:
    """Append an assessment snapshot to the client's history.

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        name: Client name (case-sensitive).
        results: Pre-calculated ``MetricResult`` objects from the logic engine.

    Returns:
        The updated ``ClientRecord``.

    Raises:
        ValueError: If no client with that name exists for this coach.
    """
    client = await _get_client_row(db, coach_username, name)
    if not client:
        raise ValueError(f"Client '{name}' not found for coach '{coach_username}'.")

    db.add(
        Assessment(
            client_id=client.id,
            assessed_at=datetime.now(tz=timezone.utc),
            results_json=json.dumps([r.model_dump(mode="json") for r in results]),
        )
    )
    await db.commit()
    return await _client_to_record(db, client, coach_username)


async def get_assessment_history(
    db: AsyncSession, coach_username: str, name: str
) -> list[AssessmentSnapshot]:
    """Return full assessment history for a client, newest first.

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        name: Client name (case-sensitive).

    Returns:
        List of ``AssessmentSnapshot`` objects, or empty list if not found.
    """
    client = await _get_client_row(db, coach_username, name)
    if not client:
        return []
    result = await db.execute(
        select(Assessment)
        .where(Assessment.client_id == client.id)
        .order_by(Assessment.assessed_at.desc())
    )
    return [
        AssessmentSnapshot(
            results=[MetricResult.model_validate(r) for r in json.loads(a.results_json)],
            assessed_at=a.assessed_at,
        )
        for a in result.scalars().all()
    ]


# ── Body Measurements ─────────────────────────────────────────────────────────


def _row_to_record(m: BodyMeasurement) -> BodyMeasurementRecord:
    return BodyMeasurementRecord(
        id=m.id,
        measured_at=m.measured_at,
        weight_kg=m.weight_kg,
        waist_cm=m.waist_cm,
        hip_cm=m.hip_cm,
        neck_cm=m.neck_cm,
        bmi=m.bmi,
        body_fat_pct=m.body_fat_pct,
        body_fat_rating=m.body_fat_rating,
        fat_mass_kg=m.fat_mass_kg,
        lean_mass_kg=m.lean_mass_kg,
    )


async def add_measurement(
    db: AsyncSession,
    coach_username: str,
    client_name: str,
    measurement: BodyMeasurementInput,
) -> BodyMeasurementRecord:
    """Log a new body-measurement snapshot for a client.

    Auto-computes BMI (from client height + submitted weight) and body fat %
    (US Navy formula, from height + waist + neck + optional hip).

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        client_name: Client name (case-sensitive).
        measurement: Raw measurement inputs submitted by the coach.

    Returns:
        The newly created ``BodyMeasurementRecord`` with computed fields.

    Raises:
        ValueError: If no matching client exists for this coach.
    """
    client = await _get_client_row(db, coach_username, client_name)
    if not client:
        raise ValueError(
            f"Client '{client_name}' not found for coach '{coach_username}'."
        )

    # BMI — requires client height (static) + submitted weight.
    bmi: float | None = None
    if client.height_cm and measurement.weight_kg:
        h_m = client.height_cm / 100.0
        bmi = round(measurement.weight_kg / (h_m * h_m), 1)

    # Body fat % — US Navy formula.
    bf_pct: float | None = None
    bf_rating: str | None = None
    if client.height_cm and measurement.waist_cm and measurement.neck_cm:
        bf_pct = compute_body_fat_pct(
            gender=client.gender,
            height_cm=client.height_cm,
            waist_cm=measurement.waist_cm,
            neck_cm=measurement.neck_cm,
            hip_cm=measurement.hip_cm,
        )
        if bf_pct is not None:
            bf_rating = classify_body_fat(bf_pct, client.gender)

    # Fat and lean mass.
    fat_mass: float | None = None
    lean_mass: float | None = None
    if measurement.weight_kg and bf_pct is not None:
        fat_mass = round(measurement.weight_kg * bf_pct / 100, 1)
        lean_mass = round(measurement.weight_kg - fat_mass, 1)

    row = BodyMeasurement(
        client_id=client.id,
        measured_at=datetime.now(tz=timezone.utc),
        weight_kg=measurement.weight_kg,
        waist_cm=measurement.waist_cm,
        hip_cm=measurement.hip_cm,
        neck_cm=measurement.neck_cm,
        bmi=bmi,
        body_fat_pct=bf_pct,
        body_fat_rating=bf_rating,
        fat_mass_kg=fat_mass,
        lean_mass_kg=lean_mass,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_record(row)


async def get_measurements(
    db: AsyncSession,
    coach_username: str,
    client_name: str,
) -> list[BodyMeasurementRecord]:
    """Return all body-measurement snapshots for a client, newest first.

    Args:
        db: Active async database session.
        coach_username: Owning coach's username.
        client_name: Client name (case-sensitive).

    Returns:
        List of ``BodyMeasurementRecord`` objects, or empty list if not found.
    """
    client = await _get_client_row(db, coach_username, client_name)
    if not client:
        return []
    result = await db.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.client_id == client.id)
        .order_by(BodyMeasurement.measured_at.desc())
    )
    return [_row_to_record(m) for m in result.scalars().all()]


# ── Progress ──────────────────────────────────────────────────────────────────


def compute_progress(
    current: list[MetricResult],
    previous: list[MetricResult],
) -> list[ProgressDelta]:
    """Compare two assessment result sets and return per-test deltas.

    Args:
        current: Current assessment results.
        previous: Previous assessment results to compare against.

    Returns:
        List of ``ProgressDelta`` for tests present in both assessments.
    """
    prev_map = {r.test_name: r for r in previous}
    deltas: list[ProgressDelta] = []

    for curr in current:
        prev = prev_map.get(curr.test_name)
        if prev is None:
            continue

        delta_val = round(curr.raw_value - prev.raw_value, 2)
        curr_idx = (
            _RATING_ORDER.index(curr.rating) if curr.rating in _RATING_ORDER else -1
        )
        prev_idx = (
            _RATING_ORDER.index(prev.rating) if prev.rating in _RATING_ORDER else -1
        )

        direction: Literal["improved", "declined", "unchanged"]
        if curr_idx > prev_idx:
            direction = "improved"
        elif curr_idx < prev_idx:
            direction = "declined"
        else:
            direction = "unchanged"

        deltas.append(
            ProgressDelta(
                test_name=curr.test_name,
                previous_value=prev.raw_value,
                current_value=curr.raw_value,
                previous_rating=prev.rating,
                current_rating=curr.rating,
                direction=direction,
                delta=delta_val,
            )
        )
    return deltas
