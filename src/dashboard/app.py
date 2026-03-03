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
from src.dashboard.components import apply_theme, metric_card_simple, plotly_layout
from src.dashboard.config import THEME

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

# Strategy Profiles expander (nested tree)
with st.expander("Strategy Profiles (clickable tree: Strategy → Passed/Failed → Metrics)", expanded=False):
    st.caption("Strategy Name → Passed/Failed → Metrics/Chars. Wire to backend for live data.")
    profile_tree = [
        {"name": "RSI_H1", "status": "Passed", "metrics": "Sharpe 1.2, DD 12%", "chars": "Trending regime: High vol tolerance"},
        {"name": "Breakout_D1", "status": "Failed", "metrics": "Sharpe 0.8, DD 22%", "chars": "Failed in low-vol: DD >20%"},
    ]
    for p in profile_tree:
        st.markdown(f"- **{p['name']}** → {p['status']} — {p['metrics']} | {p['chars']}")
    st.button("View Full Profile", key="dashboard_view_profile")

# Row 2: Charts (P&L + Regime + Treemap + Radar)
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

# Strategy Profiles (nested expander)
with st.expander("📁 Strategy Profiles", expanded=False):
    st.caption("Clickable tree: Strategy Name → Passed/Failed → Metrics/Chars")
    profile_filter = st.multiselect("Filter Profiles", options=["passed", "failed"], default=[], key="dashboard_profile_filter", label_visibility="collapsed")
    # Placeholder tree: strategy → status → metrics
    for name, status in [("RSI_H1", "Passed"), ("Breakout_D1", "Failed"), ("MACD_Swing", "Passed")]:
        if profile_filter and status.lower() not in [f.lower() for f in profile_filter]:
            continue
        with st.expander(f"{name} — {status}", expanded=False):
            st.caption("Metrics/Chars" + (" — e.g. Trending regime: High vol tolerance" if status == "Passed" else " — Failed in low-vol: DD >20%"))
            if status == "Failed":
                st.error("Failed in low-vol: DD >20%")
            st.metric("Sharpe", "1.2" if status == "Passed" else "0.4", None)
            if st.button("View Full Profile", key=f"view_profile_{name}"):
                st.session_state["selected_profile"] = name
                st.info(f"Full profile for {name} (wire to modal or detail page).")

# Row 3: Recent Activity with 5 tabs
st.markdown('<div class="panel-header">📋 Recent Activity</div>', unsafe_allow_html=True)
tab_strategy, tab_ai, tab_market, tab_trade, tab_composite = st.tabs([
    "Strategy Profile", "AI Model Profile", "Market Profile", "Individual Trade Profile", "Composite Profile",
])
with tab_strategy:
    df_strat = pd.DataFrame([
        {"Name": "RSI_H1", "Status": "Passed", "Metrics JSON": '{"sharpe":1.2}', "Chars vs Market": "Trending regime: High vol tolerance"},
        {"Name": "Breakout_D1", "Status": "Failed", "Metrics JSON": "{}", "Chars vs Market": "Low-vol: DD >20%"},
    ])
    st.dataframe(df_strat, use_container_width=True, hide_index=True)
    st.button("View Full Profile", key="recent_view_profile")
with tab_ai:
    df_ai = pd.DataFrame([
        {"Model Type": "LSTM", "Params": "layers=2", "Training Metrics": "Overfit Score: Low"},
        {"Model Type": "PPO", "Params": "lr=3e-4", "Training Metrics": "Overfit Score: Low"},
    ])
    st.dataframe(df_ai, use_container_width=True, hide_index=True)
with tab_market:
    df_mkt = pd.DataFrame([
        {"Regime": "Trending", "Vol Clustering": "Yes", "Infrastructure Sims": "Order-Driven, Latency: 2ms"},
    ])
    st.dataframe(df_mkt, use_container_width=True, hide_index=True)
with tab_trade:
    df_trade = pd.DataFrame([
        {"Trade ID": "T001", "Entry/Exit": "100.5 / 101.2", "P&L": "+0.7%", "Slippage": "0.1pip", "Odds from Situational": "72%"},
    ])
    st.dataframe(df_trade, use_container_width=True, hide_index=True)
with tab_composite:
    st.metric("Overfit Score", "0.2", "0–1")
    st.metric("Market Correlation", "0.78", "0.5–1")
    st.metric("Regime Fit Ratio", "0.85", ">0.7")

# Row 4: Tree Map + Radar Chart
st.divider()
st.markdown('<div class="panel-header">📊 Nested Chars & Metrics Comparison</div>', unsafe_allow_html=True)
chart_row1, chart_row2 = st.columns(2)
with chart_row1:
    # Treemap: strategy vs market size by returns
    fig_treemap = go.Figure(go.Treemap(
        labels=["Strategy", "RSI_H1", "Breakout_D1", "Market", "Trending", "Ranging"],
        parents=["", "Strategy", "Strategy", "", "Market", "Market"],
        values=[100, 60, 40, 100, 70, 30],
        marker=dict(colors=["#161b22", "#3fb950", "#ef4444", "#161b22", "#58a6ff", "#8b949e"]),
    ))
    fig_treemap.update_layout(**plotly_layout(height=300), title="Nested Chars (size by returns)")
    st.plotly_chart(fig_treemap, use_container_width=True)
with chart_row2:
    # Radar: Sharpe/DD/Hit for passed vs failed
    categories = ["Sharpe", "Max DD", "Hit Rate", "Sortino", "e-ratio"]
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(r=[1.2, 0.6, 0.6, 1.1, 0.9], theta=categories, fill="toself", name="Passed"))
    fig_radar.add_trace(go.Scatterpolar(r=[0.4, 0.9, 0.4, 0.3, 0.5], theta=categories, fill="toself", name="Failed"))
    fig_radar.update_layout(polar=dict(bgcolor=THEME["surface"]), **plotly_layout(height=300), title="Metrics Comparison (Passed vs Failed)")
    st.plotly_chart(fig_radar, use_container_width=True)

# Decay warning placeholder
st.divider()
with st.expander("System Status (PM2, Neon, MT5)"):
    st.caption("Green/red indicators for PM2, Neon sync, MT5 will appear here when wired.")
