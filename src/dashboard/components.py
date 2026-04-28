"""
Shared UI components and layout helpers for Trader-Suit.
Use in all pages for consistent look and metric color-coding.
"""
from __future__ import annotations

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
    /* ── Responsive layout ───────────────────────────────────── */
    .main .block-container {{
        max-width: 100% !important;
        padding: 1rem 1rem 2rem !important;
    }}
    .stDataFrame {{ overflow-x: auto !important; }}
    .stButton > button,
    .stSelectbox select,
    .stMultiSelect,
    .stSlider {{ min-height: 44px; }}
    @media (max-width: 768px) {{
        [data-testid="column"] {{
            width: 100% !important;
            flex: 0 0 100% !important;
            min-width: 100% !important;
        }}
        .stSidebar {{ width: 100% !important; }}
    }}
    [data-testid="metric-container"] {{
        background: {THEME["surface"]};
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        padding: 12px;
        min-width: 120px;
    }}
    [data-testid="stPlotlyChart"] {{ width: 100% !important; }}
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


def plotly_layout(height: int = 320, margin: Optional[dict] = None, **kwargs) -> dict:
    """Return layout dict for Plotly charts (dark theme). Use in fig.update_layout(**plotly_layout())."""
    try:
        from src.dashboard.config import THEME as _T
    except ImportError:
        _T = THEME
    return {
        "paper_bgcolor": _T["background"],
        "plot_bgcolor":  _T["surface"],
        "font": {"color": _T["text"]},
        "height": height,
        "autosize": True,
        "margin": margin or dict(t=24, b=24, l=44, r=24),
        **kwargs,
    }


# ── Candlestick Trade Chart ────────────────────────────────────────────────────

