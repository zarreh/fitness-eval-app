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
st.markdown(
    f"Recording test scores for **{client['name']}** "
    f"({client['age']} y/o {client['gender']})."
)


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

# Separate computed tests (BMI, WHR) from manual-input tests.
manual_tests = [t for t in battery if not t.get("computed", False)]
computed_tests = [t for t in battery if t.get("computed", False)]

# Group manual tests by category.
CATEGORY_LABELS = {
    "strength": "Strength",
    "flexibility": "Flexibility",
    "cardio": "Cardiovascular",
    "body_comp": "Body Composition",
}

categories: dict[str, list[dict]] = {}
for test in manual_tests:
    cat = test["category"]
    categories.setdefault(cat, []).append(test)


# ── Test input form ──────────────────────────────────────────────────────────
test_values: dict[str, float] = {}

with st.form("assessment_form"):
    for cat_key in ["strength", "flexibility", "cardio"]:
        tests_in_cat = categories.get(cat_key, [])
        if not tests_in_cat:
            continue

        st.subheader(CATEGORY_LABELS[cat_key])
        cols = st.columns(min(len(tests_in_cat), 3))

        for idx, test in enumerate(tests_in_cat):
            test_id = test["test_id"]
            label = f"{test['test_name']}\n({test['unit']})"

            with cols[idx % 3]:
                value = st.number_input(
                    label=label,
                    min_value=0.0,
                    step=1.0,
                    help=test.get("description", ""),
                    key=f"test_{test_id}",
                )
                test_values[test_id] = value

    # Show computed test notice if body measurements are present.
    if computed_tests:
        st.divider()
        st.subheader("Body Composition (auto-computed)")
        has_bmi = client.get("height_cm") and client.get("weight_kg")
        has_whr = client.get("waist_cm") and client.get("hip_cm")

        if has_bmi:
            st.info(
                "BMI will be computed automatically from height "
                f"({client['height_cm']} cm) and weight ({client['weight_kg']} kg)."
            )
        else:
            st.caption("BMI: add height and weight in the Client Profile to enable.")

        if has_whr:
            st.info(
                "Waist-to-Hip Ratio will be computed automatically from waist "
                f"({client['waist_cm']} cm) and hip ({client['hip_cm']} cm)."
            )
        else:
            st.caption(
                "Waist-to-Hip Ratio: add waist and hip measurements in the Client Profile to enable."
            )

    submitted = st.form_submit_button("Calculate Ratings", type="primary")


# ── Call /assess/calculate ───────────────────────────────────────────────────
if submitted:
    # Filter out tests the coach left at 0 (not performed).
    active_tests = {k: v for k, v in test_values.items() if v > 0}

    has_bmi = client.get("height_cm") and client.get("weight_kg")
    has_whr = client.get("waist_cm") and client.get("hip_cm")

    if not active_tests and not has_bmi and not has_whr:
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
        "Very Good": "green",
        "Good": "orange",
        "Fair": "red",
        "Poor": "red",
    }

    for r in results:
        color = RATING_COLORS.get(r["rating"], "grey")
        st.markdown(
            f"**{r['test_name']}**: {r['raw_value']} {r['unit']} — "
            f":{color}[**{r['rating']}**]"
        )
