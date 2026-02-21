"""LangChain-based LLM abstraction layer.

All LLM calls go through this module. Switching between Ollama (dev) and
OpenAI (prod) is handled here via config — callers never know the difference.

The LLM receives only pre-calculated MetricResult objects. It never sees
raw test scores and never performs calculations.
"""

import re
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.i18n_service import llm_language_instruction
from app.models import ClientProfile, MetricResult, ProgressDelta

PROMPTS_DIR = Path(__file__).parent / "prompts"

_FALLBACK_SUMMARY = (
    "The LLM service is currently unavailable. "
    "Please review the assessment results table above "
    "and consult your professional judgment."
)
_FALLBACK_WORKOUT = (
    "The LLM service is currently unavailable. "
    "Please use the assessment results to design a workout plan "
    "based on your professional expertise."
)

# Rating → numeric weight for computing an overall fitness level.
_RATING_WEIGHTS: dict[str, int] = {
    "Excellent": 5,
    "Very Good": 4,
    "Good": 3,
    "Fair": 2,
    "Poor": 1,
}

_CATEGORY_LABELS: dict[str, str] = {
    "strength": "Strength",
    "flexibility": "Flexibility",
    "cardio": "Cardiovascular Fitness",
    "body_comp": "Body Composition",
}

_GOAL_DISPLAY: dict[str, str] = {
    "weight_loss": "Weight Loss",
    "muscle_gain": "Muscle Gain",
    "endurance": "Endurance",
    "flexibility": "Flexibility",
    "general_fitness": "General Fitness",
    "sport_performance": "Sport Performance",
}


def get_llm() -> BaseChatModel:
    """Instantiate and return the configured LLM client.

    Returns:
        A LangChain chat model instance (ChatOllama or ChatOpenAI).

    Raises:
        ValueError: If LLM_PROVIDER is set to an unrecognised value.
    """
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,  # type: ignore[arg-type]
        )
    elif settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{settings.llm_provider}'")


def _load_prompt(filename: str) -> str:
    """Read a prompt template file from the prompts directory.

    Args:
        filename: File name within backend/app/prompts/.

    Returns:
        Raw prompt string.
    """
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _compute_overall_level(results: list[MetricResult]) -> str:
    """Derive a one-line overall fitness description from all results.

    Uses a simple weighted average of rating tiers. The returned string is
    injected into prompts so the LLM can scale language and workout intensity
    to match the client's actual fitness level.

    Args:
        results: Pre-calculated MetricResult objects.

    Returns:
        A human-readable overall fitness level description.
    """
    if not results:
        return "not yet assessed"
    weights = [_RATING_WEIGHTS.get(r.rating, 3) for r in results]
    avg = sum(weights) / len(weights)
    if avg >= 4.5:
        return "Excellent — performing at a high level across all areas"
    elif avg >= 3.5:
        return "Very Good — above average with minor areas to improve"
    elif avg >= 2.5:
        return "Good — solid baseline with clear room for improvement"
    elif avg >= 1.5:
        return "Fair — several areas need focused attention"
    else:
        return "Poor — all major areas need significant improvement"


def _format_results_table(results: list[MetricResult]) -> str:
    """Format MetricResult list grouped by category for prompt injection.

    Args:
        results: Pre-calculated MetricResult objects.

    Returns:
        Multi-line string with results grouped under category headers.
    """
    grouped: dict[str, list[MetricResult]] = {}
    for r in results:
        grouped.setdefault(r.category, []).append(r)

    lines: list[str] = []
    for cat_key, cat_results in grouped.items():
        label = _CATEGORY_LABELS.get(cat_key, cat_key.replace("_", " ").title())
        lines.append(f"[{label}]")
        for r in cat_results:
            lines.append(
                f"  - {r.test_name}: {r.raw_value} {r.unit} — Rating: {r.rating}"
            )
        lines.append("")  # blank line between categories
    return "\n".join(lines).strip()


def _format_goals(goals: list[str]) -> str:
    """Convert goal slugs to display labels, comma-separated.

    Args:
        goals: List of goal slugs (e.g. ["weight_loss", "endurance"]).

    Returns:
        Human-readable goal string.
    """
    return (
        ", ".join(_GOAL_DISPLAY.get(g, g.replace("_", " ").title()) for g in goals)
        if goals
        else "General fitness"
    )


