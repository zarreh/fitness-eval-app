"""Assessment Input page — collects test scores and calls /assess/calculate."""

from urllib.parse import quote

import httpx
import streamlit as st

from utils import (
    rating_badge_html,
    render_range_bar_html,
    require_login,
    show_client_sidebar,
    show_step_indicator,
)

st.set_page_config(page_title="Assessment", layout="wide")

require_login()
show_step_indicator(2)
show_client_sidebar()

st.title("Assessment Input")

API_URL = st.session_state.get("api_url", "http://localhost:8000")

# Guard: require profile first.
if "client_profile" not in st.session_state:
    st.warning("Please complete the **Client Profile** page first.")
    st.page_link("pages/1_client_profile.py", label="← Go to Client Profile")
    st.stop()

client = st.session_state["client_profile"]
st.markdown(
    f"Recording test scores for **{client['name']}** "
    f"({client['age']} y/o {client['gender']})."
)

# Allow coach to reset results and re-enter scores.
if "calculation" in st.session_state:
    if st.button("↺ Reset & Re-enter Scores"):
        for key in ("calculation", "report", "pdf_bytes"):
            st.session_state.pop(key, None)
        st.rerun()


# ── Fetch test battery from API ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_test_battery(api_url: str) -> list[dict]:
    """Retrieve available tests from the backend."""
    try:
        response = httpx.get(f"{api_url}/tests/battery", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        st.error(
            "Cannot reach the backend. Make sure the API server is running on "
            f"`{api_url}` and try again."
        )
        return []
    except Exception as exc:
        st.error(f"Could not load test battery: {exc}")
        return []


battery = fetch_test_battery(API_URL)
if not battery:
    st.stop()

manual_tests = [t for t in battery if not t.get("computed", False)]
computed_tests = [t for t in battery if t.get("computed", False)]

CATEGORY_LABELS = {
    "strength":    "Strength",
    "flexibility": "Flexibility",
    "cardio":      "Cardiovascular",
    "body_comp":   "Body Composition",
}

categories: dict[str, list[dict]] = {}
for test in manual_tests:
    categories.setdefault(test["category"], []).append(test)


# ── Test input form ───────────────────────────────────────────────────────────
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

    # Body composition notice.
    if computed_tests:
        st.divider()
        st.subheader("Body Composition (auto-computed)")
        has_bmi = client.get("height_cm") and client.get("weight_kg")
        has_whr = client.get("waist_cm") and client.get("hip_cm")

        if has_bmi:
            st.info(
                f"BMI will be computed from height ({client['height_cm']} cm) "
                f"and weight ({client['weight_kg']} kg)."
            )
        else:
            st.caption("BMI: add height and weight in Client Profile to enable.")

        if has_whr:
            st.info(
                f"Waist-to-Hip Ratio will be computed from waist ({client['waist_cm']} cm) "
                f"and hip ({client['hip_cm']} cm)."
            )
        else:
            st.caption(
                "Waist-to-Hip Ratio: add waist and hip in Client Profile to enable."
            )

    submitted = st.form_submit_button("Calculate Ratings", type="primary")


# ── Call /assess/calculate ────────────────────────────────────────────────────
if submitted:
    active_tests = {k: v for k, v in test_values.items() if v > 0}
    has_bmi = client.get("height_cm") and client.get("weight_kg")
    has_whr = client.get("waist_cm") and client.get("hip_cm")

    if not active_tests and not has_bmi and not has_whr:
        st.error("Enter at least one test result before calculating.")
        st.stop()

    payload = {"client": client, "tests": active_tests}

    with st.spinner("Calculating ratings…"):
        try:
            response = httpx.post(
                f"{API_URL}/assess/calculate",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            calculation = response.json()
        except httpx.ConnectError:
            st.error(
                f"Cannot reach the backend at `{API_URL}`. "
                "Make sure the API server is running."
            )
            st.stop()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", str(exc))
            st.error(f"Calculation error: {detail}")
            st.stop()
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.stop()

    st.session_state["calculation"] = calculation
    # Clear any stale report when scores are recalculated.
    for key in ("report", "pdf_bytes"):
        st.session_state.pop(key, None)

    # Persist assessment results to backend so they survive page reloads.
    client_name = client.get("name", "")
    if client_name:
        try:
            httpx.post(
                f"{API_URL}/clients/{quote(client_name, safe='')}/assessment",
                json=calculation["results"],
                timeout=10,
            )
        except Exception:
            pass  # Non-fatal — results are already in session state.

    st.success("Ratings calculated. Proceed to the **Report** page.")


# ── Progress helpers ──────────────────────────────────────────────────────────

_RATING_ORDER = ["Poor", "Fair", "Good", "Very Good", "Excellent"]


def _compute_progress_deltas(
    current: list[dict], previous: list[dict]
) -> dict[str, dict]:
    """Compare current vs previous results, return test_name → delta dict."""
    prev_map = {r["test_name"]: r for r in previous}
    deltas: dict[str, dict] = {}
    for curr in current:
        prev = prev_map.get(curr["test_name"])
        if prev is None:
            continue
        delta_val = round(curr["raw_value"] - prev["raw_value"], 2)
        curr_idx = _RATING_ORDER.index(curr["rating"]) if curr["rating"] in _RATING_ORDER else -1
        prev_idx = _RATING_ORDER.index(prev["rating"]) if prev["rating"] in _RATING_ORDER else -1
        if curr_idx > prev_idx:
            direction = "improved"
        elif curr_idx < prev_idx:
            direction = "declined"
        else:
            direction = "unchanged"
        deltas[curr["test_name"]] = {
            "test_name": curr["test_name"],
            "previous_value": prev["raw_value"],
            "current_value": curr["raw_value"],
            "previous_rating": prev["rating"],
            "current_rating": curr["rating"],
            "direction": direction,
            "delta": delta_val,
        }
    return deltas


def _delta_indicator_html(delta: dict) -> str:
    """Return inline HTML for a progress delta indicator."""
    if delta["direction"] == "improved":
        return (
            '<span style="color:#155724;font-size:0.75em;font-weight:700;">'
            f'&#9650; Improved (was {delta["previous_rating"]})</span>'
        )
    elif delta["direction"] == "declined":
        return (
            '<span style="color:#721c24;font-size:0.75em;font-weight:700;">'
            f'&#9660; Declined (was {delta["previous_rating"]})</span>'
        )
    else:
        return (
            '<span style="color:#888;font-size:0.75em;">'
            "&#8212; Unchanged</span>"
        )


# ── Results dashboard ─────────────────────────────────────────────────────────
if "calculation" in st.session_state:
    results: list[dict] = st.session_state["calculation"]["results"]

    # Compute progress deltas if we have previous assessment data.
    history = st.session_state.get("assessment_history", [])
    # Find previous assessment — skip the most recent one if it matches current results.
    prev_results: list[dict] | None = None
    if len(history) >= 2:
        prev_results = history[1]["results"]
    elif len(history) == 1:
        # Only show deltas if these are NEW results (not the restored ones).
        # Check if the current results differ from the stored latest.
        stored = history[0]["results"]
        stored_vals = {r["test_name"]: r["raw_value"] for r in stored}
        current_vals = {r["test_name"]: r["raw_value"] for r in results}
        if stored_vals != current_vals:
            prev_results = stored

    progress_deltas: dict[str, dict] = {}
    if prev_results:
        progress_deltas = _compute_progress_deltas(results, prev_results)

    # Store progress deltas in session state for the report page.
    if progress_deltas:
        st.session_state["progress_deltas"] = list(progress_deltas.values())
    else:
        st.session_state.pop("progress_deltas", None)

    st.divider()
    st.subheader("Results")

    if progress_deltas:
        st.caption("Showing progress compared to previous assessment.")

    # Group by category in canonical order.
    cat_order = ["strength", "flexibility", "cardio", "body_comp"]
    grouped: dict[str, list[dict]] = {}
    for r in results:
        grouped.setdefault(r["category"], []).append(r)

    for cat_key in cat_order:
        cat_results = grouped.get(cat_key, [])
        if not cat_results:
            continue

        st.markdown(f"**{CATEGORY_LABELS.get(cat_key, cat_key)}**")
        cols = st.columns(min(len(cat_results), 4))

        for col, r in zip(cols, cat_results):
            badge = rating_badge_html(r["rating"])
            raw = r["raw_value"]
            value_str = str(int(raw)) if raw == int(raw) else f"{raw:.1f}"

            # Build optional delta indicator.
            delta_html = ""
            delta = progress_deltas.get(r["test_name"])
            if delta:
                delta_html = (
                    f'<div style="margin-top:4px;">'
                    f"{_delta_indicator_html(delta)}</div>"
                )

            # Build optional range bar.
            bar_html = ""
            if r.get("thresholds"):
                bar_html = render_range_bar_html(
                    value=raw,
                    thresholds=r["thresholds"],
                    inverted=r.get("inverted", False),
                )

            col.markdown(
                f'<div style="border:1px solid #e0e0e0;border-radius:6px;'
                f'padding:10px 12px;text-align:center;background:#fafafa;">'
                f'<div style="font-size:0.8em;color:#555;margin-bottom:4px;">'
                f'{r["test_name"]}</div>'
                f'<div style="font-size:1.2em;font-weight:700;margin-bottom:6px;">'
                f'{value_str}&nbsp;<span style="font-size:0.7em;color:#888;">'
                f'{r["unit"]}</span></div>'
                f"{badge}{delta_html}{bar_html}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    st.divider()
    st.page_link("pages/3_report.py", label="Continue to Report →")
