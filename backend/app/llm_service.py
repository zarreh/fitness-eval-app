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
    "Please review the assessment results table above and consult your professional judgment."
)
_FALLBACK_WORKOUT = (
    "The LLM service is currently unavailable. "
    "Please use the assessment results to design a workout plan based on your professional expertise."
)


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


def _format_results_table(results: list[MetricResult]) -> str:
    """Format MetricResult list into a readable text table for the prompt.

    Args:
        results: List of pre-calculated metric results.

    Returns:
        Multi-line string with one result per line.
    """
    return "\n".join(
        f"- {r.test_name}: {r.raw_value} {r.unit} — Rating: {r.rating}"
        for r in results
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
            goals=", ".join(client.goals) if client.goals else "General fitness",
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
            goals=", ".join(client.goals) if client.goals else "General fitness",
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
