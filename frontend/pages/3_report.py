"""Report page — generates LLM narrative and downloads PDF."""

import httpx
import streamlit as st
from utils import (
    render_page_header,
    require_login,
    show_client_sidebar,
    show_step_indicator,
    t,
)

st.set_page_config(page_title="Report", layout="wide")

require_login()
show_step_indicator(3)
show_client_sidebar()

render_page_header(t("report_title"))

API_URL = st.session_state.get("api_url", "http://localhost:8000")

# Guard: require assessment first.
if "calculation" not in st.session_state:
    st.warning(t("report_assessment_required"))
    st.page_link("pages/2_assessment.py", label=t("report_go_assessment"))
    st.stop()

client = st.session_state["client_profile"]
calculation = st.session_state["calculation"]
n_results = len(calculation["results"])

st.markdown(t("report_generating_for", name=client["name"], count=n_results))

# ── Report settings ───────────────────────────────────────────────────────────
with st.expander(t("report_settings"), expanded="report" not in st.session_state):
    coach_notes = st.text_area(
        t("report_notes_label"),
        value=st.session_state.get("_coach_notes", ""),
        placeholder=t("report_notes_placeholder"),
        height=80,
        key="coach_notes_input",
    )

# ── Generate / Regenerate buttons ────────────────────────────────────────────
report_exists = "report" in st.session_state

if not report_exists:
    generate_clicked = st.button(
        t("report_generate"),
        type="primary",
        help=t("report_generate_help"),
    )
    regenerate_clicked = False
else:
    col_regen, col_clear = st.columns([2, 5])
    with col_regen:
        regenerate_clicked = st.button(
            f"↺ {t('report_regenerate')}",
            help=t("report_regenerate_help"),
        )
    with col_clear:
        if st.button(f"✕ {t('report_clear')}", help=t("report_clear_help")):
            for key in ("report", "pdf_bytes"):
                st.session_state.pop(key, None)
            st.rerun()
    generate_clicked = False


def _call_generate_report(notes: str) -> dict | None:
    """Call /assess/generate-report and return the response JSON, or None on error."""
    payload = {
        "client": client,
        "results": calculation["results"],
        "progress": st.session_state.get("progress_deltas"),
        "coach_notes": notes.strip() or None,
        "coach_name": st.session_state.get("coach_name"),
        "organization": st.session_state.get("organization"),
        "language": st.session_state.get("lang", "en"),
    }
    try:
        response = httpx.post(
            f"{API_URL}/assess/generate-report",
            json=payload,
            timeout=120.0,  # LLM can be slow on CPU
        )
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        st.error(
            f"Cannot reach the backend at `{API_URL}`. "
            "Make sure the API server is running."
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", str(exc))
        st.error(f"Report generation error: {detail}")
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
    return None


if generate_clicked or regenerate_clicked:
    # Persist the coach notes so the expander retains the value.
    st.session_state["_coach_notes"] = coach_notes

    with st.spinner(t("report_generating")):
        result = _call_generate_report(coach_notes)

    if result:
        st.session_state["report"] = result
        # Invalidate any cached PDF since the report changed.
        st.session_state.pop("pdf_bytes", None)
        st.success(t("report_generated_success"))
        st.rerun()


# ── Report preview ────────────────────────────────────────────────────────────
if "report" in st.session_state:
    report = st.session_state["report"]

    st.divider()

    tab_summary, tab_workout = st.tabs(
        [t("report_tab_summary"), t("report_tab_workout")]
    )

    with tab_summary:
        st.markdown(report["llm_summary"])

    with tab_workout:
        st.markdown(f"*{t('report_workout_disclaimer')}*")
        st.markdown(report["workout_suggestions"])

    st.divider()

    # ── PDF download ──────────────────────────────────────────────────────────
    if "pdf_bytes" not in st.session_state:
        with st.spinner(t("report_rendering_pdf")):
            try:
                pdf_response = httpx.post(
                    f"{API_URL}/assess/generate-pdf",
                    json=report,
                    timeout=30.0,
                )
                pdf_response.raise_for_status()
                st.session_state["pdf_bytes"] = pdf_response.content
            except httpx.ConnectError:
                st.error(t("report_pdf_error"))
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")

    pdf_bytes = st.session_state.get("pdf_bytes")
    if pdf_bytes:
        client_name = client["name"].replace(" ", "_")
        st.download_button(
            label=f"⬇ {t('report_download_pdf')}",
            data=pdf_bytes,
            file_name=f"fitness_report_{client_name}.pdf",
            mime="application/pdf",
            type="primary",
        )
