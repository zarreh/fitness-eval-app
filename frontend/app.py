"""Streamlit entry point — thin client, no business logic here.

All data operations go through the FastAPI backend via HTTP.
Run with:
    streamlit run app.py --server.port 8502
"""

import os

import streamlit as st
from utils import render_page_header, require_login, show_client_sidebar, t

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

# ── Page header ───────────────────────────────────────────────────────────────
display_name = st.session_state.get("display_name", "")
header_sub = (
    f"{t('coach_label')}: {display_name}" if display_name else t("app_subtitle")
)
render_page_header(f"🏋️ {t('app_title')}", header_sub)

# ── 3-step workflow cards ─────────────────────────────────────────────────────
_STEP_DATA = [
    (
        "👤",
        "landing_step1_title",
        "landing_step1_desc",
        "pages/1_client_profile.py",
        "landing_step1_link",
    ),
    (
        "📋",
        "landing_step2_title",
        "landing_step2_desc",
        "pages/2_assessment.py",
        "landing_step2_link",
    ),
    (
        "📄",
        "landing_step3_title",
        "landing_step3_desc",
        "pages/3_report.py",
        "landing_step3_link",
    ),
]

col1, col2, col3 = st.columns(3)
for col, (icon, title_key, desc_key, page, link_key) in zip(
    [col1, col2, col3], _STEP_DATA
):
    with col:
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e0e4e8;'
            f'border-radius:8px;padding:20px 22px;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.06);min-height:148px;">'
            f'<div style="font-size:1.9em;margin-bottom:8px;">{icon}</div>'
            f'<h4 style="margin:0 0 8px 0;color:#1a1a2e;'
            f'font-size:0.97em;font-weight:700;">{t(title_key)}</h4>'
            f'<p style="color:#6c757d;font-size:0.87em;margin:0;'
            f'line-height:1.45;">{t(desc_key)}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
        st.page_link(page, label=t(link_key))

# ── Active client status ───────────────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    status_parts = [f"**{t('active_client')}:** {p['name']}"]
    if "calculation" in st.session_state:
        n = len(st.session_state["calculation"]["results"])
        status_parts.append(f"{n} {t('tests_calculated')}")
    if "report" in st.session_state:
        status_parts.append(t("report_generated"))
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    st.info("  ·  ".join(status_parts))
