"""Shared UI utilities used across all Streamlit pages.

Import at the top of each page:
    from utils import show_step_indicator, show_client_sidebar, rating_color
"""

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


def show_client_sidebar() -> None:
    """Render the saved-clients panel in the sidebar.

    Shows one button per saved client. Clicking a button loads that
    client's profile and clears any downstream calculation/report state.
    """
    client_list: list[dict] = st.session_state.get("client_list", [])
    if not client_list:
        return

    with st.sidebar:
        st.divider()
        st.markdown("**Saved Clients**")
        to_remove: int | None = None

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
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"_del_client_{i}", help="Remove from list"):
                    to_remove = i

        if to_remove is not None:
            st.session_state["client_list"].pop(to_remove)
            st.rerun()


def rating_color(rating: str) -> str:
    """Return a Streamlit markdown color name for the given rating tier.

    Args:
        rating: One of Excellent, Very Good, Good, Fair, Poor.

    Returns:
        A color string usable in Streamlit's :color[text] syntax.
    """
    return _RATING_COLORS.get(rating, "grey")


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
