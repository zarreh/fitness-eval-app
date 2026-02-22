"""Client Profile page — collects and stores client information."""

import streamlit as st
from utils import (
    render_page_header,
    require_login,
    save_client_to_backend,
    show_client_sidebar,
    show_step_indicator,
    t,
)

require_login()
show_step_indicator(1)
show_client_sidebar()

render_page_header(t("profile_title"))

GOAL_OPTIONS = [
    "weight_loss",
    "muscle_gain",
    "endurance",
    "flexibility",
    "general_fitness",
    "sport_performance",
]

ACTIVITY_OPTIONS = [
    "gym",
    "outdoor",
    "home",
    "swimming",
    "yoga",
    "HIIT",
    "cycling",
    "pilates",
]

EQUIPMENT_OPTIONS = [
    "barbell",
    "dumbbells",
    "resistance_bands",
    "kettlebell",
    "pull-up bar",
    "cable machine",
    "none",
]

# ── New-client reset button ───────────────────────────────────────────────────
if "client_profile" in st.session_state:
    if st.button(f"✕ {t('profile_clear')}", help=t("profile_clear")):
        for key in ("client_profile", "calculation", "report", "pdf_bytes"):
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()

st.markdown(f"#### {t('profile_client_details')}")

# ── Client profile form ───────────────────────────────────────────────────────
saved = st.session_state.get("client_profile", {})

# Build translated goal display labels.
lang_bundle = __import__("utils").load_translations(st.session_state.get("lang", "en"))
goal_labels: dict[str, str] = dict(lang_bundle.get("goals", {}))

# Use the client name as part of widget keys so that loading a different
# client forces multiselects to re-render with fresh defaults.
_client_key = saved.get("name", "_new").replace(" ", "_")

with st.form("client_profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            t("profile_full_name"),
            value=saved.get("name", ""),
            placeholder="Jane Smith",
        )
        age = st.number_input(
            t("profile_age"),
            min_value=18,
            max_value=100,
            value=int(saved.get("age", 30)),
            step=1,
        )

    with col2:
        gender_options = ["male", "female"]
        gender = st.selectbox(
            t("profile_gender"),
            options=gender_options,
            index=gender_options.index(saved.get("gender", "male")),
        )
        goals = st.multiselect(
            t("profile_goals"),
            options=GOAL_OPTIONS,
            default=saved.get("goals", ["general_fitness"]),
            format_func=lambda g: goal_labels.get(g, g.replace("_", " ").title()),
            key=f"_goals_{_client_key}",
        )

    height_cm = st.number_input(
        t("profile_height"),
        min_value=0.0,
        max_value=250.0,
        value=float(saved.get("height_cm") or 0.0),
        step=0.5,
        help=t("profile_height_help"),
    )

    notes = st.text_area(
        t("profile_notes"),
        value=saved.get("notes", "") or "",
        placeholder=t("profile_notes_placeholder"),
        height=80,
    )

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        preferred_activities = st.multiselect(
            t("profile_preferred_activities"),
            options=ACTIVITY_OPTIONS,
            default=saved.get("preferred_activities", []),
            key=f"_pref_act_{_client_key}",
        )
    with pcol2:
        equipment_available = st.multiselect(
            t("profile_equipment"),
            options=EQUIPMENT_OPTIONS,
            default=saved.get("equipment_available", []),
            key=f"_equip_{_client_key}",
        )

    submitted = st.form_submit_button(t("profile_save"), type="primary")

# ── Handle form submission ────────────────────────────────────────────────────
if submitted:
    if not name.strip():
        st.error(t("profile_name_error"))
    elif not goals:
        st.error(t("profile_goals_error"))
    else:
        profile = {
            "name": name.strip(),
            "age": int(age),
            "gender": gender,
            "goals": goals,
            "notes": notes.strip() or None,
            "height_cm": height_cm if height_cm > 0 else None,
            "preferred_activities": preferred_activities,
            "equipment_available": equipment_available,
        }
        st.session_state["client_profile"] = profile

        # Persist to backend (survives page reloads and container restarts).
        save_client_to_backend(profile)

        # Clear downstream state when the profile changes.
        for key in ("calculation", "report", "pdf_bytes"):
            st.session_state.pop(key, None)

        st.success(t("profile_saved", name=name.strip()))

# ── Current profile summary card ──────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    st.divider()

    def _chip(label: str, color: str = "#e8eaf6", text_color: str = "#1a237e") -> str:
        return (
            f'<span style="display:inline-block;background:{color};color:{text_color};'
            f'border-radius:12px;padding:2px 10px;font-size:0.78em;margin:2px 2px;">'
            f"{label}</span>"
        )

    goals_html = "".join(
        _chip(goal_labels.get(g, g.replace("_", " ").title()))
        for g in p.get("goals", [])
    )
    activities_html = "".join(
        _chip(a, "#e8f5e9", "#1b5e20") for a in p.get("preferred_activities", [])
    )
    equipment_html = "".join(
        _chip(e, "#fff3e0", "#e65100") for e in p.get("equipment_available", [])
    )
    height_block = (
        f'<div style="text-align:center;min-width:80px;">'
        f'<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.08em;opacity:0.65;margin-bottom:2px;">'
        f'{t("profile_height")}</div>'
        f'<div style="font-size:1.15em;font-weight:700;">{p["height_cm"]} cm</div>'
        f"</div>"
        if p.get("height_cm")
        else ""
    )
    notes_block = (
        f'<div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.12);'
        f'font-size:0.85em;opacity:0.8;font-style:italic;">'
        f'📝 {p["notes"]}</div>'
        if p.get("notes")
        else ""
    )

    def _section(title: str, chips_html: str) -> str:
        if not chips_html:
            return ""
        return (
            f'<div style="flex:1;min-width:160px;">'
            f'<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.08em;'
            f'opacity:0.65;margin-bottom:6px;">{title}</div>'
            f'<div>{chips_html}</div>'
            f"</div>"
        )

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);'
        f'color:white;border-radius:10px;padding:20px 24px;margin-bottom:1rem;">'
        f'<div style="display:flex;gap:28px;flex-wrap:wrap;align-items:center;margin-bottom:14px;">'
        f'<div style="min-width:160px;">'
        f'<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.08em;opacity:0.65;margin-bottom:2px;">'
        f'{t("profile_full_name")}</div>'
        f'<div style="font-size:1.35em;font-weight:700;">{p["name"]}</div>'
        f"</div>"
        f'<div style="text-align:center;min-width:60px;">'
        f'<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.08em;opacity:0.65;margin-bottom:2px;">'
        f'{t("profile_age")}</div>'
        f'<div style="font-size:1.15em;font-weight:700;">{p["age"]}</div>'
        f"</div>"
        f'<div style="text-align:center;min-width:80px;">'
        f'<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.08em;opacity:0.65;margin-bottom:2px;">'
        f'{t("profile_gender")}</div>'
        f'<div style="font-size:1.15em;font-weight:700;">{p["gender"].title()}</div>'
        f"</div>"
        f"{height_block}"
        f"</div>"
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;">'
        f'{_section(t("profile_goals"), goals_html)}'
        f'{_section(t("profile_preferred_activities").split(" *(")[0], activities_html)}'
        f'{_section(t("profile_equipment").split(" *(")[0], equipment_html)}'
        f"</div>"
        f"{notes_block}"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    col_a.page_link("pages/1b_body_measures.py", label=f"📏 {t('step_body_measures')}")
    col_b.page_link("pages/2_assessment.py", label=t("profile_continue"))
