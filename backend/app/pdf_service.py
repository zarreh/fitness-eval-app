"""PDF report generation using WeasyPrint and Jinja2 templates."""

from pathlib import Path

import markdown as md_lib  # type: ignore[import-untyped]
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML  # type: ignore[import-untyped]

from app.models import MetricResult, ReportResponse

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Canonical category ordering and display labels.
_CATEGORY_LABELS: dict[str, str] = {
    "strength": "Strength",
    "flexibility": "Flexibility",
    "cardio": "Cardiovascular Fitness",
    "body_comp": "Body Composition",
}

# Worst-to-best order for comparing ratings.
_RATING_ORDER: list[str] = ["Poor", "Fair", "Good", "Very Good", "Excellent"]


def _render_markdown(text: str) -> Markup:
    """Convert markdown text to HTML, marked safe for Jinja2 autoescaping.

    Args:
        text: Markdown-formatted string (e.g. LLM output).

    Returns:
        HTML string wrapped in Markup so Jinja2 does not re-escape it.
    """
    return Markup(md_lib.markdown(text))


def _format_value(value: float) -> str:
    """Format a float as an integer when it has no fractional part.

    Args:
        value: Numeric test result.

    Returns:
        "42" for 42.0, "23.8" for 23.8.
    """
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def _category_summary(
    results: list[MetricResult],
) -> list[dict[str, str | int]]:
    """Build per-category overview data for the summary cards.

    Args:
        results: All MetricResult objects for the report.

    Returns:
        List of dicts with keys: key, label, count, best_rating, worst_rating.
        Only categories that have at least one result are included.
        Ordered by the canonical category sequence defined in _CATEGORY_LABELS.
    """
    grouped: dict[str, list[MetricResult]] = {}
    for r in results:
        grouped.setdefault(r.category, []).append(r)

    summaries: list[dict[str, str | int]] = []
    for cat_key in _CATEGORY_LABELS:
        cat_results = grouped.get(cat_key, [])
        if not cat_results:
            continue
        ratings = [r.rating for r in cat_results]
        best = max(
            ratings,
            key=lambda r: _RATING_ORDER.index(r) if r in _RATING_ORDER else -1,
        )
        worst = min(
            ratings,
            key=lambda r: _RATING_ORDER.index(r) if r in _RATING_ORDER else 99,
        )
        summaries.append(
            {
                "key": cat_key,
                "label": _CATEGORY_LABELS[cat_key],
                "count": len(cat_results),
                "best_rating": best,
                "worst_rating": worst,
            }
        )
    return summaries


def _group_by_category(
    results: list[MetricResult],
) -> list[tuple[str, str, list[MetricResult]]]:
    """Group results by category in canonical order.

    Args:
        results: All MetricResult objects for the report.

    Returns:
        List of (category_key, category_label, results) tuples, one per
        category that has at least one result.
    """
    grouped: dict[str, list[MetricResult]] = {}
    for r in results:
        grouped.setdefault(r.category, []).append(r)

    output: list[tuple[str, str, list[MetricResult]]] = []
    for cat_key in _CATEGORY_LABELS:
        cat_results = grouped.get(cat_key, [])
        if cat_results:
            output.append((cat_key, _CATEGORY_LABELS[cat_key], cat_results))
    return output


def render_report_pdf(report: ReportResponse) -> bytes:
    """Render a ReportResponse to PDF bytes via Jinja2 + WeasyPrint.

    Args:
        report: Full report data including client profile, results, and LLM text.

    Returns:
        PDF file content as bytes.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["md"] = _render_markdown
    env.filters["fmt"] = _format_value

    template = env.get_template("report.html")
    html_content = template.render(
        report=report,
        category_summary=_category_summary(report.results),
        category_groups=_group_by_category(report.results),
    )
    pdf_bytes: bytes = HTML(
        string=html_content, base_url=str(TEMPLATES_DIR)
    ).write_pdf()
    return pdf_bytes
