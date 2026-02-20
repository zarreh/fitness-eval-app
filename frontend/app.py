"""Streamlit entry point — thin client, no business logic here.

All data operations go through the FastAPI backend via HTTP.
Run with:
    streamlit run app.py --server.port 8501
"""

import os

import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Fitness Evaluation App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Make API_URL available to all pages via session_state.
if "api_url" not in st.session_state:
    st.session_state["api_url"] = API_URL

st.title("Fitness Evaluation App")
st.markdown(
    "Use the sidebar to navigate: **Client Profile** → **Assessment** → **Report**"
)
st.info(
    "Start by entering the client's profile in the **Client Profile** page, "
    "then proceed to the Assessment page to input test scores."
)
