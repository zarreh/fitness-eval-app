"""Streamlit entry point — thin client, no business logic here.

All data operations go through the FastAPI backend via HTTP.
Run with:
    streamlit run app.py --server.port 8501
"""

import os

import streamlit as st

from utils import require_login, show_client_sidebar, t

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Fitness Evaluation App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise persistent session state keys on first load.
if "api_url" not in st.session_state:
    st.session_state["api_url"] = API_URL
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

require_login()
show_client_sidebar()

# ── Landing page ──────────────────────────────────────────────────────────────
st.title(t("app_title"))
st.markdown(t("app_subtitle"))

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"#### {t('landing_step1_title')}")
    st.markdown(t("landing_step1_desc"))
    st.page_link("pages/1_client_profile.py", label=t("landing_step1_link"))

with col2:
    st.markdown(f"#### {t('landing_step2_title')}")
    st.markdown(t("landing_step2_desc"))
    st.page_link("pages/2_assessment.py", label=t("landing_step2_link"))

with col3:
    st.markdown(f"#### {t('landing_step3_title')}")
    st.markdown(t("landing_step3_desc"))
    st.page_link("pages/3_report.py", label=t("landing_step3_link"))

# ── Active client banner ──────────────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    status_parts = [f"**{t('active_client')}:** {p['name']}"]
    if "calculation" in st.session_state:
        n = len(st.session_state["calculation"]["results"])
        status_parts.append(f"{n} {t('tests_calculated')}")
    if "report" in st.session_state:
        status_parts.append(t("report_generated"))
    st.info("  ·  ".join(status_parts))
