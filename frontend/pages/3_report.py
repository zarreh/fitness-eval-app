"""Report page — generates LLM narrative and downloads PDF."""

import httpx
import streamlit as st

st.set_page_config(page_title="Report", layout="wide")
st.title("Report")

API_URL = st.session_state.get("api_url", "http://localhost:8000")

# Guard: require assessment first.
if "calculation" not in st.session_state:
    st.warning("Please complete the **Assessment** page first.")
    st.stop()

client = st.session_state["client_profile"]
calculation = st.session_state["calculation"]

st.markdown(
    f"Generating report for **{client['name']}** based on "
    f"{len(calculation['results'])} test result(s)."
)

coach_notes = st.text_area(
    "Additional coach notes for the LLM (optional)",
    placeholder="Any context to help the LLM tailor the summary...",
    height=80,
)

col1, col2 = st.columns([1, 3])

# ── Generate Report ──────────────────────────────────────────────────────────
with col1:
    generate_clicked = st.button("Generate Report", type="primary", use_container_width=True)

if generate_clicked:
    payload = {
        "client": client,
        "results": calculation["results"],
        "coach_notes": coach_notes.strip() or None,
    }

    with st.spinner("Generating LLM summary and workout plan (this may take a moment)..."):
        try:
            response = httpx.post(
                f"{API_URL}/assess/generate-report",
                json=payload,
                timeout=120.0,  # LLM can be slow on CPU
            )
            response.raise_for_status()
            report = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", str(exc))
            st.error(f"Report generation error: {detail}")
            st.stop()
        except Exception as exc:
            st.error(f"Could not reach the backend: {exc}")
            st.stop()

    st.session_state["report"] = report
    st.success("Report generated.")

# ── Display & Download ───────────────────────────────────────────────────────
if "report" in st.session_state:
    report = st.session_state["report"]

    st.divider()

    with st.expander("Assessment Summary", expanded=True):
        st.markdown(report["llm_summary"])

    with st.expander("Workout Suggestions", expanded=True):
        st.markdown(report["workout_suggestions"])

    st.divider()

    # Download PDF button
    with st.spinner("Preparing PDF..."):
        try:
            pdf_response = httpx.post(
                f"{API_URL}/assess/generate-pdf",
                json=report,
                timeout=30.0,
            )
            pdf_response.raise_for_status()
            pdf_bytes = pdf_response.content
        except Exception as exc:
            st.error(f"PDF generation failed: {exc}")
            pdf_bytes = None

    if pdf_bytes:
        client_name = client["name"].replace(" ", "_")
        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name=f"fitness_report_{client_name}.pdf",
            mime="application/pdf",
            type="primary",
        )