def _format_progress_section(progress: list[ProgressDelta] | None) -> str:
    """Format progress deltas for prompt injection.

    Args:
        progress: List of progress deltas, or None if no previous assessment.

    Returns:
        A multi-line progress section string, or empty string if no progress.
    """
    if not progress:
        return ""

    _ARROWS = {"improved": "↑", "declined": "↓", "unchanged": "→"}

    lines = [
        "",
        "PROGRESS SINCE LAST ASSESSMENT:",
    ]
    for p in progress:
        arrow = _ARROWS[p.direction]
        lines.append(
            f"  - {p.test_name}: {p.previous_value} → {p.current_value} "
            f"({arrow} {p.direction}, rating: {p.previous_rating} → {p.current_rating})"
        )
    lines.append("")
    lines.append(
        "When discussing results, note significant improvements or declines. "
        "Use directional language (e.g., 'has improved from Fair to Good') "
        "to highlight meaningful changes."
    )
    return "\n".join(lines)


def _normalise_bullets(text: str) -> str:
    """Convert Unicode bullet characters to markdown list items.

    Some LLMs output • characters instead of markdown ``- `` list syntax.
    This function normalises the output so the markdown renderer always
    receives proper list items, ensuring correct rendering in both the
    Streamlit UI and the WeasyPrint PDF.

    It handles two cases:
    - Lines that start with a bullet character: converted to ``- item``
    - Multiple items on a single line separated by bullet characters: each
      item is split onto its own line as a ``- item``

    Args:
        text: Raw LLM output string.

    Returns:
        Text with all ``•``/``·``/``●`` bullets replaced by ``- `` list items.
    """
    # Bullet characters the LLM might use.
    _BULLET_RE = re.compile(r"[•·●]\s*")

    result_lines: list[str] = []
    for line in text.split("\n"):
        if not _BULLET_RE.search(line):
            result_lines.append(line)
            continue

        # Split the line on bullet characters.
        parts = [p.strip() for p in _BULLET_RE.split(line) if p.strip()]
        if not parts:
            result_lines.append(line)
            continue

        # If the original line started with a bullet, treat all parts as items.
        # Otherwise the first part is lead-in text; the rest are items.
        if _BULLET_RE.match(line.lstrip()):
            for part in parts:
                result_lines.append(f"- {part}")
        else:
            result_lines.append(parts[0])
            for part in parts[1:]:
                result_lines.append(f"- {part}")

    return "\n".join(result_lines)


def generate_coach_summary(
    client: ClientProfile,
    results: list[MetricResult],
    coach_notes: str | None = None,
    progress: list[ProgressDelta] | None = None,
    language: str = "en",
) -> str:
    """Generate an assessment narrative summary for the coach.

    Sends pre-calculated results to the LLM and returns a structured text
    with an overall summary, strengths, and areas for improvement.

    Args:
        client: Client profile (name, age, gender, goals).
        results: Pre-calculated MetricResult objects from the logic engine.
        coach_notes: Optional additional context from the coach.
        progress: Optional progress deltas from a previous assessment.
        language: BCP 47 language code for the LLM output (e.g. ``"es"``).

    Returns:
        LLM-generated summary text, or a fallback message if LLM is unavailable.
    """
    try:
        system_prompt = _load_prompt("system_prompt.txt")
        user_template = _load_prompt("summary_prompt.txt")

        user_message = user_template.format(
            client_name=client.name,
            client_age=client.age,
            client_gender=client.gender,
            goals=_format_goals(client.goals),
            overall_level=_compute_overall_level(results),
            results_table=_format_results_table(results),
            coach_notes=coach_notes or client.notes or "None provided",
            progress_section=_format_progress_section(progress),
        ) + llm_language_instruction(language)

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        return _normalise_bullets(str(response.content))
    except Exception:
        return _FALLBACK_SUMMARY


def generate_workout_suggestions(
    client: ClientProfile,
    results: list[MetricResult],
    progress: list[ProgressDelta] | None = None,
    language: str = "en",
) -> str:
    """Generate a starter workout plan draft for the coach's review.

    Args:
        client: Client profile including stated goals.
        results: Pre-calculated MetricResult objects from the logic engine.
        progress: Optional progress deltas from a previous assessment.
        language: BCP 47 language code for the LLM output (e.g. ``"es"``).

    Returns:
        LLM-generated workout plan text, or a fallback message if LLM is unavailable.
    """
    try:
        system_prompt = _load_prompt("system_prompt.txt")
        user_template = _load_prompt("workout_prompt.txt")

        user_message = user_template.format(
            client_name=client.name,
            client_age=client.age,
            client_gender=client.gender,
            goals=_format_goals(client.goals),
            overall_level=_compute_overall_level(results),
            results_table=_format_results_table(results),
            progress_section=_format_progress_section(progress),
        ) + llm_language_instruction(language)

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        return _normalise_bullets(str(response.content))
    except Exception:
        return _FALLBACK_WORKOUT
