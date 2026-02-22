"""Coach login page."""

import time

import httpx
import streamlit as st
from utils import inject_custom_css, t, _SUPPORTED_LANGS

inject_custom_css()

# Redirect to home if already authenticated.
if st.session_state.get("authenticated"):
    st.switch_page("pages/home.py")

# ── Language selector ──────────────────────────────────────────────────────────
_, lang_col, _ = st.columns([1, 1.5, 1])
with lang_col:
    lang_options = {
        lc["code"]: f"{lc['flag']} {lc['name']}" for lc in _SUPPORTED_LANGS
    }
    current_lang = st.session_state.get("lang", "en")
    selected_lang = st.selectbox(
        t("language_label"),
        options=list(lang_options.keys()),
        format_func=lambda c: lang_options[c],
        index=list(lang_options.keys()).index(current_lang),
        key="_lang_selector_login",
    )
    if selected_lang != current_lang:
        st.session_state["lang"] = selected_lang
        st.rerun()

# ── Login card ─────────────────────────────────────────────────────────────────
_, col, _ = st.columns([1, 1.5, 1])
with col:
    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:1.2rem;'>"
        f"🏋️ {t('login_title')}</h2>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        username = st.text_input(t("login_username"))
        password = st.text_input(t("login_password"), type="password")
        submitted = st.form_submit_button(
            t("login_button"), use_container_width=True
        )

    if submitted:
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        try:
            resp = httpx.post(
                f"{api_url}/auth/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                display_name = data.get("display_name", username)
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = data.get("username", username)
                st.session_state["display_name"] = display_name
                st.session_state["_login_time"] = time.time()
                st.session_state.setdefault("coach_name", display_name)
                st.rerun()
            else:
                st.error(t("login_error"))
        except httpx.ConnectError:
            st.error(t("login_backend_error"))

    st.page_link("pages/0_signup.py", label=t("signup_link"))
