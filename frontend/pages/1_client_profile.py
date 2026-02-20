"""Client Profile page — collects and stores client information."""

import streamlit as st

from utils import show_client_sidebar, show_step_indicator

st.set_page_config(page_title="Client Profile", layout="wide")

show_step_indicator(1)
show_client_sidebar()

st.title("Client Profile")

GOAL_OPTIONS = [
    "weight_loss",
    "muscle_gain",
    "endurance",
    "flexibility",
    "general_fitness",
    "sport_performance",
]

# ── New-client reset button ───────────────────────────────────────────────────
if "client_profile" in st.session_state:
    if st.button("✕ Clear / New Client", help="Clear the current client and start fresh"):
        for key in ("client_profile", "calculation", "report", "pdf_bytes"):
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()

# ── Practitioner info (saved once per session) ────────────────────────────────
with st.expander("Practitioner Info *(for PDF cover page)*", expanded=False):
    pi_col1, pi_col2 = st.columns(2)
    with pi_col1:
        coach_name = st.text_input(
            "Coach / Practitioner Name",
            value=st.session_state.get("coach_name", ""),
            placeholder="Dr. Jane Smith",
            key="coach_name_input",
        )
    with pi_col2:
        organization = st.text_input(
            "Organisation",
            value=st.session_state.get("organization", ""),
            placeholder="Elite Fitness Studio",
            key="organization_input",
        )
    if st.button("Save Practitioner Info"):
        st.session_state["coach_name"] = coach_name.strip() or None
        st.session_state["organization"] = organization.strip() or None
        st.success("Practitioner info saved.")

st.markdown("#### Client Details")

# ── Client profile form ───────────────────────────────────────────────────────
saved = st.session_state.get("client_profile", {})

with st.form("client_profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            "Full Name",
            value=saved.get("name", ""),
            placeholder="Jane Smith",
        )
        age = st.number_input(
            "Age",
            min_value=18,
            max_value=100,
            value=int(saved.get("age", 30)),
            step=1,
        )

    with col2:
        gender_options = ["male", "female"]
        gender = st.selectbox(
            "Gender",
            options=gender_options,
            index=gender_options.index(saved.get("gender", "male")),
        )
        goals = st.multiselect(
            "Goals",
            options=GOAL_OPTIONS,
            default=saved.get("goals", ["general_fitness"]),
            format_func=lambda g: g.replace("_", " ").title(),
        )

    notes = st.text_area(
        "Coach Notes *(optional)*",
        value=saved.get("notes", "") or "",
        placeholder="Any relevant context, injuries, or preferences...",
        height=80,
    )

    st.divider()
    st.markdown("**Body Measurements** *(optional — required for BMI and Waist-to-Hip Ratio)*")

    bcol1, bcol2 = st.columns(2)
    with bcol1:
        height_cm = st.number_input(
            "Height (cm)",
            min_value=0.0,
            max_value=250.0,
            value=float(saved.get("height_cm") or 0.0),
            step=0.5,
            help="Required to compute BMI.",
        )
        waist_cm = st.number_input(
            "Waist Circumference (cm)",
            min_value=0.0,
            max_value=200.0,
            value=float(saved.get("waist_cm") or 0.0),
            step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )
    with bcol2:
        weight_kg = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            max_value=300.0,
            value=float(saved.get("weight_kg") or 0.0),
            step=0.5,
            help="Required to compute BMI.",
        )
        hip_cm = st.number_input(
            "Hip Circumference (cm)",
            min_value=0.0,
            max_value=200.0,
            value=float(saved.get("hip_cm") or 0.0),
            step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )

    submitted = st.form_submit_button("Save Profile", type="primary")

# ── Handle form submission ────────────────────────────────────────────────────
if submitted:
    if not name.strip():
        st.error("Please enter the client's name.")
    elif not goals:
        st.error("Please select at least one goal.")
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
        }
        st.session_state["client_profile"] = profile

        # Add or update in the saved-clients list.
        client_list: list[dict] = st.session_state.setdefault("client_list", [])
        existing = next(
            (i for i, c in enumerate(client_list) if c["name"] == profile["name"]), None
        )
        if existing is not None:
            client_list[existing] = {"name": profile["name"], "profile": profile}
        else:
            client_list.append({"name": profile["name"], "profile": profile})

        # Clear downstream state when the profile changes.
        for key in ("calculation", "report", "pdf_bytes"):
            st.session_state.pop(key, None)

        st.success(
            f"Profile saved for **{name.strip()}**. "
            "Proceed to the **Assessment** page."
        )

# ── Current profile summary ───────────────────────────────────────────────────
if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    st.divider()
    st.markdown("#### Current Profile")

    c1, c2, c3 = st.columns(3)
    c1.metric("Name", p["name"])
    c2.metric("Age", p["age"])
    c3.metric("Gender", p["gender"].title())

    st.write("**Goals:**", ", ".join(g.replace("_", " ").title() for g in p["goals"]))
    if p.get("notes"):
        st.write("**Notes:**", p["notes"])

    measurements = {
        "Height": f"{p['height_cm']} cm" if p.get("height_cm") else None,
        "Weight": f"{p['weight_kg']} kg" if p.get("weight_kg") else None,
        "Waist":  f"{p['waist_cm']} cm" if p.get("waist_cm") else None,
        "Hip":    f"{p['hip_cm']} cm" if p.get("hip_cm") else None,
    }
    filled = {k: v for k, v in measurements.items() if v}
    if filled:
        st.write(
            "**Body Measurements:**",
            "  ·  ".join(f"{k}: {v}" for k, v in filled.items()),
        )

    st.page_link("pages/2_assessment.py", label="Continue to Assessment →")
