"""Internationalisation (i18n) service.

Loads translation bundles from ``backend/data/i18n/{lang}.json``.
Falls back to English when the requested locale is unavailable.

Supported locales: en, es, fa.
"""

import json
from functools import lru_cache
from pathlib import Path

I18N_DIR = Path(__file__).parent.parent / "data" / "i18n"
_SUPPORTED = {"en", "es", "fa"}
_FALLBACK = "en"


@lru_cache(maxsize=8)
def load_translations(lang: str) -> dict[str, object]:
    """Load and return the translation bundle for the given language code.

    Results are cached so the file is only read once per language per process.
    Falls back to English when *lang* is not supported or the file is missing.

    Args:
        lang: BCP 47 language code (e.g. ``"en"``, ``"es"``, ``"fa"``).

    Returns:
        Translation dict with keys: ``lang_code``, ``lang_name``, ``direction``,
        ``ui``, ``ratings``, ``categories``, ``goals``, ``pdf``, ``progress``.
    """
    code = lang if lang in _SUPPORTED else _FALLBACK
    path = I18N_DIR / f"{code}.json"
    try:
        data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Last-resort: return English inline so the app never crashes.
        fallback_path = I18N_DIR / f"{_FALLBACK}.json"
        text = fallback_path.read_text(encoding="utf-8")
        fallback: dict[str, object] = json.loads(text)
        return fallback


def get_supported_languages() -> list[dict[str, str]]:
    """Return the list of supported language options for the language picker.

    Returns:
        List of dicts with ``code``, ``name``, ``direction``.
    """
    result: list[dict[str, str]] = []
    for code in ["en", "es", "fa"]:
        data = load_translations(code)
        result.append(
            {
                "code": code,
                "name": str(data.get("lang_name", code)),
                "direction": str(data.get("direction", "ltr")),
            }
        )
    return result


def llm_language_instruction(lang: str) -> str:
    """Return a language instruction to append to LLM prompts.

    For English nothing is appended (the prompts are already in English).
    For other languages, a clear instruction is returned so the model
    writes its response in the correct language.

    Args:
        lang: BCP 47 language code.

    Returns:
        Instruction string, or empty string for English.
    """
    _INSTRUCTIONS: dict[str, str] = {
        "es": (
            "\n\nIMPORTANT: Write your ENTIRE response in Spanish (Español). "
            "Do not use any English."
        ),
        "fa": (
            "\n\nمهم: تمام پاسخ خود را به فارسی بنویسید. "
            "از هیچ زبان دیگری استفاده نکنید."
        ),
    }
    return _INSTRUCTIONS.get(lang, "")
