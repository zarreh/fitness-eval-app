"""Assessment Input page — collects test scores and calls /assess/calculate."""

import httpx
import streamlit as st

st.set_page_config(page_title="Assessment", layout="wide")
st.title("Assessment Input")

API_URL = st.session_state.get("api_url", "http://localhost:8000")

# Guard: require profile first.
if "client_profile" not in st.session_state:
    st.warning("Please complete the **Client Profile** page first.")
    st.stop()

client = st.session_state["client_profile"]
st.markdown(f"Recording test scores for **{client['name']}** ({client['age']} y/o {client['gender']}).")

# ── Fetch test battery from API ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_test_battery(api_url: str) -> list[dict]:
    """Retrieve available tests from the backend."""
    try:
        response = httpx.get(f"{api_url}/tests/battery", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Could not load test battery from API: {exc}")
        return []


battery = fetch_test_battery(API_URL)

if not battery:
    st.stop()

# ── Test input form ──────────────────────────────────────────────────────────
st.subheader("Strength Tests")

test_values: dict[str, float] = {}

with st.form("assessment_form"):
    for test in battery:
        test_id = test["test_id"]
        label = f"{test['test_name']} ({test['unit']})"
        help_text = test.get("description", "")

        value = st.number_input(
            label=label,
            min_value=0.0,
            step=1.0,
            help=help_text,
            key=f"test_{test_id}",
        )
        test_values[test_id] = value

    submitted = st.form_submit_button("Calculate Ratings", type="primary")

# ── Call /assess/calculate ───────────────────────────────────────────────────
if submitted:
    # Filter out tests the coach left at 0 (not performed).
    active_tests = {k: v for k, v in test_values.items() if v > 0}

    if not active_tests:
        st.error("Enter at least one test result before calculating.")
        st.stop()

    payload = {"client": client, "tests": active_tests}

    with st.spinner("Calculating ratings..."):
        try:
            response = httpx.post(
                f"{API_URL}/assess/calculate",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            calculation = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", str(exc))
            st.error(f"Calculation error: {detail}")
            st.stop()
        except Exception as exc:
            st.error(f"Could not reach the backend: {exc}")
            st.stop()

    st.session_state["calculation"] = calculation
    st.success("Ratings calculated. Proceed to the **Report** page.")

# ── Display results if available ─────────────────────────────────────────────
if "calculation" in st.session_state:
    results = st.session_state["calculation"]["results"]
    st.divider()
    st.subheader("Results")

    RATING_COLORS = {
        "Excellent": "green",
        "Good": "green",
        "Average": "orange",
        "Below Average": "red",
        "Poor": "red",
    }

    for r in results:
        color = RATING_COLORS.get(r["rating"], "grey")
        st.markdown(
            f"**{r['test_name']}**: {r['raw_value']} {r['unit']} — "
            f":{color}[**{r['rating']}**]"
        )
