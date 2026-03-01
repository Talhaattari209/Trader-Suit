"""Alpha Idea Lab — prompt-based alpha generation, Librarian → RESEARCH_PLAN."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW, ALPHA_TEMPLATES
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Alpha Idea Lab — Trader-Suit", page_icon="🧪", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## 🧪 Alpha Idea Lab")
    st.markdown("Templates & examples")
    st.selectbox("Template", options=ALPHA_TEMPLATES, key="alpha_template")
    st.divider()

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_NARROW)
with main_col:
    st.markdown("# 🧪 Alpha Idea Lab")
    st.markdown("Describe your alpha idea in natural language; generate a hypothesis and RESEARCH_PLAN.")
    st.text_area("Natural language prompt", placeholder="e.g. Mean-reversion on US30 post-news", key="alpha_prompt", height=120)
    if st.button("Generate Hypothesis"):
        st.info("Librarian agent will produce RESEARCH_PLAN (wire to run_instruction).")
    st.divider()
    st.markdown("**Generated RESEARCH_PLAN preview**")
    st.markdown("*Preview will appear here after generation.*")
    if st.button("Proceed to Builder"):
        st.session_state["proceed_to_builder"] = True
        st.switch_page("pages/3_No_Code_Builder.py")
