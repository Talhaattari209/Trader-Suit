"""Backtester & Killer — Monte Carlo Pro validation."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Backtester & Killer — Trader-Suit", page_icon="🎯", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## 🎯 Backtester & Killer")
    st.selectbox("Strategy to test", options=["(none)", "RSI_H1", "Breakout_D1"], key="backtest_strategy_id")
    st.slider("Iterations", 1000, 10000, 5000, step=1000, key="backtest_iterations")
    st.multiselect("Stress tests", options=["noise", "slippage", "regimes"], key="backtest_stress_tests")
    st.checkbox("Walk-Forward")
    st.checkbox("Out-of-Sample")
    st.divider()

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_NARROW)
with main_col:
    st.markdown("# 🎯 Backtester & Killer")
    st.markdown("Run Monte Carlo Pro; pass → production, fail → journal.")
    if st.button("Run Monte Carlo Pro"):
        st.spinner("Running…")
        st.info("Wire to monte_carlo_pro + Killer agent.")
    st.divider()
    st.markdown("**Results** (placeholder)")
    st.dataframe(__import__("pandas").DataFrame(columns=["Run", "Sharpe", "DD", "e-ratio", "Hit Rate"]), use_container_width=True, hide_index=True)
    st.button("Approve to Production")
    st.button("Journal Failure")
    with st.expander("Market param sims"):
        st.caption("Order types, slippage, etc.")
