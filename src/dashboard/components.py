"""
Shared UI components and layout helpers for Trader-Suit.
Use in all pages for consistent look and metric color-coding.
"""

import streamlit as st
from typing import Optional

try:
    from src.dashboard.config import (
        THEME,
        LAYOUT_SIDEBAR_MAIN,
        SHARPE_TARGET_MIN,
        SORTINO_TARGET_MIN,
        MAX_DD_TARGET_PCT,
        HIT_RATE_TARGET_MIN,
        E_RATIO_TARGET_MIN,
    )
except ImportError:
    THEME = {
        "background": "#0d1117",
        "surface": "#161b22",
        "border": "#30363d",
        "text": "#e6edf3",
        "text_muted": "#8b949e",
        "accent": "#58a6ff",
        "success": "#3fb950",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }
    LAYOUT_SIDEBAR_MAIN = (1, 4)
    SHARPE_TARGET_MIN = 1.0
    SORTINO_TARGET_MIN = 1.5
    MAX_DD_TARGET_PCT = 20.0
    HIT_RATE_TARGET_MIN = 0.55
    E_RATIO_TARGET_MIN = 1.5


def apply_theme() -> None:
    """Inject global dark theme CSS. Call once in main app.py."""
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: {THEME["background"]};
            color: {THEME["text"]};
        }}
        [data-testid="stSidebar"] {{
            background: {THEME["surface"]};
            border-right: 1px solid {THEME["border"]};
        }}
        .panel-header {{
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: {THEME["accent"]};
            border-bottom: 1px solid {THEME["border"]};
            padding-bottom: 6px;
            margin-bottom: 12px;
        }}
        .metric-card {{
            background: {THEME["surface"]};
            border: 1px solid {THEME["border"]};
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 10px;
        }}
    .metric-card.good {{ border-left: 4px solid {THEME["success"]}; }}
    .metric-card.bad {{ border-left: 4px solid {THEME["danger"]}; }}
    .metric-card.neutral {{ border-left: 4px solid {THEME["text_muted"]}; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
    /* Cockpit: signal cards and badges */
    .signal-card {{
        background: {THEME["surface"]};
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }}
    .signal-card:hover {{ border-color: {THEME["accent"]}; }}
    .badge-long {{ background:#1a7f37; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }}
    .badge-short {{ background:#b91c1c; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }}
    .badge-active {{ background:#1d4ed8; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }}
    .badge-pending {{ background:#92400e; color:#fff; border-radius:4px; padding:2px 8px; font-size:.75rem; }}
    .countdown {{ font-size: .85rem; color: #f0883e; font-weight: 600; }}
    </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str | float,
    delta: Optional[str | float] = None,
    threshold_min: Optional[float] = None,
    threshold_max: Optional[float] = None,
    numeric_value: Optional[float] = None,
) -> None:
    """
    Render a single metric with optional threshold color-coding.
    Green if value >= threshold_min (and <= threshold_max when max is set);
    Red otherwise. If no thresholds, neutral.
    numeric_value: used for threshold check when value is formatted string (e.g. "+12.5%").
    """
    if numeric_value is None and isinstance(value, (int, float)):
        numeric_value = float(value)
    use_val = numeric_value

    if threshold_min is not None and use_val is not None:
        good = use_val >= threshold_min
        if threshold_max is not None:
            good = good and use_val <= threshold_max
    elif threshold_max is not None and use_val is not None:
        good = use_val <= threshold_max  # e.g. Max DD: lower is better
    else:
        good = None

    if good is True:
        st.metric(label=label, value=value, delta=delta)
    elif good is False:
        st.metric(label=label, value=value, delta=delta)
        # Streamlit doesn't allow coloring metric per call; we use container + custom class
        # So we just render metric; theme can add global overrides or we use columns with custom HTML
    else:
        st.metric(label=label, value=value, delta=delta)


def metric_card_simple(label: str, value: str | float, delta: Optional[str | float] = None) -> None:
    """Simple metric with no threshold coloring."""
    st.metric(label=label, value=value, delta=delta)


# Threshold presets for common metrics (caller can pass numeric_value and these thresholds)
def metric_sharpe(value: float, delta: Optional[float] = None) -> None:
    """Sharpe: good if >= SHARPE_TARGET_MIN."""
    metric_card("Sharpe Ratio", f"{value:.2f}", f"+{delta:.2f}" if delta is not None else None,
                threshold_min=SHARPE_TARGET_MIN, numeric_value=value)


def metric_sortino(value: float, delta: Optional[float] = None) -> None:
    """Sortino: good if >= SORTINO_TARGET_MIN."""
    metric_card("Sortino Ratio", f"{value:.2f}", f"+{delta:.2f}" if delta is not None else None,
                threshold_min=SORTINO_TARGET_MIN, numeric_value=value)


def metric_max_dd(value: float, delta: Optional[float] = None) -> None:
    """Max Drawdown: good if <= MAX_DD_TARGET_PCT (e.g. 20%)."""
    metric_card("Max Drawdown", f"{value:.1f}%", f"{delta:+.1f}%" if delta is not None else None,
                threshold_max=MAX_DD_TARGET_PCT, numeric_value=value)


def metric_hit_rate(value: float, delta: Optional[float] = None) -> None:
    """Hit Rate: good if >= HIT_RATE_TARGET_MIN (0.55)."""
    metric_card("Hit Rate", f"{value:.0%}", f"+{delta:.0%}" if delta is not None else None,
                threshold_min=HIT_RATE_TARGET_MIN, numeric_value=value)


def metric_eratio(value: float, delta: Optional[float] = None) -> None:
    """E-ratio: good if >= E_RATIO_TARGET_MIN."""
    metric_card("E-Ratio", f"{value:.2f}", f"+{delta:.2f}" if delta is not None else None,
                threshold_min=E_RATIO_TARGET_MIN, numeric_value=value)


def layout_sidebar_main(ratio: tuple[int, int] = LAYOUT_SIDEBAR_MAIN):
    """Return (sidebar_col, main_col) for st.columns([s, m]). Use with 'with' context."""
    return st.columns([ratio[0], ratio[1]])
