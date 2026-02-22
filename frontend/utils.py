"""Shared UI utilities used across all Streamlit pages.

Import at the top of each page:
    from utils import require_login, show_step_indicator, show_client_sidebar
"""

import httpx
import streamlit as st

_STEP_LABELS = ["Client Profile", "Assessment", "Report"]

# ── i18n helpers ───────────────────────────────────────────────────────────────

_SUPPORTED_LANGS = [
    {"code": "en", "name": "English", "flag": "🇺🇸"},
    {"code": "es", "name": "Español", "flag": "🇪🇸"},
    {"code": "fa", "name": "فارسی",  "flag": "🇮🇷"},
]


def load_translations(lang: str) -> dict:
    """Fetch the UI translation bundle from the backend and cache it.

    Args:
        lang: BCP 47 language code (``"en"``, ``"es"``, ``"fa"``).

    Returns:
        Translation dict; falls back to English on network error.
    """
    cache_key = f"_i18n_{lang}"
    cached = st.session_state.get(cache_key)
    # Only use the cache when it actually contains translations.
    # An empty cache (from a previous failed fetch) is treated as a miss so
    # the next render retries the request.
    if cached and cached.get("ui"):
        return cached  # type: ignore[return-value]
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    try:
        resp = httpx.get(f"{api_url}/i18n/{lang}", timeout=5)
        resp.raise_for_status()
        data: dict = resp.json()
    except Exception:
        # Do not cache failures — they will be retried on the next render.
        return {"ui": {}, "ratings": {}, "categories": {}, "goals": {}, "pdf": {}}
    st.session_state[cache_key] = data
    return data


def t(key: str, **kwargs: object) -> str:
    """Look up a UI translation string for the current session language.

    The key uses dot notation into the ``ui`` section of the bundle,
    e.g. ``t("login_title")``.  Format kwargs are interpolated if present.

    Args:
        key: Dot-separated key path within ``ui`` (e.g. ``"login_title"``).
        **kwargs: Named placeholders for ``.format()`` interpolation.

    Returns:
        Translated string, or the key itself when not found.
    """
    lang = st.session_state.get("lang", "en")
    bundle = load_translations(lang)
    ui = bundle.get("ui", {})
    text = ui.get(key, key)
    if kwargs:
        try:
            text = str(text).format(**kwargs)
        except (KeyError, ValueError):
            pass
    return str(text)

# ── Global CSS & page structure ────────────────────────────────────────────────


def inject_custom_css() -> None:
    """Inject global CSS for a professional, consistent UI look.

    Handles RTL layout automatically when the session language is Farsi.
    Called at the start of require_login() so styles are applied before
    any page content renders.
    """
    is_rtl = st.session_state.get("lang") == "fa"
    direction = "rtl" if is_rtl else "ltr"
    st.markdown(
        f"""<style>
        body {{ direction: {direction}; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        .main .block-container {{ padding-top: 0.75rem; }}

        /* ── Sidebar: dark navy ── */
        section[data-testid="stSidebar"] {{
            background: #1a1a2e;
            border-right: 1px solid rgba(255,255,255,0.07);
        }}
        /* All text in sidebar gets light color */
        section[data-testid="stSidebar"] * {{
            color: #c8cfe0 !important;
        }}
        /* Selectbox needs a visible background */
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.1) !important;
            border-color: rgba(255,255,255,0.2) !important;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.13);
            color: #dde2f0 !important;
            border-radius: 6px;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255,255,255,0.14);
            border-color: rgba(255,255,255,0.28);
        }}
        section[data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.1) !important;
        }}

        /* ── Primary button ── */
        div.stButton > button[kind="primary"] {{
            background: #1a1a2e;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            color: white;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background: #0f3460;
            box-shadow: 0 4px 12px rgba(26,26,46,0.22);
        }}

        /* ── Metric cards ── */
        div[data-testid="metric-container"] {{
            background: #ffffff;
            border: 1px solid #e0e4e8;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}

        /* ── Expander ── */
        div[data-testid="stExpander"] {{
            border: 1px solid #e0e4e8 !important;
            border-radius: 8px;
        }}

        /* ── Alerts / info boxes ── */
        div[data-testid="stAlert"] {{ border-radius: 8px; }}

        {"/* ── RTL markdown fix ── */" if is_rtl else ""}
        {"[data-testid='stMarkdownContainer'] { direction: rtl; text-align: right; }" if is_rtl else ""}
        {"[data-testid='stMarkdownContainer'] ul, [data-testid='stMarkdownContainer'] ol { padding-right: 1.5em; padding-left: 0; }" if is_rtl else ""}
        {"[data-testid='stMarkdownContainer'] li { text-align: right; }" if is_rtl else ""}
        {"[data-testid='stMarkdownContainer'] h1, [data-testid='stMarkdownContainer'] h2, [data-testid='stMarkdownContainer'] h3 { text-align: right; }" if is_rtl else ""}
        </style>""",
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str | None = None) -> None:
    """Render a styled gradient page header banner.

    Args:
        title: Main heading text displayed prominently.
        subtitle: Optional smaller text shown below the heading.
    """
    sub_html = (
        f'<p style="margin:6px 0 0;font-size:0.9em;opacity:0.92;">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%);'
        f'color:white;padding:18px 24px;border-radius:8px;margin-bottom:1.2rem;">'
        f'<h2 style="margin:0;font-size:1.3em;font-weight:700;">'
        f"{title}</h2>{sub_html}</div>",
        unsafe_allow_html=True,
    )


