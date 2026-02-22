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
        )
    with pcol2:
        equipment_available = st.multiselect(
            t("profile_equipment"),
            options=EQUIPMENT_OPTIONS,
            default=saved.get("equipment_available", []),
        )

    st.divider()
    st.markdown(f"**{t('profile_body_measurements')}**")

    bcol1, bcol2 = st.columns(2)
    with bcol1:
        height_cm = st.number_input(
            t("profile_height"),
            min_value=0.0,
            max_value=250.0,
            value=float(saved.get("height_cm") or 0.0),
            step=0.5,
            help="Required to compute BMI.",
        )
        waist_cm = st.number_input(
            t("profile_waist"),
            min_value=0.0,
            max_value=200.0,
            value=float(saved.get("waist_cm") or 0.0),
            step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )
    with bcol2:
        weight_kg = st.number_input(
            t("profile_weight"),
            min_value=0.0,
            max_value=300.0,
            value=float(saved.get("weight_kg") or 0.0),
            step=0.5,
            help="Required to compute BMI.",
        )
        hip_cm = st.number_input(
            t("profile_hip"),
            min_value=0.0,
            max_value=200.0,
            value=float(saved.get("hip_cm") or 0.0),
            step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )

    neck_cm = st.number_input(
        t("profile_neck"),
        min_value=0.0,
        max_value=80.0,
        value=float(saved.get("neck_cm") or 0.0),
        step=0.5,
        help=t("profile_neck_help"),
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
            "weight_kg": weight_kg if weight_kg > 0 else None,
            "waist_cm": waist_cm if waist_cm > 0 else None,
            "hip_cm": hip_cm if hip_cm > 0 else None,
            "neck_cm": neck_cm if neck_cm > 0 else None,
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

# ── Current profile summary ───────────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    st.divider()
    st.markdown(f"#### {t('profile_current')}")

    c1, c2, c3 = st.columns(3)
    c1.metric(t("profile_full_name"), p["name"])
    c2.metric(t("profile_age"), p["age"])
    c3.metric(t("profile_gender"), p["gender"].title())

    st.write(
        f"**{t('profile_goals')}:**",
        ", ".join(goal_labels.get(g, g.replace("_", " ").title()) for g in p["goals"]),
    )
    if p.get("notes"):
        st.write(f"**{t('profile_notes')}:**", p["notes"])

    measurements = {
        t("profile_height"): f"{p['height_cm']} cm" if p.get("height_cm") else None,
        t("profile_weight"): f"{p['weight_kg']} kg" if p.get("weight_kg") else None,
        t("profile_waist"):  f"{p['waist_cm']} cm" if p.get("waist_cm") else None,
        t("profile_hip"):    f"{p['hip_cm']} cm" if p.get("hip_cm") else None,
        t("profile_neck"):   f"{p['neck_cm']} cm" if p.get("neck_cm") else None,
    }
    filled = {k: v for k, v in measurements.items() if v}
    if filled:
        st.write(
            f"**{t('profile_body_measurements')}:**",
            "  ·  ".join(f"{k}: {v}" for k, v in filled.items()),
        )

    col_a, col_b = st.columns(2)
    col_a.page_link("pages/1b_body_measures.py", label=f"📏 {t('step_body_measures')}")
    col_b.page_link("pages/2_assessment.py", label=t("profile_continue"))
