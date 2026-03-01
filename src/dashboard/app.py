"""
Trader-Suit — Streamlit entry point.
Sets wide layout, global theme, session state; renders Home/Dashboard.
Other pages live in pages/ (multipage).
"""

import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.dashboard.config import (
    API_BASE_URL,
    LAYOUT_SIDEBAR_MAIN_WIDE,
    DASHBOARD_DEFAULT_DAYS,
)
from src.dashboard.session_state import init_session_state, get_date_range
from src.dashboard.components import apply_theme, metric_card_simple

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Trader-Suit — Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
init_session_state()


def _fetch(endpoint: str, fallback):
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def _placeholder_pnl_chart(metrics):
    if not metrics:
        return
    pnl = metrics.get("pnl_pct", 0) or 0
    fig = go.Figure(go.Scatter(x=[1, 2, 3, 4, 5], y=[0, pnl * 0.3, pnl * 0.7, pnl, pnl]))
    fig.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22", font_color="#e6edf3", height=280, margin=dict(t=20, b=20, l=40, r=20))
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar (1:5 ratio per spec) ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Trader-Suit")
    st.markdown("**Home** — System overview")
    st.divider()

    alpaca_status = _fetch("/alpaca/status", {})
    if alpaca_status.get("connected"):
        st.success("Alpaca connected")
    else:
        st.caption("Alpaca: set ALPACA_API_KEY for live data")

    start, end = get_date_range()
    st.date_input("From", value=start, key="date_range_start")
    st.date_input("To", value=end, key="date_range_end")

    st.multiselect(
        "Regime",
        options=["Trending", "Ranging"],
        default=st.session_state.get("regime_filters", []),
        key="regime_filters",
        label_visibility="collapsed",
    )
    st.multiselect(
        "Session",
        options=["London", "NY", "Asia"],
        default=st.session_state.get("session_filters", []),
        key="session_filters",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(f"🔗 **API:** `{API_BASE_URL}`")
    st.caption(f"Last render: {datetime.utcnow().strftime('%H:%M:%S UTC')}")

# ── Main: Dashboard layout (1:5 sidebar already in sidebar) ─────────────────
st.markdown("# 🏠 Dashboard")
st.markdown("System health, performance, and quick actions.")
st.divider()

# Fetch metrics and activity (stub endpoints)
metrics = _fetch("/metrics", None)
activity = _fetch("/activity?limit=5", [])

# Row 1: Four metric cards
if metrics:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card_simple("P&L", f"{metrics.get('pnl_pct', 0):+.1f}%", metrics.get("delta_sharpe") and f"Sharpe Δ {metrics['delta_sharpe']:+.2f}")
    with c2:
        metric_card_simple("Sharpe Ratio", f"{metrics.get('sharpe', 0):.2f}", f"Sortino Δ {metrics.get('delta_sortino') or 0:+.2f}")
    with c3:
        metric_card_simple("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0):.1f}%", None)
    with c4:
        active = metrics.get("active_strategies", 0)
        total = metrics.get("total_strategies", 10)
        metric_card_simple("Active Strategies", f"{active}/{total}", None)
else:
    st.info("Cannot reach API. Start the backend with: `uvicorn src.api.main:app --reload`")

# Quick actions
col_btn1, col_btn2, _ = st.columns([1, 1, 2])
with col_btn1:
    if st.button("✨ New Alpha Idea", use_container_width=True):
        st.switch_page("pages/1_Alpha_Idea_Lab.py")
with col_btn2:
    if st.button("📡 View Live MT5 Feed", use_container_width=True):
        st.switch_page("pages/7_Execution_Reports.py")

st.divider()

# Row 2: Charts (P&L from Alpaca portfolio history when available)
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.markdown('<div class="panel-header">📈 Cumulative P&L</div>', unsafe_allow_html=True)
    hist_resp = _fetch("/portfolio/history?days=30", {})
    history = hist_resp.get("history") if isinstance(hist_resp, dict) else []
    if history and len(history) > 0:
        df = pd.DataFrame(history)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "pnl_pct" not in df.columns and "equity" in df.columns and len(df) > 0:
            base = df["equity"].iloc[0]
            df["pnl_pct"] = ((df["equity"] / base) - 1.0) * 100 if base else 0
        if not df.empty and "pnl_pct" in df.columns:
            df = df.dropna(subset=["pnl_pct"])
        if not df.empty and "pnl_pct" in df.columns:
            fig = go.Figure(go.Scatter(x=df["timestamp"] if "timestamp" in df.columns else df.index, y=df["pnl_pct"], mode="lines"))
            fig.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22", font_color="#e6edf3", height=280, margin=dict(t=20, b=20, l=40, r=20), xaxis_title="", yaxis_title="P&L %")
            st.plotly_chart(fig, use_container_width=True)
        else:
            _placeholder_pnl_chart(metrics)
    elif metrics:
        _placeholder_pnl_chart(metrics)
    else:
        st.caption("Connect API and set ALPACA_API_KEY to show P&L curve.")

with chart_col2:
    st.markdown('<div class="panel-header">📊 Regime breakdown (placeholder)</div>', unsafe_allow_html=True)
    st.caption("Regime performance chart will appear here.")

# Row 3: Recent activity table
st.markdown('<div class="panel-header">📋 Recent Activity</div>', unsafe_allow_html=True)
if activity:
    df = pd.DataFrame(activity)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.dataframe(pd.DataFrame(columns=["Timestamp", "Event", "Status"]), use_container_width=True, hide_index=True)
    st.caption("No recent activity. Run agents to populate.")

# Decay warning placeholder
st.divider()
with st.expander("System Status (PM2, Neon, MT5)"):
    st.caption("Green/red indicators for PM2, Neon sync, MT5 will appear here when wired.")
