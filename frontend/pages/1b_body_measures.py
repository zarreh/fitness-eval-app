"""Body Measures page — log and track body measurements over time."""

import httpx
import streamlit as st
from utils import (
    rating_badge_html,
    render_metric_chart,
    render_page_header,
    render_range_bar_html,
    require_login,
    show_client_sidebar,
    t,
)

require_login()
show_client_sidebar()

render_page_header(t("body_measures_title"))

API_URL = st.session_state.get("api_url", "http://localhost:8000")

if "client_profile" not in st.session_state:
    st.warning(t("body_measures_profile_required"))
    st.page_link("pages/1_client_profile.py", label=t("body_measures_go_profile"))
    st.stop()

client = st.session_state["client_profile"]
coach = st.session_state.get("current_user", "")
client_name = client["name"]
gender = client.get("gender", "male")

# Show height info (stored on client profile, needed for BMI/BF% computation).
if not client.get("height_cm"):
    st.warning(
        f"⚠️ Height is not set on **{client_name}**'s profile. "
        "BMI and body fat % cannot be calculated without it. "
        "Please update the profile first."
    )
    st.page_link("pages/1_client_profile.py", label=f"→ {t('step_client_profile')}")
else:
    st.caption(
        f"👤 **{client_name}** · {client['age']} y/o · {client['gender'].title()} · "
        f"Height: {client['height_cm']} cm"
    )

# ── Thresholds for range bars (mirrors logic.py) ─────────────────────────────

_BMI_THRESHOLDS = {
    "excellent": 23.0,
    "very_good": 25.0,
    "good": 27.5,
    "fair": 30.0,
    "poor": 50.0,
}

_BF_THRESHOLDS: dict[str, dict[str, float]] = {
    "male": {
        "excellent": 13.0,
        "very_good": 17.0,
        "good": 24.0,
        "fair": 30.0,
        "poor": 60.0,
    },
    "female": {
        "excellent": 20.0,
        "very_good": 24.0,
        "good": 31.0,
        "fair": 38.0,
        "poor": 60.0,
    },
}

_WHR_THRESHOLDS: dict[str, dict[str, float]] = {
    "male": {
        "excellent": 0.85,
        "very_good": 0.90,
        "good": 0.95,
        "fair": 1.00,
        "poor": 1.50,
    },
    "female": {
        "excellent": 0.75,
        "very_good": 0.80,
        "good": 0.85,
        "fair": 0.90,
        "poor": 1.50,
    },
}

is_rtl = st.session_state.get("lang") == "fa"


# ── Fetch measurement history ─────────────────────────────────────────────────

