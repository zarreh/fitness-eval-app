"""Streamlit entrypoint — navigation controller.

Handles auth-conditional routing via st.navigation():
- Authenticated:   Home, Client Profile, Assessment, Report
- Unauthenticated: Login (default) + Sign Up  — both hidden from sidebar

Run with:
    streamlit run app.py --server.port 8502
"""

import os
import time

import streamlit as st
from utils import inject_custom_css, t

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

inject_custom_css()

# ── Session timeout check ──────────────────────────────────────────────────────
authenticated = st.session_state.get("authenticated", False)
if authenticated:
    login_ts = st.session_state.get("_login_time", 0.0)
    if time.time() - login_ts > 3600:
        for key in (
            "authenticated", "current_user", "display_name",
            "client_profile", "calculation", "report", "pdf_bytes",
            "client_list", "assessment_history", "progress_deltas",
            "_login_time",
        ):
            st.session_state.pop(key, None)
        st.warning(t("session_expired"))
        authenticated = False

# ── Navigation routing ─────────────────────────────────────────────────────────
if authenticated:
    pg = st.navigation(
        [
            st.Page("pages/home.py", title=t("app_title"), icon="🏋️", default=True),
            st.Page(
                "pages/1_client_profile.py",
                title=t("step_client_profile"),
                icon="👤",
            ),
            st.Page(
                "pages/1b_body_measures.py",
                title=t("step_body_measures"),
                icon="📏",
            ),
            st.Page(
                "pages/2_assessment.py",
                title=t("step_assessment"),
                icon="📋",
            ),
            st.Page(
                "pages/3_report.py",
                title=t("step_report"),
                icon="📄",
            ),
        ]
    )
else:
    pg = st.navigation(
        [
            st.Page("pages/login.py", title="Login", default=True),
            st.Page("pages/0_signup.py", title="Sign Up"),
        ],
        position="hidden",
    )

pg.run()
