"""Vault Explorer — file-based Obsidian vault (Needs_Action, Plans, Approved, Reports, Logs)."""

import streamlit as st
from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, VAULT_FOLDERS
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Vault Explorer — Trader-Suit", page_icon="📁", layout="wide")
apply_theme()
init_session_state()

with st.sidebar:
    st.markdown("## 📁 Vault Explorer")
    st.radio("Folder", options=list(VAULT_FOLDERS), key="selected_vault_folder", label_visibility="collapsed")
    st.text_input("Search files", key="vault_search", placeholder="Filter by name/hypothesis")
    st.divider()

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN)
with main_col:
    st.markdown("# 📁 Vault Explorer")
    st.markdown("Browse and manage vault files (Needs_Action, Plans, Approved, Reports, Logs).")
    left, right = st.columns(2)
    with left:
        st.markdown("**File list** (placeholder)")
        st.dataframe(
            __import__("pandas").DataFrame(columns=["Name", "Date", "Type", "Status"]),
            use_container_width=True,
            hide_index=True,
        )
        st.button("Upload File")
        st.button("Trigger Watcher")
    with right:
        st.markdown("**Preview**")
        st.caption("Select a file to preview.")
    st.divider()
    with st.expander("File metadata"):
        st.caption("Regime tags, linked strategies.")
