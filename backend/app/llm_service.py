"""LangChain-based LLM abstraction layer.

All LLM calls go through this module. Switching between Ollama (dev) and
OpenAI (prod) is handled here via config — callers never know the difference.

The LLM receives only pre-calculated MetricResult objects. It never sees
raw test scores and never performs calculations.
"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.models import ClientProfile, MetricResult

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


def generate_coach_summary(
    client: ClientProfile,
    results: list[MetricResult],
    coach_notes: str | None = None,
) -> str:
    """Generate an assessment narrative summary for the coach.

    Sends pre-calculated results to the LLM and returns a structured text
    with an overall summary, strengths, and areas for improvement.

    Args:
        client: Client profile (name, age, gender, goals).
        results: Pre-calculated MetricResult objects from the logic engine.
        coach_notes: Optional additional context from the coach.

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
        )

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        return str(response.content)
    except Exception:
        return _FALLBACK_SUMMARY


def generate_workout_suggestions(
    client: ClientProfile,
    results: list[MetricResult],
) -> str:
    """Generate a starter workout plan draft for the coach's review.

    Args:
        client: Client profile including stated goals.
        results: Pre-calculated MetricResult objects from the logic engine.

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
        )

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        return str(response.content)
    except Exception:
        return _FALLBACK_WORKOUT
