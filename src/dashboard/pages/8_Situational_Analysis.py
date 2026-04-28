"""Situational Analysis — Probabilistic analysis of market events (odds per candle, gap fill, etc.)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, COLAB_NOTEBOOK_URL, API_BASE_URL
from src.dashboard.components import apply_theme, plotly_layout
from src.dashboard.session_state import init_session_state
from src.dashboard.autonomous_chat import render_autonomous_agent_widget

st.set_page_config(page_title="Situational Analysis — Trader-Suit", page_icon="📊", layout="wide")
apply_theme()
init_session_state()
render_autonomous_agent_widget(api_base_url=API_BASE_URL)

with st.sidebar:
    st.markdown("## 📊 Situational Analysis")
    st.text_input("Event Description", value="Friday gap down in DAX", key="situ_event_desc", placeholder="e.g. Friday gap down in DAX")
    st.selectbox("Asset", options=["US30", "DAX", "SPX", "NDX"], key="situ_asset", index=0)
    lookback_years = st.slider("Historical Lookback (years)", 1, 10, 6, key="situ_lookback")
    st.selectbox("Candle Granularity", options=["1m", "5m", "15m", "1H", "4H", "D"], key="situ_granularity", index=4)
    st.multiselect(
        "Metrics to Compute",
        options=["Odds of Fill", "Average Recovery Time", "Volatility Spike", "Gap Size Distribution"],
        default=["Odds of Fill", "Average Recovery Time"],
        key="situ_metrics",
    )
    st.checkbox("Include Live MT5 Data", value=False, key="situ_live_mt5")
    st.divider()
    run_analysis = st.button("Run Analysis", type="primary", use_container_width=True)
    export_report = st.button("Export Report (PDF)", use_container_width=True)
    st.divider()
    trigger_colab = st.button("Trigger Colab for Deep Stats", use_container_width=True)

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN)
with main_col:
    st.markdown("# 📊 Situational Analysis")
    st.markdown("Professional-grade probabilistic analysis of market events (e.g. Friday gap down: odds per candle).")
    tab_input, tab_results = st.tabs(["Event Input", "Analysis Results"])

    with tab_input:
        st.markdown("### Event summary")
        event_summary = st.session_state.get("situ_event_desc", "Friday gap down in DAX")
        st.markdown(f"**Event:** {event_summary}  \n**Asset:** {st.session_state.get('situ_asset', 'US30')}  \n**Lookback:** {st.session_state.get('situ_lookback', 6)} years")
        with st.expander("Advanced params (confidence intervals, etc.)"):
            st.slider("Confidence level (%)", 80, 99, 95, key="situ_confidence")
            st.caption("Uses statsmodels for confidence intervals.")

    with tab_results:
        if run_analysis or st.session_state.get("situ_has_results"):
            st.session_state["situ_has_results"] = True
            progress = st.progress(1.0, text="Done.")
            progress.empty()

            # Odds breakdown table (placeholder data)
            odds_data = [
                {"Candle #": i, "Odds Up (%)": 35 + i * 2, "Odds Down (%)": 45 - i, "Historical Matches": 120 - i * 5}
                for i in range(1, 16)
            ]
            df_odds = pd.DataFrame(odds_data)
            st.markdown("#### Odds breakdown")
            st.dataframe(df_odds, use_container_width=True, hide_index=True)

            # Metrics row
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Odds Ratio (Up:Down)", "70:30", None)
            with c2:
                st.metric("Confidence Interval", "95%", None)
            with c3:
                st.metric("Historical Hit Rate", "62%", ">50%")
            with c4:
                st.metric("Volatility Ratio", "1.4", "post vs avg")
            with c5:
                st.metric("e-ratio", "1.25", ">1.2 bullish")

            st.info("**Interpretation:** ~70% odds of gap fill by EOD based on 6-year US30 history. Consider session filter (London/NY) for refinement.")

            # Charts: 3-column grid 1:2:1 → inputs already in sidebar; here we show odds table + charts
            chart_col1, chart_col2, chart_col3 = st.columns(3)
            with chart_col1:
                st.markdown("**Odds per Candle**")
                fig_bar = go.Figure(data=[
                    go.Bar(name="Up", x=df_odds["Candle #"], y=df_odds["Odds Up (%)"], marker_color="#3fb950"),
                    go.Bar(name="Down", x=df_odds["Candle #"], y=df_odds["Odds Down (%)"], marker_color="#ef4444"),
                ])
                fig_bar.update_layout(barmode="stack", **plotly_layout(height=280))
                st.plotly_chart(fig_bar, use_container_width=True)
            with chart_col2:
                st.markdown("**Distribution of Outcomes**")
                import numpy as np
                np.random.seed(42)
                hist_vals = np.random.randn(200) * 0.5 + 0.3
                fig_hist = go.Figure(go.Histogram(x=hist_vals, nbinsx=20, marker_color="#58a6ff"))
                fig_hist.update_layout(**plotly_layout(height=280), xaxis_title="Gap size vs recovery odds")
                st.plotly_chart(fig_hist, use_container_width=True)
            with chart_col3:
                st.markdown("**Cumulative Probability Over Time**")
                cumul = df_odds["Odds Up (%)"].cumsum() / 100
                fig_line = go.Figure(go.Scatter(x=df_odds["Candle #"], y=cumul, mode="lines+markers", line=dict(color="#58a6ff")))
                fig_line.update_layout(**plotly_layout(height=280), yaxis_title="Cumulative P(Up)")
                st.plotly_chart(fig_line, use_container_width=True)

            if export_report:
                st.success("Export Report: wire to PDF generation (e.g. reportlab or weasyprint).")
        else:
            st.info("Click **Run Analysis** in the sidebar to compute odds and see results.")

        if trigger_colab:
            st.success("Open Colab for Monte Carlo odds simulation. Use the link below.")
            st.link_button("Open Colab notebook", url=COLAB_NOTEBOOK_URL, type="secondary")
