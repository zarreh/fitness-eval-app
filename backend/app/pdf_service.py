"""PDF report generation using WeasyPrint and Jinja2 templates."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML  # type: ignore[import-untyped]

from app.models import ReportResponse

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


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

    # Custom filter: convert newlines to <br> for preformatted LLM text.
    env.filters["nl2br"] = lambda text: text.replace("\n", "<br>\n")

    template = env.get_template("report.html")
    html_content = template.render(report=report)
    pdf_bytes: bytes = HTML(
        string=html_content, base_url=str(TEMPLATES_DIR)
    ).write_pdf()
    return pdf_bytes