_RATING_COLORS: dict[str, str] = {
    "Excellent": "green",
    "Very Good": "green",
    "Good": "orange",
    "Fair": "red",
    "Poor": "red",
}

_BADGE_STYLES: dict[str, tuple[str, str]] = {
    # rating → (background, text color)
    "Excellent": ("#d4edda", "#155724"),
    "Very Good": ("#b8e8c8", "#0b5226"),
    "Good":      ("#c8f0c8", "#1e6b1e"),
    "Fair":      ("#fff3cd", "#7d5a00"),
    "Poor":      ("#f8d7da", "#721c24"),
}


# ── Authentication ─────────────────────────────────────────────────────────────

def require_login() -> None:
    """Guard: redirect to the login page if the session is not authenticated.

    Call this as the **first statement** in every page (after imports).
    Session timeout is handled centrally in ``app.py``.
    """
    inject_custom_css()
    if not st.session_state.get("authenticated"):
        st.switch_page("pages/login.py")
        st.stop()


# ── Step indicator ─────────────────────────────────────────────────────────────

def show_step_indicator(current_step: int) -> None:
    """Render a 3-step workflow indicator at the top of a page.

    Args:
        current_step: 1 = Client Profile, 2 = Assessment, 3 = Report.
    """
    step_labels = [
        t("step_client_profile"),
        t("step_assessment"),
        t("step_report"),
    ]
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, step_labels)):
        step_num = i + 1
        if step_num < current_step:
            bg, fg, prefix = "#d4edda", "#155724", "✓"
        elif step_num == current_step:
            bg, fg, prefix = "#1a1a2e", "#ffffff", str(step_num)
        else:
            bg, fg, prefix = "#e9ecef", "#6c757d", str(step_num)

        col.markdown(
            f'<div style="text-align:center;padding:8px 4px;background:{bg};'
            f'border-radius:4px;color:{fg};font-size:0.82em;font-weight:600;'
            f'margin-bottom:4px;">'
            f"{prefix}&nbsp;&nbsp;{label}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)


# ── Client sidebar ─────────────────────────────────────────────────────────────

def _refresh_client_list() -> None:
    """Fetch saved clients from the backend and update session state."""
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    coach = st.session_state.get("current_user", "")
    try:
        params = {"coach": coach} if coach else {}
        resp = httpx.get(f"{api_url}/clients", params=params, timeout=10)
        resp.raise_for_status()
        records = resp.json()  # list of ClientRecord dicts
        # Store name, profile, assessment history, and last assessment for sidebar.
        st.session_state["client_list"] = [
            {
                "name": r["name"],
                "profile": r["profile"],
                "last_assessment": r.get("last_assessment"),
                "assessment_history": r.get("assessment_history", []),
            }
            for r in records
        ]
    except Exception:
        # Non-fatal — sidebar will just show the cached list (or empty).
        pass


def show_client_sidebar() -> None:
    """Render the saved-clients panel in the sidebar.

    Fetches the latest client list from the backend on each render so
    it stays in sync across browser sessions. Provides load and delete
    buttons per client, and a logout button at the bottom.
    """
    _refresh_client_list()
    client_list: list[dict] = st.session_state.get("client_list", [])

    with st.sidebar:
        # Language selector — always visible when authenticated.
        lang_options = {
            lc["code"]: f"{lc['flag']} {lc['name']}" for lc in _SUPPORTED_LANGS
        }
        current_lang = st.session_state.get("lang", "en")
        selected_lang = st.selectbox(
            t("language_label"),
            options=list(lang_options.keys()),
            format_func=lambda c: lang_options[c],
            index=list(lang_options.keys()).index(current_lang),
            key="_lang_selector_sidebar",
        )
        if selected_lang != current_lang:
            st.session_state["lang"] = selected_lang
            st.rerun()

        display_name = st.session_state.get("display_name", "")
        if display_name:
            st.markdown(
                f'<div style="padding:8px 4px 4px;">'
                f'<div style="font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:0.08em;font-weight:600;opacity:0.6;">'
                f'{t("coach_label")}</div>'
                f'<div style="font-size:1.0em;font-weight:700;margin-top:2px;">'
                f"👤 {display_name}</div></div>",
                unsafe_allow_html=True,
            )

        if client_list:
            st.divider()
            st.markdown(f"**{t('saved_clients')}**")
            search_q = st.text_input(
                t("search_clients"),
                key="_client_search",
                placeholder=t("search_clients_placeholder"),
                label_visibility="collapsed",
            )
            if search_q:
                client_list = [
                    e for e in client_list
                    if search_q.lower() in e["name"].lower()
                ]
            to_delete: str | None = None

            for i, entry in enumerate(client_list):
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    if st.button(
                        entry["name"],
                        key=f"_load_client_{i}",
                        use_container_width=True,
                        help=t("load_client_help"),
                    ):
                        st.session_state["client_profile"] = entry["profile"]
                        for key in ("calculation", "report", "pdf_bytes"):
                            st.session_state.pop(key, None)
                        # Store assessment history for progress tracking.
                        st.session_state["assessment_history"] = entry.get(
                            "assessment_history", []
                        )
                        # Restore last assessment results if available.
                        if entry.get("last_assessment"):
                            st.session_state["calculation"] = {
                                "client": entry["profile"],
                                "results": entry["last_assessment"],
                            }
                        st.rerun()
                with col_del:
                    if st.button(
                        "✕",
                        key=f"_del_client_{i}",
                        help=t("remove_client_help"),
                    ):
                        to_delete = entry["name"]

            if to_delete is not None:
                _delete_client_from_backend(to_delete)
                st.rerun()

        # Logout button always shown when authenticated.
        if st.session_state.get("authenticated"):
            st.divider()
            if st.button(f"🚪 {t('logout')}", use_container_width=True):
                for key in ("authenticated", "current_user", "display_name",
                            "client_profile", "calculation", "report",
                            "pdf_bytes", "client_list", "_login_time"):
                    st.session_state.pop(key, None)
                st.rerun()


def save_client_to_backend(profile: dict) -> None:
    """Upsert a client profile to the backend.

    Sends the ``ClientProfile`` fields directly; the backend sets ``saved_at``.
    Attaches the current coach username so clients are scoped per coach.

    Args:
        profile: The client profile dictionary from session state.
    """
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    coach = st.session_state.get("current_user", "")
    try:
        params = {"coach": coach} if coach else {}
        resp = httpx.post(
            f"{api_url}/clients", json=profile, params=params, timeout=10
        )
        resp.raise_for_status()
    except Exception:
        pass  # Non-fatal — profile is already in session state.


def _delete_client_from_backend(name: str) -> None:
    """Delete a client by name from the backend.

    Args:
        name: The client name to delete.
    """
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    coach = st.session_state.get("current_user", "")
    try:
        httpx.delete(
            f"{api_url}/clients/{name}", params={"coach": coach}, timeout=10
        )
    except Exception:
        pass  # Non-fatal.


# ── Rating helpers ─────────────────────────────────────────────────────────────

def rating_color(rating: str) -> str:
    """Return a Streamlit markdown color name for the given rating tier.

    Args:
        rating: One of Excellent, Very Good, Good, Fair, Poor.

    Returns:
        A color string usable in Streamlit's :color[text] syntax.
    """
    return _RATING_COLORS.get(rating, "grey")


def _tr(rating: str) -> str:
    """Look up a translated rating label (Excellent/Very Good/Good/Fair/Poor).

    Args:
        rating: English rating key.

    Returns:
        Translated rating string for the current session language.
    """
    lang = st.session_state.get("lang", "en")
    bundle = load_translations(lang)
    return str(bundle.get("ratings", {}).get(rating, rating))


def render_range_bar_html(
    value: float,
    thresholds: dict[str, float],
    inverted: bool = False,
    is_rtl: bool = False,
) -> str:
    """Return inline HTML for a colored range bar with a marker at the value.

    The bar has 5 zones (Poor → Excellent) with:
    - abbreviated rating labels centered inside each zone
    - a triangle marker showing where the client's value falls
    - threshold boundary numbers below the bar

    For inverted tests (lower = better) the value axis is flipped.
    For RTL languages the zone order is reversed and the marker is mirrored.

    Args:
        value: The client's raw test result.
        thresholds: Dict with keys excellent, very_good, good, fair, poor.
        inverted: If True, lower values are better (e.g. step test BPM).
        is_rtl: If True, render for a right-to-left language (Farsi).

    Returns:
        HTML string for a styled range bar.
    """
    t_fair = thresholds["fair"]
    t_good = thresholds["good"]
    t_vgood = thresholds["very_good"]
    t_excellent = thresholds["excellent"]

    zone_defs = [
        ("#f8d7da", "Poor"),
        ("#fff3cd", "Fair"),
        ("#c8f0c8", "Good"),
        ("#b8e8c8", "V.Good"),
        ("#d4edda", "Exc."),
    ]

    if inverted:
        bar_min = min(t_excellent * 0.85, value * 0.85)
        bar_max = max(t_fair * 1.2, value * 1.1)
        total = bar_max - bar_min or 1
        widths = [
            (bar_max - t_fair) / total * 100,
            (t_fair - t_good) / total * 100,
            (t_good - t_vgood) / total * 100,
            (t_vgood - t_excellent) / total * 100,
            (t_excellent - bar_min) / total * 100,
        ]
        marker_pct = (bar_max - value) / total * 100
    else:
        bar_min = 0.0
        bar_max = max(t_excellent * 1.25, value * 1.1)
        total = bar_max - bar_min or 1
        widths = [
            (t_fair - bar_min) / total * 100,
            (t_good - t_fair) / total * 100,
            (t_vgood - t_good) / total * 100,
            (t_excellent - t_vgood) / total * 100,
            (bar_max - t_excellent) / total * 100,
        ]
        marker_pct = (value - bar_min) / total * 100

    widths = [max(w, 0.5) for w in widths]
    marker_pct = max(1, min(99, marker_pct))

    # Cumulative zone-boundary positions and their threshold values (LTR order).
    threshold_vals = [t_fair, t_good, t_vgood, t_excellent]
    cum, cumulative_pcts = 0.0, []
    for w in widths[:4]:
        cum += w
        cumulative_pcts.append(cum)

    if is_rtl:
        zone_defs = list(reversed(zone_defs))
        widths = list(reversed(widths))
        marker_pct = 100.0 - marker_pct
        marker_pct = max(1, min(99, marker_pct))
        # Mirror cumulative positions and reverse values to match new zone order.
        cumulative_pcts = [100.0 - p for p in reversed(cumulative_pcts)]
        threshold_vals = list(reversed(threshold_vals))

    def _fmt(v: float) -> str:
        return str(int(v)) if v == int(v) else f"{v:.1f}"

    zones_html = ""
    for (color, label), w in zip(zone_defs, widths):
        zones_html += (
            f'<div style="width:{w:.1f}%;background:{color};height:100%;'
            f'display:flex;align-items:center;justify-content:center;'
            f'box-sizing:border-box;border-right:1px solid rgba(0,0,0,0.08);'
            f'overflow:hidden;">'
            f'<span style="font-size:0.42em;color:rgba(0,0,0,0.45);'
            f'white-space:nowrap;">{label}</span></div>'
        )

    thresh_html = "".join(
        f'<span style="position:absolute;left:{p:.1f}%;'
        f'transform:translateX(-50%);font-size:0.48em;color:#999;">'
        f'{_fmt(v)}</span>'
        for p, v in zip(cumulative_pcts, threshold_vals)
    )

    return (
        f'<div style="position:relative;width:100%;margin:4px 0 14px 0;">'
        f'<div style="display:flex;height:14px;border-radius:4px;'
        f'overflow:hidden;border:1px solid #ddd;">{zones_html}</div>'
        f'<div style="position:absolute;top:-2px;left:{marker_pct:.1f}%;'
        f'transform:translateX(-50%);font-size:12px;line-height:1;'
        f'color:#1a1a2e;">&#9660;</div>'
        f'<div style="position:relative;height:10px;margin-top:1px;">'
        f'{thresh_html}</div>'
        f'</div>'
    )


def render_metric_chart(
    test_name: str,
    history: list[dict],
    thresholds: dict[str, float],
    inverted: bool,
    unit: str,
) -> None:
    """Render a Plotly line chart with zone backgrounds for a metric's history.

    Only renders when the metric appears in 2 or more history snapshots.
    History is expected newest-first (as returned by the backend); it is
    reversed internally so the chart runs oldest → newest left to right.

    Args:
        test_name: The metric name used to filter history snapshots.
        history: List of assessment snapshot dicts (each with ``results``
            and ``assessed_at`` keys).
        thresholds: Dict with keys ``excellent``, ``very_good``, ``good``,
            ``fair`` (boundary values for the 5 rating zones).
        inverted: If True, lower values are better (e.g. step-test BPM).
        unit: Unit string shown on the y-axis label.
    """
    import plotly.graph_objects as go  # type: ignore[import-untyped]

    # Build chronological (oldest → newest) (date_label, value) pairs.
    points: list[tuple[str, float]] = []
    for snap in reversed(history):
        assessed_at = str(snap.get("assessed_at", ""))[:16].replace("T", " ")
        for r in snap.get("results", []):
            if r.get("test_name") == test_name:
                points.append((assessed_at, float(r["raw_value"])))
                break

    if len(points) < 2:
        return

    dates, values = zip(*points)

    t_fair = thresholds["fair"]
    t_good = thresholds["good"]
    t_vgood = thresholds["very_good"]
    t_excellent = thresholds["excellent"]

    if inverted:
        y_min = min(t_excellent * 0.85, min(values) * 0.85)
        y_max = max(t_fair * 1.2, max(values) * 1.1)
        zone_bands = [
            (t_excellent, y_max, "#f8d7da"),
            (t_vgood, t_excellent, "#fff3cd"),
            (t_good, t_vgood, "#c8f0c8"),
            (t_fair, t_good, "#b8e8c8"),
            (y_min, t_fair, "#d4edda"),
        ]
    else:
        y_min = 0.0
        y_max = max(t_excellent * 1.25, max(values) * 1.1)
        zone_bands = [
            (y_min, t_fair, "#f8d7da"),
            (t_fair, t_good, "#fff3cd"),
            (t_good, t_vgood, "#c8f0c8"),
            (t_vgood, t_excellent, "#b8e8c8"),
            (t_excellent, y_max, "#d4edda"),
        ]

    fig = go.Figure()
    for y0, y1, color in zone_bands:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color, opacity=0.5,
            layer="below", line_width=0,
        )
    fig.add_trace(go.Scatter(
        x=list(dates),
        y=list(values),
        mode="lines+markers",
        marker=dict(size=8, color="#1a1a2e"),
        line=dict(color="#1a1a2e", width=2),
        hovertemplate="%{x}<br>%{y} " + unit + "<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title=unit,
        yaxis_range=[y_min, y_max],
        height=240,
        margin=dict(l=40, r=20, t=16, b=36),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        font=dict(size=11),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    st.plotly_chart(fig, use_container_width=True)


def rating_badge_html(rating: str) -> str:
    """Return an inline HTML badge for the given rating.

    Args:
        rating: One of Excellent, Very Good, Good, Fair, Poor.

    Returns:
        An HTML <span> string styled as a colored pill badge with
        the translated rating label for the current session language.
    """
    bg, fg = _BADGE_STYLES.get(rating, ("#e9ecef", "#333"))
    label = _tr(rating)
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:12px;font-size:0.85em;font-weight:700;">'
        f"{label}</span>"
    )
