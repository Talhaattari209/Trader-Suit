"""Execution & Reports — Cockpit (signals, risk, agents) + Reports tab + Alpaca positions & live ticker."""

import requests
import streamlit as st
import pandas as pd
from src.dashboard.config import API_BASE_URL, REFRESH_INTERVAL_SECONDS
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state
from src.dashboard.cockpit import render_cockpit

st.set_page_config(page_title="Execution & Reports — Trader-Suit", page_icon="📡", layout="wide")
apply_theme()
init_session_state()


def _fetch(endpoint: str, fallback):
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


with st.sidebar:
    st.markdown("## 📡 Execution & Reports")
    st.markdown("Cockpit + briefings")
    refresh = st.slider("Refresh (s)", 2, 60, REFRESH_INTERVAL_SECONDS)
    auto_refresh = st.toggle("Auto-refresh", value=st.session_state.get("auto_refresh", True))
    st.session_state["auto_refresh"] = auto_refresh
    st.divider()
    alpaca_ok = _fetch("/alpaca/status", {}).get("connected", False)
    if alpaca_ok:
        st.success("Alpaca connected")
    st.caption(f"API: {API_BASE_URL}")

tab_exec, tab_reports = st.tabs(["Execution Monitor", "Reports"])
with tab_exec:
    st.markdown("# 📡 Execution Monitor")
    st.markdown("Real-time signals, risk, agent health.")

    # Live ticker (Alpaca) — updates every 10s when Alpaca connected
    quote = _fetch("/quote", None)
    if quote and isinstance(quote, dict) and (quote.get("bid") or quote.get("ask")):
        sym = quote.get("symbol", "—")
        mid = quote.get("mid")
        bid = quote.get("bid", 0)
        ask = quote.get("ask", 0)
        if mid is None and (bid or ask):
            mid = (float(bid) + float(ask)) / 2
        st.markdown(f"**Live ticker ({sym})** — Mid: **{mid:.2f}** (Bid: {bid:.2f} / Ask: {ask:.2f})")
    else:
        st.caption("Live ticker: set ALPACA_API_KEY and optional ALPACA_TICKER_SYMBOL (default SPY).")

    # Open positions (Alpaca)
    positions = _fetch("/positions", [])
    if positions and isinstance(positions, list):
        st.markdown("**Open positions**")
        if positions:
            rows = []
            for p in positions:
                rows.append({
                    "Symbol": p.get("symbol", ""),
                    "Side": p.get("side", ""),
                    "Qty": p.get("qty", 0),
                    "Entry": p.get("entry_price"),
                    "Current": p.get("current_price"),
                    "P&L": p.get("unrealized_pl"),
                    "Value": p.get("market_value"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No open positions.")
    st.divider()

    render_cockpit(refresh_interval_sec=refresh, auto_refresh=auto_refresh)
with tab_reports:
    st.markdown("# 📋 Reports")
    st.markdown("Monday Briefing, graveyard summaries, send report.")
    st.caption("Monday Briefing preview will appear here.")
    st.button("Send Report (Gmail/Telegram)")
    st.button("/failure_report — query journals")
    with st.expander("Graveyard Summaries"):
        st.caption("Failure journals and summaries.")
