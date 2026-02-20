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
        height=100,
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
