"""Client Profile page — collects and stores client information."""

import streamlit as st

st.set_page_config(page_title="Client Profile", layout="wide")
st.title("Client Profile")
st.markdown("Enter the client's information before running the assessment.")

GOAL_OPTIONS = [
    "weight_loss",
    "muscle_gain",
    "endurance",
    "flexibility",
    "general_fitness",
    "sport_performance",
]

with st.form("client_profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Full Name", placeholder="Jane Smith")
        age = st.number_input("Age", min_value=18, max_value=100, value=30, step=1)

    with col2:
        gender = st.selectbox("Gender", options=["male", "female"])
        goals = st.multiselect(
            "Goals",
            options=GOAL_OPTIONS,
            default=["general_fitness"],
            format_func=lambda g: g.replace("_", " ").title(),
        )

    notes = st.text_area(
        "Coach Notes (optional)",
        placeholder="Any relevant context, injuries, or preferences...",
        height=80,
    )

    st.divider()
    st.markdown(
        "**Body Measurements** *(optional — required for BMI and Waist-to-Hip Ratio)*"
    )
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        height_cm = st.number_input(
            "Height (cm)", min_value=0.0, max_value=250.0, value=0.0, step=0.5,
            help="Required to compute BMI.",
        )
        waist_cm = st.number_input(
            "Waist Circumference (cm)", min_value=0.0, max_value=200.0, value=0.0, step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )
    with bcol2:
        weight_kg = st.number_input(
            "Weight (kg)", min_value=0.0, max_value=300.0, value=0.0, step=0.5,
            help="Required to compute BMI.",
        )
        hip_cm = st.number_input(
            "Hip Circumference (cm)", min_value=0.0, max_value=200.0, value=0.0, step=0.5,
            help="Required to compute Waist-to-Hip Ratio.",
        )

    submitted = st.form_submit_button("Save Profile", type="primary")

if submitted:
    if not name.strip():
        st.error("Please enter the client's name.")
    elif not goals:
        st.error("Please select at least one goal.")
    else:
        st.session_state["client_profile"] = {
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
        st.success(f"Profile saved for **{name}**. Proceed to the Assessment page.")

if "client_profile" in st.session_state:
    p = st.session_state["client_profile"]
    st.divider()
    st.subheader("Current profile")
    col1, col2, col3 = st.columns(3)
    col1.metric("Name", p["name"])
    col2.metric("Age", p["age"])
    col3.metric("Gender", p["gender"].title())
    st.write("**Goals:**", ", ".join(g.replace("_", " ").title() for g in p["goals"]))
    if p.get("notes"):
        st.write("**Notes:**", p["notes"])

    # Show body measurements if provided.
    measurements = {
        "Height": f"{p['height_cm']} cm" if p.get("height_cm") else None,
        "Weight": f"{p['weight_kg']} kg" if p.get("weight_kg") else None,
        "Waist": f"{p['waist_cm']} cm" if p.get("waist_cm") else None,
        "Hip": f"{p['hip_cm']} cm" if p.get("hip_cm") else None,
    }
    filled = {k: v for k, v in measurements.items() if v}
    if filled:
        st.write("**Body Measurements:**", " · ".join(f"{k}: {v}" for k, v in filled.items()))
