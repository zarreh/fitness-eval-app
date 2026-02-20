"""Report page — generates LLM narrative and downloads PDF."""

import httpx
import streamlit as st

from utils import show_client_sidebar, show_step_indicator

st.set_page_config(page_title="Report", layout="wide")

show_step_indicator(3)
show_client_sidebar()

st.title("Report")

API_URL = st.session_state.get("api_url", "http://localhost:8000")

# Guard: require assessment first.
if "calculation" not in st.session_state:
    st.warning("Please complete the **Assessment** page first.")
    st.page_link("pages/2_assessment.py", label="← Go to Assessment")
    st.stop()

client = st.session_state["client_profile"]
calculation = st.session_state["calculation"]
n_results = len(calculation["results"])

st.markdown(
    f"Generating report for **{client['name']}** based on {n_results} test result(s)."
)

# ── Report settings ───────────────────────────────────────────────────────────
with st.expander("Report Settings", expanded="report" not in st.session_state):
    coach_notes = st.text_area(
        "Additional notes for the LLM *(optional)*",
        value=st.session_state.get("_coach_notes", ""),
        placeholder="Any extra context to help tailor the summary — injuries, recent events, etc.",
        height=80,
        key="coach_notes_input",
    )

# ── Generate / Regenerate buttons ────────────────────────────────────────────
report_exists = "report" in st.session_state

if not report_exists:
    generate_clicked = st.button(
        "Generate Report",
        type="primary",
        help="Call the LLM to generate a summary and workout plan.",
    )
    regenerate_clicked = False
else:
    col_regen, col_clear = st.columns([2, 5])
    with col_regen:
        regenerate_clicked = st.button(
            "↺ Regenerate Report",
            help="Re-run the LLM to get a fresh summary and workout plan.",
        )
    with col_clear:
        if st.button("✕ Clear Report", help="Remove the current report"):
            for key in ("report", "pdf_bytes"):
                st.session_state.pop(key, None)
            st.rerun()
    generate_clicked = False


def _call_generate_report(notes: str) -> dict | None:
    """Call /assess/generate-report and return the response JSON, or None on error."""
    payload = {
        "client": client,
        "results": calculation["results"],
        "coach_notes": notes.strip() or None,
        "coach_name": st.session_state.get("coach_name"),
        "organization": st.session_state.get("organization"),
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

    with st.spinner("Generating summary and workout plan — this may take a moment…"):
        result = _call_generate_report(coach_notes)

    if result:
        st.session_state["report"] = result
        # Invalidate any cached PDF since the report changed.
        st.session_state.pop("pdf_bytes", None)
        st.success("Report generated.")
        st.rerun()


# ── Report preview ────────────────────────────────────────────────────────────
if "report" in st.session_state:
    report = st.session_state["report"]

    st.divider()

    tab_summary, tab_workout = st.tabs(["Assessment Summary", "Workout Plan"])

    with tab_summary:
        st.markdown(report["llm_summary"])

    with tab_workout:
        st.markdown(
            "*Draft for coach review — please adapt as appropriate for this client.*"
        )
        st.markdown(report["workout_suggestions"])

    st.divider()

    # ── PDF download ──────────────────────────────────────────────────────────
    # Generate PDF on demand and cache the bytes so the button doesn't
    # re-trigger a full PDF render on every Streamlit rerun.
    if "pdf_bytes" not in st.session_state:
        with st.spinner("Rendering PDF…"):
            try:
                pdf_response = httpx.post(
                    f"{API_URL}/assess/generate-pdf",
                    json=report,
                    timeout=30.0,
                )
                pdf_response.raise_for_status()
                st.session_state["pdf_bytes"] = pdf_response.content
            except httpx.ConnectError:
                st.error("Cannot reach the backend to generate the PDF.")
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")

    pdf_bytes = st.session_state.get("pdf_bytes")
    if pdf_bytes:
        client_name = client["name"].replace(" ", "_")
        st.download_button(
            label="⬇ Download PDF Report",
            data=pdf_bytes,
            file_name=f"fitness_report_{client_name}.pdf",
            mime="application/pdf",
            type="primary",
        )
