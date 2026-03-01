"""Strategy Library — drafts, production, graveyard."""

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
    st.markdown("Drafts, production, and graveyard strategies.")
    st.dataframe(
        pd.DataFrame(columns=["ID", "Name", "Status", "Sharpe", "DD", "Hit Rate"]),
        use_container_width=True,
        hide_index=True,
    )
    st.button("View Details")
    st.button("Export to Pine Script")
    with st.expander("Full Journal"):
        st.caption("Graveyard: failure mode, reason, metrics.")
    st.button("Retrigger Validation")