def build_trade_chart(
    df_ohlcv,                        # pd.DataFrame: Open/High/Low/Close/Volume, DatetimeIndex
    trades: list[dict] | None = None,  # [{"timestamp", "side":"buy"|"sell", "price", "label"}]
    price_levels: dict | None = None,  # full price_levels dict from price_level_detector
    indicators: list[str] | None = None,  # ["SMA20","SMA50","EMA20","Bollinger Bands","RSI","ATR"]
    height: int = 520,
    show_liquidity: bool = True,
    show_fvg: bool = True,
    show_session: bool = True,
):
    """
    Build a Plotly candlestick chart (1H OHLCV) with:
    - Trade markers (buy=green ▲, sell=red ▼)
    - Price level overlays (liquidity zones, FVG rectangles, session lines)
    - Optional indicator overlays (SMA, EMA, Bollinger Bands, RSI subplot, ATR subplot)

    Returns a go.Figure.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    import pandas as pd

    from src.config.computation_budget import budget as CB
    indicators = indicators or []

    # Cap candles to budget limit — reduces Plotly render time significantly on local PC
    if df_ohlcv is not None and len(df_ohlcv) > CB.chart_max_candles:
        df_ohlcv = df_ohlcv.tail(CB.chart_max_candles)

    # Determine if we need RSI/ATR subplots
    has_rsi = "RSI" in indicators
    has_atr = "ATR" in indicators
    n_rows = 1 + (1 if has_rsi else 0) + (1 if has_atr else 0)
    row_heights = [0.6] + [0.2] * (n_rows - 1) if n_rows > 1 else [1.0]

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.03,
        subplot_titles=(["Price (1H)"] + (["RSI"] if has_rsi else []) + (["ATR"] if has_atr else [])),
    )

    # ── Candlesticks ──
    if df_ohlcv is not None and len(df_ohlcv) > 0:
        fig.add_trace(go.Candlestick(
            x=df_ohlcv.index,
            open=df_ohlcv["Open"],
            high=df_ohlcv["High"],
            low=df_ohlcv["Low"],
            close=df_ohlcv["Close"],
            name="Price",
            increasing_line_color="#3fb950",
            decreasing_line_color="#ef4444",
            increasing_fillcolor="#1a7f37",
            decreasing_fillcolor="#b91c1c",
        ), row=1, col=1)

        # ── Use indicator_engine for all TA calculations ──────────────────
        try:
            from src.tools.indicator_engine import compute_indicator as _ci
            _use_engine = True
        except ImportError:
            _use_engine = False

        def _ind(name: str, **kw):
            """Compute indicator via engine (falls back to pandas inline)."""
            if _use_engine:
                return _ci(name, df_ohlcv, **kw)
            return None

        # Colour palette for indicators
        _IND_COLORS = {
            "SMA20":           "#58a6ff",
            "SMA50":           "#f59e0b",
            "EMA20":           "#a371f7",
            "Bollinger Bands": "#8b949e",
            "VWAP":            "#3fb950",
            "WMA20":           "#ffa657",
            "HMA20":           "#ff7b72",
        }

        subplot_row = 2

        # ── Price-subplot indicators ──────────────────────────────────────
        if "SMA20" in indicators:
            s = _ind("SMA", length=20)
            if s is not None:
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=s,
                    name="SMA 20 (pandas_ta_classic)",
                    line=dict(color="#58a6ff", width=1.5),
                ), row=1, col=1)

        if "SMA50" in indicators:
            s = _ind("SMA", length=50)
            if s is not None:
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=s,
                    name="SMA 50 (pandas_ta_classic)",
                    line=dict(color="#f59e0b", width=1.5),
                ), row=1, col=1)

        if "EMA20" in indicators:
            s = _ind("EMA", length=20)
            if s is not None:
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=s,
                    name="EMA 20 (pandas_ta_classic)",
                    line=dict(color="#a371f7", width=1.5),
                ), row=1, col=1)

        if "Bollinger Bands" in indicators:
            bb = _ind("BBANDS", length=20, std=2.0)
            if bb is not None and hasattr(bb, "columns"):
                cols = list(bb.columns)
                lower_col = next((c for c in cols if c.startswith("BBL")), cols[0])
                upper_col = next((c for c in cols if c.startswith("BBU")), cols[-1])
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=bb[upper_col],
                    name="BB Upper", line=dict(color="#8b949e", width=1, dash="dot"),
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=bb[lower_col],
                    name="BB Lower", line=dict(color="#8b949e", width=1, dash="dot"),
                    fill="tonexty", fillcolor="rgba(88,166,255,0.05)",
                ), row=1, col=1)

        if "VWAP" in indicators:
            s = _ind("VWAP")
            if s is not None:
                if hasattr(s, "columns"):
                    s = s.iloc[:, 0]
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=s,
                    name="VWAP (pandas_ta_classic)",
                    line=dict(color="#3fb950", width=1.5, dash="dash"),
                ), row=1, col=1)

        # ── RSI subplot ──
        if has_rsi:
            rsi_series = _ind("RSI", length=14)
            if rsi_series is not None:
                if hasattr(rsi_series, "columns"):
                    rsi_series = rsi_series.iloc[:, 0]
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=rsi_series,
                    name="RSI 14 (pandas_ta_classic)",
                    line=dict(color="#f59e0b", width=1.5),
                ), row=subplot_row, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=subplot_row, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="#3fb950", row=subplot_row, col=1)
            subplot_row += 1

        # ── ATR subplot ──
        if has_atr:
            atr_series = _ind("ATR", length=14)
            if atr_series is not None:
                if hasattr(atr_series, "columns"):
                    atr_series = atr_series.iloc[:, 0]
                fig.add_trace(go.Scatter(
                    x=df_ohlcv.index, y=atr_series,
                    name="ATR 14 (pandas_ta_classic)",
                    line=dict(color="#a371f7", width=1.5),
                ), row=subplot_row, col=1)

    # ── Price level overlays ──
    if price_levels:
        shapes: list[dict] = []
        annotations: list[dict] = []

        # Liquidity zones
        if show_liquidity:
            for z in price_levels.get("liquidity_zones", []):
                color = "rgba(63,185,80,0.15)" if z["type"] == "demand" else "rgba(239,68,68,0.15)"
                line_color = "#3fb950" if z["type"] == "demand" else "#ef4444"
                price = z["price"]
                band  = price * 0.0008  # 0.08% band around zone price
                shapes.append(dict(
                    type="rect", xref="paper", yref="y",
                    x0=0, x1=1, y0=price - band, y1=price + band,
                    fillcolor=color, line_width=0, layer="below",
                ))
                shapes.append(dict(
                    type="line", xref="paper", yref="y",
                    x0=0, x1=1, y0=price, y1=price,
                    line=dict(color=line_color, width=1, dash="dot"),
                ))
                annotations.append(dict(
                    xref="paper", yref="y", x=1.01, y=price,
                    text=f"{z['type'].capitalize()} ({z['strength']})",
                    font=dict(size=10, color=line_color),
                    showarrow=False, xanchor="left",
                ))

        # FVG zones
        if show_fvg:
            x0_str = str(df_ohlcv.index[0]) if df_ohlcv is not None and len(df_ohlcv) > 0 else "0"
            x1_str = str(df_ohlcv.index[-1]) if df_ohlcv is not None and len(df_ohlcv) > 0 else "1"
            for fvg in price_levels.get("fvg_zones", []):
                color = "rgba(88,166,255,0.15)" if fvg["type"] == "bullish" else "rgba(245,158,11,0.15)"
                line_c = "#58a6ff" if fvg["type"] == "bullish" else "#f59e0b"
                shapes.append(dict(
                    type="rect", xref="paper", yref="y",
                    x0=0, x1=1, y0=fvg["low"], y1=fvg["high"],
                    fillcolor=color,
                    line=dict(color=line_c, width=0.5),
                    layer="below",
                ))

        # Session levels
        if show_session:
            sl = price_levels.get("session_levels", {})
            level_colors = {
                "day":  ("#e6edf3", "Day"),
                "week": ("#58a6ff", "Week"),
            }
            for key, (col, label) in level_colors.items():
                period = sl.get(key, {})
                for level_name, dash in [("high", "dash"), ("low", "dash"), ("open", "solid")]:
                    val = period.get(level_name)
                    if val is not None:
                        shapes.append(dict(
                            type="line", xref="paper", yref="y",
                            x0=0, x1=1, y0=val, y1=val,
                            line=dict(color=col, width=1, dash=dash),
                        ))
                        annotations.append(dict(
                            xref="paper", yref="y", x=0, y=val,
                            text=f"{label} {level_name.upper()}",
                            font=dict(size=9, color=col), showarrow=False, xanchor="right",
                        ))

        fig.update_layout(shapes=shapes, annotations=annotations)

    # ── Trade markers ──
    if trades:
        buy_trades  = [t for t in trades if t.get("side") == "buy"]
        sell_trades = [t for t in trades if t.get("side") == "sell"]

        if buy_trades:
            fig.add_trace(go.Scatter(
                x=[t["timestamp"] for t in buy_trades],
                y=[t["price"] for t in buy_trades],
                mode="markers+text",
                name="Buy",
                text=[t.get("label", "B") for t in buy_trades],
                textposition="bottom center",
                marker=dict(symbol="triangle-up", size=12, color="#3fb950",
                            line=dict(color="#fff", width=1)),
            ), row=1, col=1)

        if sell_trades:
            fig.add_trace(go.Scatter(
                x=[t["timestamp"] for t in sell_trades],
                y=[t["price"] for t in sell_trades],
                mode="markers+text",
                name="Sell",
                text=[t.get("label", "S") for t in sell_trades],
                textposition="top center",
                marker=dict(symbol="triangle-down", size=12, color="#ef4444",
                            line=dict(color="#fff", width=1)),
            ), row=1, col=1)

    # ── Layout ──
    try:
        from src.dashboard.config import THEME as _T
    except ImportError:
        _T = THEME

    fig.update_layout(
        height=height,
        autosize=True,
        paper_bgcolor=_T["background"],
        plot_bgcolor=_T["surface"],
        font=dict(color=_T["text"]),
        margin=dict(t=30, b=30, l=60, r=80),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(22,27,34,0.8)",
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=_T["border"], showgrid=True)
    fig.update_yaxes(gridcolor=_T["border"], showgrid=True)

    return fig
