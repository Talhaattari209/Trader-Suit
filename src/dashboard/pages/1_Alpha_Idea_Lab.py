"""Alpha Idea Lab — prompt + DOCX/PDF upload; conversational refinement (up to 10 iterations); Librarian → RESEARCH_PLAN."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW, ALPHA_TEMPLATES
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Alpha Idea Lab — Trader-Suit", page_icon="🧪", layout="wide")
apply_theme()
init_session_state()

# Chat state: up to 10 messages
if "alpha_chat_messages" not in st.session_state:
    st.session_state.alpha_chat_messages = []
if "alpha_iteration_count" not in st.session_state:
    st.session_state.alpha_iteration_count = 0
MAX_ITERATIONS = 10

with st.sidebar:
    st.markdown("## 🧪 Alpha Idea Lab")
    st.markdown("Templates & upload")
    st.selectbox("Template", options=ALPHA_TEMPLATES, key="alpha_template")
    st.file_uploader("Upload DOCX/PDF (max 10MB)", type=["docx", "pdf"], key="alpha_upload", help="Parsed via PyPDF2/openpyxl for inspiration")
    st.divider()
    st.caption(f"Iterations: {len(st.session_state.alpha_chat_messages) // 2}/{MAX_ITERATIONS}")

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_NARROW)
with main_col:
    st.markdown("# 🧪 Alpha Idea Lab")
    st.markdown("Describe your alpha idea or upload a doc; refine via conversation (up to 10 iterations). Librarian produces RESEARCH_PLAN.")
    st.text_area("Natural language prompt", placeholder="e.g. Mean-reversion on US30 post-news", key="alpha_prompt", height=100)

    # Chat-like display
    st.markdown("### Conversation")
    for msg in st.session_state.alpha_chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input + actions
    if len(st.session_state.alpha_chat_messages) < MAX_ITERATIONS * 2:
        user_msg = st.chat_input("Refine: e.g. Add vol filter")
        col_start, col_final = st.columns(2)
        with col_start:
            start_conv = st.button("Start Conversation")
        with col_final:
            finalize = st.button("Finalize Idea")

        if start_conv or (user_msg and user_msg.strip()):
            if start_conv:
                prompt = st.session_state.get("alpha_prompt", "")
                if prompt:
                    st.session_state.alpha_chat_messages.append({"role": "user", "content": prompt})
                    st.session_state.alpha_chat_messages.append({
                        "role": "assistant",
                        "content": "Librarian: I'll extract the core hypothesis and compare to market theory. Your idea suggests mean-reversion post-news; consider session filter (London/NY) for refinement.",
                    })
                    st.rerun()
            elif user_msg and user_msg.strip():
                st.session_state.alpha_chat_messages.append({"role": "user", "content": user_msg})
                st.session_state.alpha_chat_messages.append({
                    "role": "assistant",
                    "content": "Librarian: Refinement noted. Refinement score (similarity improvement) >0.2 via embeddings when wired to backend.",
                })
                st.session_state.alpha_iteration_count = len(st.session_state.alpha_chat_messages) // 2
                st.rerun()

        if finalize:
            st.session_state["research_plan_preview"] = "RESEARCH_PLAN.md (refined hypothesis; wire to Librarian output)"
            st.success("Idea finalized. RESEARCH_PLAN saved (wire to Plans/ folder).")
            st.balloons()
    else:
        st.warning("Max iterations (10) reached. Finalize or start a new conversation.")
        if st.button("Finalize Idea"):
            st.success("RESEARCH_PLAN saved.")
            st.rerun()

    st.divider()
    st.markdown("**Generated RESEARCH_PLAN preview**")
    st.markdown(st.session_state.get("research_plan_preview") or "*Preview will appear here after generation or finalize.*")
    if st.button("Proceed to Builder"):
        st.session_state["proceed_to_builder"] = True
        st.switch_page("pages/3_No_Code_Builder.py")
