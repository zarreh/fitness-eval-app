"""Persistent client storage backed by a JSON file.

Clients are upserted by name (case-sensitive). The file is created
automatically on first write and written atomically via a temp-file swap
to avoid corruption on unexpected process termination.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.models import ClientProfile, ClientRecord, MetricResult

DATA_DIR = Path(__file__).parent.parent / "data"
CLIENTS_FILE = DATA_DIR / "clients.json"


def _ensure_data_dir() -> None:
    """Create the data directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_clients() -> list[ClientRecord]:
    """Return all saved clients ordered by most recently saved first.

    Returns an empty list when the file does not exist yet.
    """
    if not CLIENTS_FILE.exists():
        return []
    try:
        raw: list[dict[str, object]] = json.loads(
            CLIENTS_FILE.read_text(encoding="utf-8")
        )
        return [ClientRecord.model_validate(r) for r in raw]
    except (json.JSONDecodeError, ValueError):
        # Corrupted file — treat as empty rather than crashing.
        return []


def _write_clients(records: list[ClientRecord]) -> None:
    """Atomically write *records* to CLIENTS_FILE."""
    _ensure_data_dir()
    payload = json.dumps(
        [r.model_dump(mode="json") for r in records],
        indent=2,
        ensure_ascii=False,
    )
    # Write to a temp file in the same directory, then rename (atomic on POSIX).
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp_path, CLIENTS_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


def upsert_client(profile: ClientProfile) -> ClientRecord:
    """Save or update a client.

    Matching is done by name (case-sensitive). If a record with the same
    name already exists it is replaced in-place; otherwise a new record is
    appended.

    Args:
        profile: The ``ClientProfile`` to save.

    Returns:
        The saved ``ClientRecord`` with an updated ``saved_at`` timestamp.
    """
    records = load_clients()
    now = datetime.now(tz=timezone.utc)
    record = ClientRecord(name=profile.name, profile=profile, saved_at=now)

    for i, existing in enumerate(records):
        if existing.name == profile.name:
            records[i] = record
            _write_clients(records)
            return record

    records.append(record)
    _write_clients(records)
    return record


def delete_client(name: str) -> bool:
    """Delete the client with the given name.

    Args:
        name: The client name to delete.

    Returns:
        ``True`` if the client was found and deleted, ``False`` otherwise.
    """
    records = load_clients()
    filtered = [r for r in records if r.name != name]
    if len(filtered) == len(records):
        return False
    _write_clients(filtered)
    return True


def save_assessment(name: str, results: list[MetricResult]) -> ClientRecord:
    """Attach the latest assessment results to an existing client record.

    Args:
        name: Client name (case-sensitive).
        results: Pre-calculated MetricResult objects from the logic engine.

    Returns:
        The updated ClientRecord with assessment data included.

    Raises:
        ValueError: If no client with the given name exists.
    """
    records = load_clients()
    now = datetime.now(tz=timezone.utc)
    for i, existing in enumerate(records):
        if existing.name == name:
            updated = ClientRecord(
                name=existing.name,
                profile=existing.profile,
                saved_at=existing.saved_at,
                last_assessment=results,
                assessed_at=now,
            )
            records[i] = updated
            _write_clients(records)
            return updated
    raise ValueError(f"Client '{name}' not found.")
