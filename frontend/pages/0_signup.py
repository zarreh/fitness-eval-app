"""Coach signup page — lets a new coach create an account."""

import httpx
import streamlit as st
from utils import inject_custom_css, t, _SUPPORTED_LANGS

inject_custom_css()

# Redirect to main app if already logged in.
if st.session_state.get("authenticated"):
    st.switch_page("app.py")

# ── Language selector ─────────────────────────────────────────────────────────
_, lang_col, _ = st.columns([1, 1.5, 1])
with lang_col:
    lang_options = {lc["code"]: f"{lc['flag']} {lc['name']}" for lc in _SUPPORTED_LANGS}
    current_lang = st.session_state.get("lang", "en")
    selected_lang = st.selectbox(
        t("language_label"),
        options=list(lang_options.keys()),
        format_func=lambda c: lang_options[c],
        index=list(lang_options.keys()).index(current_lang),
        key="_lang_selector_signup",
    )
    if selected_lang != current_lang:
        st.session_state["lang"] = selected_lang
        st.rerun()

# ── Signup card ───────────────────────────────────────────────────────────────
_, col, _ = st.columns([1, 1.5, 1])
with col:
    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:1.2rem;'>"
        f"🏋️ {t('signup_title')}</h2>",
        unsafe_allow_html=True,
    )

    with st.form("signup_form"):
        display_name = st.text_input(
            t("signup_display_name"),
            placeholder=t("signup_display_name_placeholder"),
        )
        username = st.text_input(
            t("signup_username"),
            help=t("signup_username_help"),
        )
        password = st.text_input(
            t("signup_password"),
            type="password",
            help=t("signup_password_help"),
        )
        confirm_password = st.text_input(
            t("signup_confirm_password"),
            type="password",
        )
        submitted = st.form_submit_button(
            t("signup_button"), use_container_width=True, type="primary"
        )

    if submitted:
        if password != confirm_password:
            st.error(t("signup_error_passwords_mismatch"))
        else:
            api_url = st.session_state.get("api_url", "http://localhost:8000")
            try:
                resp = httpx.post(
                    f"{api_url}/auth/signup",
                    json={
                        "username": username,
                        "password": password,
                        "display_name": display_name,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    st.success(t("signup_success"))
                elif resp.status_code == 409:
                    st.error(t("signup_error_username_taken"))
                else:
                    try:
                        detail = resp.json().get("detail", "")
                    except Exception:
                        detail = ""
                    st.error(f"{t('signup_error_generic')} ({detail})" if detail else t("signup_error_generic"))
            except httpx.ConnectError:
                st.error(t("login_backend_error"))

    st.page_link("pages/login.py", label=t("signup_already_have_account"))
