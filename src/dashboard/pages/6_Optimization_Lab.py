"""Optimization Lab — PPO, Genetic, Ensemble tuning."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Optimization Lab — Trader-Suit", page_icon="⚙️", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## ⚙️ Optimization Lab")
    st.selectbox("Env", options=["US30 Gym (custom)"], key="opt_env")
    st.slider("Learning rate", 1e-5, 1e-1, 3e-4, format="%e")
    st.slider("Reward (Sharpe * Sortino)", 0.0, 2.0, 1.0)
    st.divider()

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN)
with main_col:
    st.markdown("# ⚙️ Optimization Lab")
    st.markdown("Tune RL/DL: PPO, Genetic, Ensemble.")
    tab1, tab2, tab3 = st.tabs(["PPO", "Genetic", "Ensemble"])
    with tab1:
        st.slider("Epochs", 10, 500, 100)
        if st.button("Train Model"):
            st.info("Run training on Colab/remote per project rules.")
    with tab2:
        st.caption("Genetic algorithm params.")
    with tab3:
        st.caption("Ensemble voting weights.")
    st.divider()
    st.markdown("**Best params** (placeholder)")
    st.dataframe(__import__("pandas").DataFrame(columns=["Mode", "Sharpe", "Sortino", "Kelly"]), use_container_width=True, hide_index=True)
    st.button("Save to Strategy")
    with st.expander("Code hooks"):
        st.caption("Editable for engineers.")
