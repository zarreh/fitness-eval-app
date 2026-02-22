"""PDF report generation using WeasyPrint and Jinja2 templates."""

from pathlib import Path
from typing import cast

import markdown as md_lib  # type: ignore[import-untyped]
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML  # type: ignore[import-untyped]

from app.i18n_service import load_translations
from app.models import MetricResult, ProgressDelta, ReportResponse

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
    cat_labels: dict[str, str],
) -> list[dict[str, str | int]]:
    """Build per-category overview data for the summary cards.

    Args:
        results: All MetricResult objects for the report.
        cat_labels: Translated category label mapping (key → display name).

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
                "label": cat_labels.get(cat_key, _CATEGORY_LABELS[cat_key]),
                "count": len(cat_results),
                "best_rating": best,
                "worst_rating": worst,
            }
        )
    return summaries


def _group_by_category(
    results: list[MetricResult],
    cat_labels: dict[str, str],
) -> list[tuple[str, str, list[MetricResult]]]:
    """Group results by category in canonical order.

    Args:
        results: All MetricResult objects for the report.
        cat_labels: Translated category label mapping (key → display name).

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
            label = cat_labels.get(cat_key, _CATEGORY_LABELS[cat_key])
            output.append((cat_key, label, cat_results))
    return output


def _build_progress_map(
    progress: list[ProgressDelta] | None,
) -> dict[str, ProgressDelta]:
    """Build a test_name → ProgressDelta lookup for the PDF template.

    Args:
        progress: Optional list of progress deltas.

    Returns:
        Dict mapping test_name to its ProgressDelta, or empty dict.
    """
    if not progress:
        return {}
    return {p.test_name: p for p in progress}


def _compute_range_bar_data(
    result: MetricResult,
    direction: str = "ltr",
) -> dict[str, object] | None:
    """Compute zone widths, marker position, and threshold labels for a CSS range bar.

    Args:
        result: MetricResult with thresholds populated.
        direction: ``"ltr"`` or ``"rtl"``. RTL reverses zone order and mirrors
            the marker so Poor appears on the right.

    Returns:
        Dict with:
          - ``zones``: list of ``{color, width_pct, abbr}``
          - ``marker_pct``: float 0–100
          - ``threshold_labels``: list of ``{pct, val}`` for boundary numbers
        or ``None`` if thresholds are not available.
    """
    if not result.thresholds:
        return None

    th = result.thresholds
    t_fair = th["fair"]
    t_good = th["good"]
    t_vgood = th["very_good"]
    t_excellent = th["excellent"]

    zone_colors = ["#f8d7da", "#fff3cd", "#c8f0c8", "#b8e8c8", "#d4edda"]
    zone_abbrs = ["Poor", "Fair", "Good", "V.Good", "Exc."]

    if result.inverted:
        bar_min = min(t_excellent * 0.85, result.raw_value * 0.85)
        bar_max = max(t_fair * 1.2, result.raw_value * 1.1)
        total = bar_max - bar_min or 1
        widths = [
            (bar_max - t_fair) / total * 100,
            (t_fair - t_good) / total * 100,
            (t_good - t_vgood) / total * 100,
            (t_vgood - t_excellent) / total * 100,
            (t_excellent - bar_min) / total * 100,
        ]
        marker_pct = (bar_max - result.raw_value) / total * 100
    else:
        bar_min = 0.0
        bar_max = max(t_excellent * 1.25, result.raw_value * 1.1)
        total = bar_max - bar_min or 1
        widths = [
            (t_fair - bar_min) / total * 100,
            (t_good - t_fair) / total * 100,
            (t_vgood - t_good) / total * 100,
            (t_excellent - t_vgood) / total * 100,
            (bar_max - t_excellent) / total * 100,
        ]
        marker_pct = (result.raw_value - bar_min) / total * 100

    widths = [max(w, 0.5) for w in widths]
    marker_pct = max(1.0, min(99.0, marker_pct))

    # Threshold boundary positions (cumulative zone widths after zones 0..3).
    threshold_vals = [t_fair, t_good, t_vgood, t_excellent]
    cum, cumulative_pcts = 0.0, []
    for w in widths[:4]:
        cum += w
        cumulative_pcts.append(cum)

    if direction == "rtl":
        zone_colors = list(reversed(zone_colors))
        zone_abbrs = list(reversed(zone_abbrs))
        widths = list(reversed(widths))
        marker_pct = 100.0 - marker_pct
        marker_pct = max(1.0, min(99.0, marker_pct))
        cumulative_pcts = [100.0 - p for p in reversed(cumulative_pcts)]
        threshold_vals = list(reversed(threshold_vals))

    def _fmt(v: float) -> str:
        return str(int(v)) if v == int(v) else f"{v:.1f}"

    zones = [
        {"color": c, "width_pct": w, "abbr": a}
        for c, w, a in zip(zone_colors, widths, zone_abbrs)
    ]
    threshold_labels = [
        {"pct": p, "val": _fmt(v)}
        for p, v in zip(cumulative_pcts, threshold_vals)
    ]
    return {"zones": zones, "marker_pct": marker_pct, "threshold_labels": threshold_labels}


def _build_range_bars(
    results: list[MetricResult],
    direction: str = "ltr",
) -> dict[str, dict[str, object]]:
    """Build a test_name → range bar data lookup for the PDF template.

    Args:
        results: All MetricResult objects for the report.
        direction: ``"ltr"`` or ``"rtl"`` — passed to ``_compute_range_bar_data``.

    Returns:
        Dict mapping test_name to its range bar data.
    """
    bars: dict[str, dict[str, object]] = {}
    for r in results:
        bar_data = _compute_range_bar_data(r, direction=direction)
        if bar_data:
            bars[r.test_name] = bar_data
    return bars


def render_report_pdf(report: ReportResponse) -> bytes:
    """Render a ReportResponse to PDF bytes via Jinja2 + WeasyPrint.

    Args:
        report: Full report data including client profile, results, and LLM text.

    Returns:
        PDF file content as bytes.
    """
    i18n = load_translations(report.language)
    cat_labels: dict[str, str] = cast(dict[str, str], i18n.get("categories", {}))
    rating_labels: dict[str, str] = cast(dict[str, str], i18n.get("ratings", {}))
    direction: str = str(i18n.get("direction", "ltr"))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["md"] = _render_markdown
    env.filters["fmt"] = _format_value

    template = env.get_template("report.html")
    html_content = template.render(
        report=report,
        i18n=i18n,
        rating_labels=rating_labels,
        category_summary=_category_summary(report.results, cat_labels),
        category_groups=_group_by_category(report.results, cat_labels),
        progress_map=_build_progress_map(report.progress),
        range_bars=_build_range_bars(report.results, direction=direction),
    )
    pdf_bytes: bytes = HTML(
        string=html_content, base_url=str(TEMPLATES_DIR)
    ).write_pdf()
    return pdf_bytes
