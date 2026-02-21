"""Shared UI utilities used across all Streamlit pages.

Import at the top of each page:
    from utils import require_login, show_step_indicator, show_client_sidebar, rating_color
"""

import httpx
import streamlit as st

_STEP_LABELS = ["Client Profile", "Assessment", "Report"]

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
    """Enforce coach authentication on every page.

    If the current session is not authenticated, a login form is displayed
    and ``st.stop()`` is called so the rest of the page never renders.
    Call this as the **first statement** in every page (after imports).
    """
    if st.session_state.get("authenticated"):
        return

    # Centre the login card with empty columns.
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown(
            "<h2 style='text-align:center;margin-bottom:1.2rem;'>🏋️ Coach Login</h2>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            api_url = st.session_state.get("api_url", "http://localhost:8000")
            try:
                resp = httpx.post(
                    f"{api_url}/auth/login",
                    json={"username": username, "password": password},
                    timeout=10,
                )
                if resp.status_code == 200:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except httpx.ConnectError:
                st.error("Cannot reach the backend. Is the API server running?")

    st.stop()


# ── Step indicator ─────────────────────────────────────────────────────────────

def show_step_indicator(current_step: int) -> None:
    """Render a 3-step workflow indicator at the top of a page.

    Args:
        current_step: 1 = Client Profile, 2 = Assessment, 3 = Report.
    """
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, _STEP_LABELS)):
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
    try:
        resp = httpx.get(f"{api_url}/clients", timeout=10)
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
        if client_list:
            st.divider()
            st.markdown("**Saved Clients**")
            to_delete: str | None = None

            for i, entry in enumerate(client_list):
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    if st.button(
                        entry["name"],
                        key=f"_load_client_{i}",
                        use_container_width=True,
                        help="Load this client's profile",
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
                    if st.button("✕", key=f"_del_client_{i}", help="Remove client"):
                        to_delete = entry["name"]

            if to_delete is not None:
                _delete_client_from_backend(to_delete)
                st.rerun()

        # Logout button always shown when authenticated.
        if st.session_state.get("authenticated"):
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                for key in ("authenticated", "current_user", "client_profile",
                            "calculation", "report", "pdf_bytes", "client_list"):
                    st.session_state.pop(key, None)
                st.rerun()


def save_client_to_backend(profile: dict) -> None:
    """Upsert a client profile to the backend.

    Sends the ``ClientProfile`` fields directly; the backend sets ``saved_at``.

    Args:
        profile: The client profile dictionary from session state.
    """
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    try:
        resp = httpx.post(f"{api_url}/clients", json=profile, timeout=10)
        resp.raise_for_status()
    except Exception:
        pass  # Non-fatal — profile is already in session state.


def _delete_client_from_backend(name: str) -> None:
    """Delete a client by name from the backend.

    Args:
        name: The client name to delete.
    """
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    try:
        httpx.delete(f"{api_url}/clients/{name}", timeout=10)
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


def render_range_bar_html(
    value: float,
    thresholds: dict[str, float],
    inverted: bool = False,
) -> str:
    """Return inline HTML for a colored range bar with a marker at the value.

    The bar has 5 zones (Poor → Excellent) with a triangle marker showing
    where the client's value falls. For inverted tests (lower = better),
    the value axis is flipped so the marker still moves right for improvement.

    Args:
        value: The client's raw test result.
        thresholds: Dict with keys excellent, very_good, good, fair, poor.
        inverted: If True, lower values are better (e.g. step test BPM).

    Returns:
        HTML string for a styled range bar.
    """
    t_fair = thresholds["fair"]
    t_good = thresholds["good"]
    t_vgood = thresholds["very_good"]
    t_excellent = thresholds["excellent"]
    t_poor = thresholds["poor"]

    zone_colors = [
        ("#f8d7da", "Poor"),
        ("#fff3cd", "Fair"),
        ("#c8f0c8", "Good"),
        ("#b8e8c8", "V.Good"),
        ("#d4edda", "Excellent"),
    ]

    if inverted:
        # Lower is better. Flip axis so low values appear on the right (Excellent).
        bar_min = min(t_excellent * 0.85, value * 0.85)
        bar_max = max(t_fair * 1.2, value * 1.1)
        total = bar_max - bar_min
        if total <= 0:
            total = 1
        widths = [
            (bar_max - t_fair) / total * 100,
            (t_fair - t_good) / total * 100,
            (t_good - t_vgood) / total * 100,
            (t_vgood - t_excellent) / total * 100,
            (t_excellent - bar_min) / total * 100,
        ]
        marker_pct = (bar_max - value) / total * 100
    else:
        # Higher is better. Standard axis.
        bar_min = 0.0
        bar_max = max(t_excellent * 1.25, value * 1.1)
        total = bar_max - bar_min
        if total <= 0:
            total = 1
        widths = [
            (t_fair - bar_min) / total * 100,
            (t_good - t_fair) / total * 100,
            (t_vgood - t_good) / total * 100,
            (t_excellent - t_vgood) / total * 100,
            (bar_max - t_excellent) / total * 100,
        ]
        marker_pct = (value - bar_min) / total * 100

    # Clamp widths and marker.
    widths = [max(w, 0.5) for w in widths]
    marker_pct = max(1, min(99, marker_pct))

    zones_html = ""
    for (color, label), w in zip(zone_colors, widths):
        zones_html += (
            f'<div style="width:{w:.1f}%;background:{color};height:100%;'
            f'display:inline-block;box-sizing:border-box;'
            f'border-right:1px solid rgba(0,0,0,0.08);"></div>'
        )

    return (
        f'<div style="position:relative;width:100%;margin:4px 0 2px 0;">'
        # Zones bar
        f'<div style="display:flex;height:14px;border-radius:4px;'
        f'overflow:hidden;border:1px solid #ddd;">{zones_html}</div>'
        # Marker triangle
        f'<div style="position:absolute;top:-2px;left:{marker_pct:.1f}%;'
        f'transform:translateX(-50%);font-size:12px;line-height:1;'
        f'color:#1a1a2e;">&#9660;</div>'
        # Labels
        f'<div style="display:flex;font-size:0.55em;color:#888;margin-top:1px;">'
        f'<span style="flex:1;text-align:left;">Poor</span>'
        f'<span style="flex:1;text-align:center;">Good</span>'
        f'<span style="flex:1;text-align:right;">Excellent</span>'
        f'</div></div>'
    )


def rating_badge_html(rating: str) -> str:
    """Return an inline HTML badge for the given rating.

    Args:
        rating: One of Excellent, Very Good, Good, Fair, Poor.

    Returns:
        An HTML <span> string styled as a colored pill badge.
    """
    bg, fg = _BADGE_STYLES.get(rating, ("#e9ecef", "#333"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:12px;font-size:0.85em;font-weight:700;">'
        f"{rating}</span>"
    )
