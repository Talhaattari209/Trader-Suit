"""Strategy Library — Drafts, Production, Graveyard tabs; compare across tabs."""

import streamlit as st
import pandas as pd
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Strategy Library — Trader-Suit", page_icon="📚", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## 📚 Strategy Library")
    st.multiselect("Status", options=["drafts", "production", "graveyard"], key="library_filters")
    st.text_input("Search", key="library_search", placeholder="Name / hypothesis / failure mode")
    st.divider()

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN)
with main_col:
    st.markdown("# 📚 Strategy Library")
    st.markdown("Drafts, production, and graveyard strategies. Compare metrics across tabs.")
    st.metric("Survival Ratio (production vs graveyard)", "55%", ">50% target")

    tab_drafts, tab_production, tab_graveyard = st.tabs(["Drafts", "Production", "Graveyard"])

    with tab_drafts:
        df_d = pd.DataFrame([
            {"Name": "RSI_H1_v2", "Info": "Pending Killer", "Metrics": "Sharpe 1.1, DD 12%"},
            {"Name": "Breakout_D1_draft", "Info": "Not validated", "Metrics": "—"},
        ])
        st.dataframe(df_d, use_container_width=True, hide_index=True)
        with st.expander("Detailed Info — Drafts"):
            st.caption("Drafts: strategies in src/models/drafts/ awaiting Monte Carlo validation.")

    with tab_production:
        df_p = pd.DataFrame([
            {"Name": "RSI_H1", "Info": "Live", "Metrics": "Sharpe 1.2, DD 10%, Hit 58%"},
            {"Name": "MACD_Swing", "Info": "Live", "Metrics": "Sharpe 1.0, DD 15%"},
        ])
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        with st.expander("Detailed Info — Production"):
            st.caption("Production: passed Killer; in src/models/production/.")

    with tab_graveyard:
        df_g = pd.DataFrame([
            {"Name": "Breakout_D1", "Info": "Failed MC", "Metrics": "DD >20% in low-vol"},
            {"Name": "Momentum_H4", "Info": "Overfit", "Metrics": "OOS Sharpe <0.3"},
        ])
        st.dataframe(df_g, use_container_width=True, hide_index=True)
        with st.expander("Graveyard: Failure Journal"):
            st.caption("Failed strategies with journal: mode, reason, metrics. Review before retry.")

    if st.button("Compare Across Tabs"):
        st.info("Metrics diff: Production avg Sharpe 1.1 vs Graveyard 0.4. Survival ratio >50%.")
    st.button("View Details", key="lib_view_details")
    st.button("Export to Pine Script", key="lib_export_pine")
    st.button("Retrigger Validation", key="lib_retrigger")
