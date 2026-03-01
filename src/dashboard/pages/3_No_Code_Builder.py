"""No-Code Strategy Builder — 8-step wizard, Strategist → drafts/."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_WIDE
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="No-Code Builder — Trader-Suit", page_icon="🔧", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## 🔧 No-Code Builder")
    step = st.slider("Step", 1, 8, 1)
    st.progress(step / 8)
    st.divider()
    st.caption("Agent suggestions will appear here.")

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_WIDE)
with main_col:
    st.markdown("# 🔧 No-Code Strategy Builder")
    st.markdown("Step-by-step wizard: data, features, model, then generate code.")
    tabs = st.tabs([f"Step {i}" for i in range(1, 9)])
    with tabs[step - 1]:
        st.selectbox("Model", options=["LSTM", "CNN", "Combo"], key=f"model_step{step}")
        st.slider("Layers", 1, 5, 2)
        st.slider("Dropout", 0.0, 0.5, 0.2)
        if st.button("Next"):
            st.rerun()
    st.divider()
    if st.button("Generate Code"):
        st.info("Strategist will write draft to src/models/drafts/.")
    with st.expander("Advanced Code View"):
        st.code("# Editable Python snippet", language="python")