def _fetch_records() -> list[dict]:
    try:
        resp = httpx.get(
            f"{API_URL}/clients/{client_name}/measurements",
            params={"coach": coach},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except httpx.ConnectError:
        st.error(t("login_backend_error"))
    return []


records = _fetch_records()

# ── Log new measurement ───────────────────────────────────────────────────────

with st.expander(t("measurement_log_expander"), expanded=not records):
    with st.form("measurement_form"):
        mc1, mc2 = st.columns(2)
        with mc1:
            m_weight = st.number_input(
                t("measurement_weight"), min_value=0.0, max_value=300.0,
                value=0.0, step=0.5,
            )
            m_waist = st.number_input(
                t("measurement_waist"), min_value=0.0, max_value=200.0,
                value=0.0, step=0.5,
            )
        with mc2:
            m_hip = st.number_input(
                t("measurement_hip"), min_value=0.0, max_value=200.0,
                value=0.0, step=0.5,
            )
            m_neck = st.number_input(
                t("measurement_neck"), min_value=0.0, max_value=80.0,
                value=0.0, step=0.5,
                help=t("profile_neck_help"),
            )
        m_submitted = st.form_submit_button(t("measurement_save"), type="primary")

    if m_submitted:
        payload = {
            k: v if v > 0 else None
            for k, v in {
                "weight_kg": m_weight,
                "waist_cm": m_waist,
                "hip_cm": m_hip,
                "neck_cm": m_neck,
            }.items()
        }
        try:
            resp = httpx.post(
                f"{API_URL}/clients/{client_name}/measurements",
                json=payload,
                params={"coach": coach},
                timeout=10,
            )
            if resp.status_code == 200:
                st.success(t("measurement_logged"))
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Error logging measurement."))
        except httpx.ConnectError:
            st.error(t("login_backend_error"))

if not records:
    st.info(t("body_measures_no_data"))
    st.stop()

# ── Current measurement cards with range bars ─────────────────────────────────

latest = records[0]  # newest first

st.divider()
st.markdown(f"#### {t('body_measures_current')}")

metric_cards = []

if latest.get("bmi") is not None:
    metric_cards.append({
        "label": t("body_measures_bmi"),
        "value": latest["bmi"],
        "unit": "kg/m²",
        "rating": None,
        "thresholds": _BMI_THRESHOLDS,
        "inverted": True,
    })

if latest.get("body_fat_pct") is not None:
    metric_cards.append({
        "label": t("body_measures_body_fat"),
        "value": latest["body_fat_pct"],
        "unit": "%",
        "rating": latest.get("body_fat_rating"),
        "thresholds": _BF_THRESHOLDS.get(gender, _BF_THRESHOLDS["male"]),
        "inverted": True,
    })

# WHR (computed from latest waist + hip)
waist = latest.get("waist_cm")
hip = latest.get("hip_cm")
if waist and hip and hip > 0:
    whr = round(waist / hip, 3)
    metric_cards.append({
        "label": t("body_measures_whr"),
        "value": whr,
        "unit": "",
        "rating": None,
        "thresholds": _WHR_THRESHOLDS.get(gender, _WHR_THRESHOLDS["male"]),
        "inverted": True,
    })

if latest.get("weight_kg") is not None:
    metric_cards.append({
        "label": t("body_measures_weight"),
        "value": latest["weight_kg"],
        "unit": "kg",
        "rating": None,
        "thresholds": None,
        "inverted": False,
    })

if latest.get("fat_mass_kg") is not None:
    metric_cards.append({
        "label": t("body_measures_fat_mass"),
        "value": latest["fat_mass_kg"],
        "unit": "kg",
        "rating": None,
        "thresholds": None,
        "inverted": False,
    })

if latest.get("lean_mass_kg") is not None:
    metric_cards.append({
        "label": t("body_measures_lean_mass"),
        "value": latest["lean_mass_kg"],
        "unit": "kg",
        "rating": None,
        "thresholds": None,
        "inverted": False,
    })

if metric_cards:
    # Show primary metrics (with range bars) in a row of up to 3 columns.
    primary = [c for c in metric_cards if c["thresholds"]]
    secondary = [c for c in metric_cards if not c["thresholds"]]

    if primary:
        cols = st.columns(min(len(primary), 3))
        for col, card in zip(cols, primary):
            raw = card["value"]
            value_str = f"{raw:.1f}" if isinstance(raw, float) else str(raw)
            badge = rating_badge_html(card["rating"]) if card["rating"] else ""
            bar_html = render_range_bar_html(
                value=raw,
                thresholds=card["thresholds"],
                inverted=card["inverted"],
                is_rtl=is_rtl,
            )
            unit_html = (
                f'<span style="font-size:0.7em;color:#888;">'
                f'&nbsp;{card["unit"]}</span>'
                if card["unit"] else ""
            )
            col.markdown(
                f'<div style="border:1px solid #e0e0e0;border-radius:6px;'
                f'padding:10px 12px;text-align:center;background:#fafafa;">'
                f'<div style="font-size:0.8em;color:#555;margin-bottom:4px;">'
                f'{card["label"]}</div>'
                f'<div style="font-size:1.2em;font-weight:700;margin-bottom:6px;">'
                f'{value_str}{unit_html}</div>'
                f"{badge}{bar_html}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    if secondary:
        cols2 = st.columns(min(len(secondary), 4))
        for col, card in zip(cols2, secondary):
            raw = card["value"]
            value_str = f"{raw:.1f}" if isinstance(raw, float) else str(raw)
            col.metric(card["label"], f"{value_str} {card['unit']}".strip())

# ── Historical charts ─────────────────────────────────────────────────────────

if len(records) >= 2:
    st.divider()
    with st.expander(f"📈 {t('body_measures_charts_expander')}", expanded=False):
        # Convert measurement records into the shape render_metric_chart expects:
        # list of dicts with "assessed_at" and "results" keys.
        def _to_chart_history(field: str, test_name: str, unit: str) -> list[dict]:
            """Build a fake assessment-history list for render_metric_chart."""
            out = []
            for r in records:
                val = r.get(field)
                if val is not None:
                    out.append({
                        "assessed_at": r["measured_at"],
                        "results": [{"test_name": test_name, "raw_value": val}],
                    })
            return out

        chart_specs = []
        if any(r.get("bmi") for r in records):
            chart_specs.append({
                "field": "bmi",
                "test_name": "BMI",
                "unit": "kg/m²",
                "thresholds": _BMI_THRESHOLDS,
                "inverted": True,
            })
        if any(r.get("body_fat_pct") for r in records):
            chart_specs.append({
                "field": "body_fat_pct",
                "test_name": "Body Fat %",
                "unit": "%",
                "thresholds": _BF_THRESHOLDS.get(gender, _BF_THRESHOLDS["male"]),
                "inverted": True,
            })
        # WHR derived from stored waist/hip
        whr_hist = []
        for r in records:
            w = r.get("waist_cm")
            h = r.get("hip_cm")
            if w and h and h > 0:
                whr_hist.append({
                    "assessed_at": r["measured_at"],
                    "results": [{"test_name": "WHR", "raw_value": round(w / h, 3)}],
                })
        if len(whr_hist) >= 2:
            chart_specs.append({
                "field": "_whr",
                "test_name": "WHR",
                "unit": "",
                "thresholds": _WHR_THRESHOLDS.get(gender, _WHR_THRESHOLDS["male"]),
                "inverted": True,
                "_custom_history": whr_hist,
            })

        for spec in chart_specs:
            hist = spec.get("_custom_history") or _to_chart_history(
                spec["field"], spec["test_name"], spec["unit"]
            )
            if len(hist) >= 2:
                render_metric_chart(
                    test_name=spec["test_name"],
                    history=hist,
                    thresholds=spec["thresholds"],
                    inverted=spec["inverted"],
                    unit=spec["unit"],
                )
else:
    st.caption(t("body_measures_charts_min2"))

# ── Full measurement history table ────────────────────────────────────────────

st.divider()
st.markdown(f"**{t('measurement_history')}**")

import pandas as pd

rows = []
for r in records:
    w = r.get("waist_cm")
    h = r.get("hip_cm")
    whr_val = round(w / h, 3) if w and h and h > 0 else None
    rows.append({
        t("measurement_date"): r["measured_at"][:16].replace("T", " "),
        t("measurement_weight"): r.get("weight_kg"),
        t("measurement_waist"): r.get("waist_cm"),
        t("measurement_hip"): r.get("hip_cm"),
        t("measurement_neck"): r.get("neck_cm"),
        t("body_measures_whr"): whr_val,
        t("measurement_bmi"): r.get("bmi"),
        t("measurement_body_fat"): r.get("body_fat_pct"),
        t("measurement_body_fat_rating"): r.get("body_fat_rating"),
        t("measurement_fat_mass"): r.get("fat_mass_kg"),
        t("measurement_lean_mass"): r.get("lean_mass_kg"),
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
