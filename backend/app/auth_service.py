"""Coach authentication service.

Validates credentials against a ``coaches.json`` file when present,
falling back to the single-user ``COACH_USERNAME`` / ``COACH_PASSWORD``
environment variables for backward compatibility.
"""

import json
from pathlib import Path

from app.config import settings

DATA_DIR = Path(__file__).parent.parent / "data"
COACHES_FILE = DATA_DIR / "coaches.json"


def _load_coaches() -> list[dict[str, str]]:
    """Load the coaches list from ``coaches.json``.

    Returns:
        List of coach dicts with keys ``username``, ``password``,
        ``display_name``. Returns an empty list if the file does not
        exist or is malformed.
    """
    if not COACHES_FILE.exists():
        return []
    try:
        data = json.loads(COACHES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [dict(item) for item in data]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def validate_credentials(username: str, password: str) -> dict[str, str] | None:
    """Check credentials and return coach info on success.

    Tries ``coaches.json`` first. If no coaches file exists or it is
    empty, falls back to the legacy single-user env-var credentials.

    Args:
        username: Submitted username.
        password: Submitted password.

    Returns:
        Dict with ``username`` and ``display_name`` on success, or
        ``None`` if the credentials are invalid.
    """
    coaches = _load_coaches()

    if coaches:
        for coach in coaches:
            if coach.get("username") == username and coach.get("password") == password:
                return {
                    "username": coach["username"],
                    "display_name": coach.get("display_name", coach["username"]),
                }
        return None

    # Fallback: legacy single-user mode from env vars.
    if username == settings.coach_username and password == settings.coach_password:
        return {"username": username, "display_name": username}
    return None
