"""Backtester & Killer — Monte Carlo Pro; MC Profiles tab, Violin plot, Trigger Colab MC."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW, COLAB_NOTEBOOK_URL
from src.dashboard.components import apply_theme, plotly_layout
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
    st.markdown("Run Monte Carlo Pro; pass → production, fail → journal. MC Profiles for deep characteristics.")
    tab_runs, tab_mc_profiles = st.tabs(["Runs & Results", "MC Profiles"])

    with tab_runs:
        if st.button("Run Monte Carlo Pro"):
            with st.spinner("Running…"):
                st.info("Wire to monte_carlo_pro + Killer agent. Use **Trigger Colab MC** for heavy runs.")
        st.divider()
        st.markdown("**Results** (placeholder)")
        df_results = pd.DataFrame([
            {"Run": "MC_001", "Sharpe": 1.2, "DD": 12, "e-ratio": 1.4, "Hit Rate": "58%"},
            {"Run": "MC_002", "Sharpe": 0.8, "DD": 18, "e-ratio": 1.0, "Hit Rate": "52%"},
        ])
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        st.button("Approve to Production")
        st.button("Journal Failure")
        with st.expander("Market param sims"):
            st.caption("Order types, slippage, etc.")

    with tab_mc_profiles:
        st.markdown("**MC Profiles** — list of runs with deep characteristics.")
        df_mc = pd.DataFrame([
            {"Run ID": "MC_001", "Chars": "Noise Level: 2pip, Regime: Trending"},
            {"Run ID": "MC_002", "Chars": "Noise Level: 3pip, Regime: Ranging"},
        ])
        st.dataframe(df_mc, use_container_width=True, hide_index=True)
        if st.button("View Profile", key="mc_view_profile"):
            st.info("Modal with details: metrics, sim params, failure odds.")
        if st.button("Trigger Colab MC", type="primary"):
            st.success("Heavy MC runs on Colab. Open notebook below.")
            st.link_button("Open Colab notebook", url=COLAB_NOTEBOOK_URL, type="secondary")
        with st.expander("Deep Profile (per run)"):
            st.caption("Metrics, sim params, failure odds per run.")
        st.metric("Robustness Ratio (passed sims)", "82%", ">80%")
        st.metric("Characteristic Depth", "10+ params", "analyzed")
        # Violin: characteristic distributions (e.g. slippage across runs)
        st.markdown("**Characteristic Distributions**")
        np.random.seed(42)
        slippage_a = np.random.randn(100) * 0.5 + 1.2
        slippage_b = np.random.randn(100) * 0.6 + 1.5
        fig_violin = go.Figure()
        fig_violin.add_trace(go.Violin(y=slippage_a, name="Run A", box_visible=True, line_color="#58a6ff"))
        fig_violin.add_trace(go.Violin(y=slippage_b, name="Run B", box_visible=True, line_color="#3fb950"))
        fig_violin.update_layout(**plotly_layout(height=300), yaxis_title="Slippage (pip)")
        st.plotly_chart(fig_violin, use_container_width=True)
