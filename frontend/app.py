"""Streamlit entry point — thin client, no business logic here.

All data operations go through the FastAPI backend via HTTP.
Run with:
    streamlit run app.py --server.port 8501
"""

import os

import streamlit as st

from utils import require_login, show_client_sidebar

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Fitness Evaluation App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise persistent session state keys on first load.
if "api_url" not in st.session_state:
    st.session_state["api_url"] = API_URL

require_login()
show_client_sidebar()

# ── Landing page ──────────────────────────────────────────────────────────────
st.title("Fitness Evaluation App")
st.markdown(
    "Generate professional fitness assessment reports in three steps."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        #### 1 · Client Profile
        Enter the client's name, age, gender, goals, and body measurements.
        Body measurements enable auto-computed BMI and Waist-to-Hip Ratio.
        """
    )
    st.page_link("pages/1_client_profile.py", label="Go to Client Profile →")

with col2:
    st.markdown(
        """
        #### 2 · Assessment
        Input raw test scores. The logic engine looks up normative data and
        returns a rating (Excellent → Poor) for each test instantly.
        """
    )
    st.page_link("pages/2_assessment.py", label="Go to Assessment →")

with col3:
    st.markdown(
        """
        #### 3 · Report
        Generate an LLM-powered narrative summary and personalised workout
        plan, then download a polished PDF for the client.
        """
    )
    st.page_link("pages/3_report.py", label="Go to Report →")

# ── Active client banner ──────────────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    status_parts = [f"**Active client:** {p['name']}"]
    if "calculation" in st.session_state:
        n = len(st.session_state["calculation"]["results"])
        status_parts.append(f"{n} test result(s) calculated")
    if "report" in st.session_state:
        status_parts.append("report generated")
    st.info("  ·  ".join(status_parts))
