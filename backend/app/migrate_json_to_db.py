"""One-time migration from JSON flat-files to SQLite.

Called automatically on startup when the ``coaches`` table is empty.
Safe to call repeatedly — it skips all work if coaches already exist.

Migration order:
1. Seed coach accounts from ``coaches.json`` (or env-var fallback).
2. Migrate clients from ``clients.json`` → ``clients`` + ``body_measurements``
   + ``assessments`` tables.

Legacy clients with an empty ``coach_username`` are assigned to the first
coach created during migration.
"""

import json
import logging
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db_models import Assessment, BodyMeasurement, Client, Coach
from app.models import ClientRecord

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
COACHES_FILE = DATA_DIR / "coaches.json"
CLIENTS_FILE = DATA_DIR / "clients.json"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def run_migration_if_needed(db: AsyncSession) -> None:
    """Migrate JSON data to SQLite when the coaches table is empty.

    This function is idempotent — it checks the ``coaches`` row count
    first and returns immediately if coaches already exist.

    Args:
        db: Active async database session (not committed on entry).
    """
    count_result = await db.execute(select(func.count(Coach.id)))
    if (count_result.scalar() or 0) > 0:
        logger.info("DB migration already complete — skipping.")
        return

    logger.info("Running JSON → SQLite migration.")

    # ── Seed coaches ──────────────────────────────────────────────────────────

    coaches_raw: list[dict[str, str]] = []
    if COACHES_FILE.exists():
        try:
            data = json.loads(COACHES_FILE.read_text(encoding="utf-8"))
            coaches_raw = [dict(item) for item in data] if isinstance(data, list) else []
        except (json.JSONDecodeError, ValueError):
            pass

    if not coaches_raw:
        # Fall back to the single env-var coach.
        coaches_raw = [
            {
                "username": settings.coach_username,
                "password": settings.coach_password,
                "display_name": settings.coach_username,
            }
        ]

    coach_map: dict[str, Coach] = {}
    for c in coaches_raw:
        coach = Coach(
            username=c["username"],
            hashed_password=_pwd_context.hash(c["password"]),
            display_name=c.get("display_name", c["username"]),
        )
        db.add(coach)
        coach_map[c["username"]] = coach

    await db.flush()  # Populate coach PKs.

    # ── Seed clients ──────────────────────────────────────────────────────────

    if not CLIENTS_FILE.exists():
        await db.commit()
        logger.info("Migration complete — no clients.json found.")
        return

    try:
        raw_clients = json.loads(CLIENTS_FILE.read_text(encoding="utf-8"))
        records = [ClientRecord.model_validate(r) for r in raw_clients]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Could not parse clients.json during migration: %s", exc)
        await db.commit()
        return

    first_coach = next(iter(coach_map.values()))

    for record in records:
        owner = coach_map.get(record.coach_username or "", first_coach)
        profile = record.profile

        client = Client(
            coach_id=owner.id,
            name=profile.name,
            age=profile.age,
            gender=profile.gender,
            goals=json.dumps(profile.goals),
            notes=profile.notes,
            height_cm=profile.height_cm,
            saved_at=record.saved_at,
        )
        db.add(client)
        await db.flush()  # Populate client.id.

        # Migrate body measurements from the profile snapshot.
        if any([profile.weight_kg, profile.waist_cm, profile.hip_cm]):
            bmi: float | None = None
            if profile.height_cm and profile.weight_kg:
                h_m = profile.height_cm / 100.0
                bmi = round(profile.weight_kg / (h_m * h_m), 1)
            db.add(
                BodyMeasurement(
                    client_id=client.id,
                    measured_at=record.saved_at,
                    weight_kg=profile.weight_kg,
                    waist_cm=profile.waist_cm,
                    hip_cm=profile.hip_cm,
                    bmi=bmi,
                )
            )

        # Migrate assessment history — insert oldest first so the newest
        # ends up with the highest id (consistent with the DB ordering).
        for snapshot in reversed(record.assessment_history):
            db.add(
                Assessment(
                    client_id=client.id,
                    assessed_at=snapshot.assessed_at,
                    results_json=json.dumps(
                        [r.model_dump(mode="json") for r in snapshot.results]
                    ),
                )
            )

    await db.commit()
    logger.info(
        "Migration complete: %d coach(es), %d client(s).",
        len(coach_map),
        len(records),
    )
