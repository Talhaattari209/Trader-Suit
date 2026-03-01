"""
Execution & Reports — Cockpit (Signal Monitor, Risk Visualizer, Agent Status).
Reused by pages/7_Execution_Reports.py. Polls FastAPI /signals, /risk, /status.
"""

import time
import math
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

try:
    from src.dashboard.config import (
        API_BASE_URL,
        REFRESH_INTERVAL_SECONDS,
        VAR_WARNING_THRESHOLD,
        VAR_DANGER_THRESHOLD,
        DRAWDOWN_WARNING_PCT,
        DRAWDOWN_DANGER_PCT,
    )
except ImportError:
    API_BASE_URL = "http://localhost:8000"
    REFRESH_INTERVAL_SECONDS = 5
    VAR_WARNING_THRESHOLD = 2.0
    VAR_DANGER_THRESHOLD = 3.0
    DRAWDOWN_WARNING_PCT = 0.70
    DRAWDOWN_DANGER_PCT = 0.90


def _fetch(endpoint: str, fallback):
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def _fmt_countdown(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _confidence_bar(conf: float) -> str:
    filled = math.floor(conf * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar}  {conf*100:.0f}%"


def _agent_dot(status: str) -> str:
    mapping = {"HEALTHY": "🟢", "WARNING": "🟡", "DOWN": "🔴"}
    return mapping.get(status.upper(), "⚪")


def _var_color(var: float) -> str:
    if var >= VAR_DANGER_THRESHOLD:
        return "#ef4444"
    if var >= VAR_WARNING_THRESHOLD:
        return "#f59e0b"
    return "#22c55e"


def _drawdown_color(current: float, limit: float) -> str:
    ratio = current / limit if limit else 0
    if ratio >= DRAWDOWN_DANGER_PCT:
        return "#ef4444"
    if ratio >= DRAWDOWN_WARNING_PCT:
        return "#f59e0b"
    return "#22c55e"


def render_cockpit(refresh_interval_sec: int = 5, auto_refresh: bool = True) -> None:
    """Render Signal Monitor, Risk Visualizer, Agent Status. Optionally auto-refresh."""
    signals_data = _fetch("/signals?limit=8", [])
    risk_data = _fetch("/risk", {
        "portfolio_var": 0.0, "current_drawdown": 0.0,
        "max_drawdown_limit": 10.0, "exposure": {}
    })
    status_data = _fetch("/status", {"agents": [], "uptime_seconds": 0, "timestamp": "—"})

    col_signals, col_right = st.columns([1.4, 1], gap="large")

    with col_signals:
        st.markdown('<div class="panel-header">📡 Signal Monitor</div>', unsafe_allow_html=True)
        if not signals_data:
            st.info("No active signals. Waiting for Approved strategies…")
        else:
            for sig in signals_data:
                direction_badge = (
                    '<span class="badge-long">▲ LONG</span>'
                    if sig["direction"] == "LONG"
                    else '<span class="badge-short">▼ SHORT</span>'
                )
                status_badge = (
                    '<span class="badge-active">● ACTIVE</span>'
                    if sig["status"] == "ACTIVE"
                    else '<span class="badge-pending">◌ PENDING</span>'
                )
                countdown_str = _fmt_countdown(sig["candle_close_in_sec"])
                conf_bar = _confidence_bar(sig["confidence"])
                st.markdown(
                    f"""
                    <div class="signal-card">
                      <div class="symbol">{sig["symbol"]}
                        &nbsp;{direction_badge}&nbsp;{status_badge}
                        &nbsp;<span style="font-size:.8rem;color:#8b949e;">{sig["timeframe"]}</span>
                      </div>
                      <div class="strategy">{sig["strategy_name"]} &nbsp;·&nbsp; ID: {sig["id"]}</div>
                      <div style="display:flex;gap:24px;font-size:.82rem;">
                        <span>🎯 Confidence: <code>{conf_bar}</code></span>
                        <span class="countdown">⏱ Candle closes in: {countdown_str}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_right:
        st.markdown('<div class="panel-header">⚠️ Risk Visualizer</div>', unsafe_allow_html=True)
        var = risk_data.get("portfolio_var", 0.0)
        dd_cur = risk_data.get("current_drawdown", 0.0)
        dd_max = risk_data.get("max_drawdown_limit", 10.0)
        exposure = risk_data.get("exposure", {})

        gauge_color = _var_color(var)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=var,
            number={"suffix": "%", "font": {"color": gauge_color, "size": 28}},
            delta={"reference": VAR_WARNING_THRESHOLD, "increasing": {"color": "#ef4444"},
                   "decreasing": {"color": "#22c55e"}},
            gauge={
                "axis": {"range": [0, 5], "tickcolor": "#8b949e", "tickfont": {"color": "#8b949e"}},
                "bar": {"color": gauge_color},
                "bgcolor": "#161b22",
                "bordercolor": "#30363d",
                "steps": [
                    {"range": [0, VAR_WARNING_THRESHOLD], "color": "#1a2a1a"},
                    {"range": [VAR_WARNING_THRESHOLD, VAR_DANGER_THRESHOLD], "color": "#2a2010"},
                    {"range": [VAR_DANGER_THRESHOLD, 5], "color": "#2a1010"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 3},
                    "thickness": 0.8,
                    "value": VAR_DANGER_THRESHOLD,
                },
            },
            title={"text": "Portfolio VaR (1-Day, 95%)", "font": {"color": "#8b949e", "size": 13}},
        ))
        fig_gauge.update_layout(
            height=220, margin=dict(l=20, r=20, t=40, b=10),
            paper_bgcolor="#0d1117", font_color="#e6edf3",
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        dd_pct = (dd_cur / dd_max * 100) if dd_max else 0
        dd_col = _drawdown_color(dd_cur, dd_max)
        st.markdown(
            f"""
            <div style="margin-bottom:4px;font-size:.82rem;color:#8b949e;">
                Current Drawdown vs Max Limit &nbsp;
                <span style="color:{dd_col};font-weight:700;">{dd_cur:.1f}% / {dd_max:.1f}%</span>
            </div>
            <div style="background:#161b22;border-radius:6px;height:18px;border:1px solid #30363d;overflow:hidden;">
              <div style="width:{min(dd_pct,100):.1f}%;height:100%;background:{dd_col};
                          border-radius:6px;transition:width .4s;"></div>
            </div>
            <div style="font-size:.75rem;color:#8b949e;margin-top:3px;">{dd_pct:.1f}% of limit used</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if exposure:
            df_exp = pd.DataFrame(
                {"Asset Class": list(exposure.keys()), "Exposure (%)": list(exposure.values())}
            )
            fig_pie = px.pie(
                df_exp, names="Asset Class", values="Exposure (%)",
                color_discrete_sequence=["#58a6ff", "#3fb950", "#f0883e", "#bc8cff"],
                hole=0.45,
            )
            fig_pie.update_traces(textfont_color="#e6edf3", textfont_size=12)
            fig_pie.update_layout(
                height=240,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                legend=dict(font=dict(color="#8b949e"), bgcolor="#0d1117"),
                title=dict(text="Exposure by Asset Class", font=dict(color="#8b949e", size=13)),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.markdown('<div class="panel-header">🤖 Agent Status</div>', unsafe_allow_html=True)
        agents = status_data.get("agents", [])
        uptime = status_data.get("uptime_seconds", 0)
        if not agents:
            st.warning("Cannot reach API — agent status unavailable.")
        else:
            for agent in agents:
                dot = _agent_dot(agent["status"])
                color = {"HEALTHY": "#22c55e", "WARNING": "#f59e0b", "DOWN": "#ef4444"}.get(
                    agent["status"].upper(), "#8b949e"
                )
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:10px;
                                background:#161b22;border:1px solid #30363d;
                                border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                      <span style="font-size:1.4rem;">{dot}</span>
                      <div style="flex:1;">
                        <div style="font-weight:700;color:#e6edf3;">{agent["name"]}</div>
                        <div style="font-size:.75rem;color:#8b949e;">❤️ {agent["last_heartbeat"]}</div>
                      </div>
                      <div style="text-align:right;">
                        <div style="font-size:.8rem;color:{color};font-weight:600;">{agent["status"]}</div>
                        <div style="font-size:.72rem;color:#8b949e;">{agent["tasks_completed"]} tasks</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)
        st.caption(f"⏱ System uptime: {h}h {m:02d}m {s:02d}s  ·  {status_data.get('timestamp', '—')}")

    if auto_refresh:
        time.sleep(refresh_interval_sec)
        st.rerun()
