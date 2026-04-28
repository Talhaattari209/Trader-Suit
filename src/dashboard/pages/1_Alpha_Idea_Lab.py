"""Alpha Idea Lab — submit ideas, similarity comparison, price levels, workflow start."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW, ALPHA_TEMPLATES
from src.dashboard.components import apply_theme, plotly_layout
from src.dashboard.session_state import init_session_state
from src.dashboard.autonomous_chat import render_autonomous_agent_widget

try:
    from src.dashboard.config import API_BASE_URL
except ImportError:
    API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Alpha Idea Lab — Trader-Suit", page_icon="🧪", layout="wide")
apply_theme()
init_session_state()
render_autonomous_agent_widget(api_base_url=API_BASE_URL)


def _api(method: str, path: str, **kwargs):
    try:
        import httpx
        r = getattr(httpx, method)(f"{API_BASE_URL}{path}", **kwargs, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Chat state ────────────────────────────────────────────────────────────────
if "alpha_chat_messages" not in st.session_state:
    st.session_state.alpha_chat_messages = []
if "alpha_iteration_count" not in st.session_state:
    st.session_state.alpha_iteration_count = 0
MAX_ITERATIONS = 10

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧪 Alpha Idea Lab")
    st.selectbox("Template", options=ALPHA_TEMPLATES, key="alpha_template")
    st.file_uploader(
        "Upload DOCX/PDF (max 10MB)", type=["docx", "pdf"],
        key="alpha_upload", help="Parsed for hypothesis extraction",
    )
    st.divider()
    st.caption(f"Iterations: {len(st.session_state.alpha_chat_messages) // 2}/{MAX_ITERATIONS}")
    if st.session_state.get("workflow_id"):
        st.success(f"Workflow: `{st.session_state['workflow_id']}`")
    if st.session_state.get("alpha_id"):
        st.info(f"Alpha: `{st.session_state['alpha_id']}`")

# ── Main ──────────────────────────────────────────────────────────────────────
sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_NARROW)
with main_col:
    st.markdown("# 🧪 Alpha Idea Lab")
    st.markdown(
        "Describe your alpha idea. The Librarian will analyse it, compare against existing alphas, "
        "and snapshot current 1H price levels. Then decide how to proceed."
    )

    # ── Idea input ────────────────────────────────────────────────────────────
    st.text_area(
        "Natural language prompt",
        placeholder="e.g. Volume spike at US30 session open predicts momentum",
        key="alpha_prompt", height=100,
    )

    col_gen, col_clear = st.columns([3, 1])
    generate = col_gen.button("🚀 Generate Hypothesis", type="primary", use_container_width=True)
    if col_clear.button("Clear", use_container_width=True):
        st.session_state.alpha_chat_messages = []
        st.session_state.pop("workflow_id", None)
        st.session_state.pop("alpha_id", None)
        st.session_state.pop("workflow_result", None)
        st.rerun()

    # ── Submit idea to API ────────────────────────────────────────────────────
    if generate:
        idea = st.session_state.get("alpha_prompt", "").strip()
        if not idea:
            st.warning("Please enter an idea first.")
        else:
            with st.spinner("Librarian analysing idea and detecting 1H price levels…"):
                result = _api("post", "/workflow/start", json={
                    "idea": idea,
                    "template": st.session_state.get("alpha_template"),
                })
            if "error" in result:
                st.error(f"API error: {result['error']}")
            else:
                st.session_state["workflow_id"]   = result.get("workflow_id")
                st.session_state["alpha_id"]      = result.get("alpha_id")
                st.session_state["workflow_result"] = result
                st.session_state.alpha_chat_messages.append({"role": "user", "content": idea})
                st.session_state.alpha_chat_messages.append({
                    "role": "assistant",
                    "content": (
                        f"Librarian: Hypothesis received. Alpha ID `{result.get('alpha_id')}` "
                        f"created. Price levels detected on 1H data. "
                        f"Found {len(result.get('similar_alphas', []))} similar alphas in DataStore."
                    ),
                })
                st.rerun()

    # ── Conversation history ──────────────────────────────────────────────────
    if st.session_state.alpha_chat_messages:
        st.markdown("### Conversation")
        for msg in st.session_state.alpha_chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ── Similarity report + price levels (after submission) ──────────────────
    result = st.session_state.get("workflow_result")
    if result:
        similar = result.get("similar_alphas", [])
        if similar:
            st.subheader("🔍 Similarity Report")
            for s in similar:
                col_name, col_score = st.columns([4, 1])
                col_name.write(s.get("hypothesis", s.get("alpha_id", "?"))[:80])
                col_score.metric("Score", f"{s.get('score', 0):.0%}")

        pl = result.get("price_levels", {})
        if pl:
            with st.expander("📈 Price Levels at Idea Submission (1H)", expanded=True):
                col_lz, col_fvg = st.columns(2)
                with col_lz:
                    st.markdown("**Liquidity Zones**")
                    lz = pl.get("liquidity_zones", [])
                    if lz:
                        st.dataframe(
                            pd.DataFrame(lz)[["type", "price", "strength"]].head(10),
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.caption("None detected")
                with col_fvg:
                    st.markdown("**FVG Zones**")
                    fvgs = pl.get("fvg_zones", [])
                    if fvgs:
                        st.dataframe(
                            pd.DataFrame(fvgs)[["type", "low", "high"]].head(10),
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.caption("None detected")

                sl = pl.get("session_levels", {})
                if sl:
                    st.markdown("**Session Levels**")
                    try:
                        sl_df = pd.DataFrame(sl).T
                        st.dataframe(sl_df, use_container_width=True)
                    except Exception:
                        st.json(sl)

        # ── Human feedback form ───────────────────────────────────────────────
        st.divider()
        st.subheader("⚖️ Your Decision")
        decision = st.radio(
            "What would you like to do?",
            ["Create new strategy", "Use existing alpha", "Merge with existing", "Discard"],
            horizontal=True,
            key="alpha_decision",
        )
        merge_notes = ""
        if "Merge" in decision:
            merge_notes = st.text_area("Merge notes", height=60, key="alpha_merge_notes")

        if st.button("Submit Feedback", type="primary", use_container_width=True):
            wf_id = st.session_state.get("workflow_id", "")
            if not wf_id:
                st.warning("No active workflow. Generate a hypothesis first.")
            else:
                resp = _api("post", "/workflow/feedback", json={
                    "workflow_id": wf_id,
                    "decision": decision.lower().replace(" ", "_"),
                    "merge_notes": merge_notes,
                })
                if "error" in resp:
                    st.error(f"Feedback error: {resp['error']}")
                else:
                    sid = resp.get("strategy_id")
                    if sid:
                        st.session_state["strategy_id"] = sid
                    st.success(f"Feedback submitted. Next step: `{resp.get('next_step', '?')}`")
                    if sid:
                        st.info(f"Strategy ID: `{sid}` — proceed to Backtester & Killer.")

    st.divider()
    st.markdown("**Generated RESEARCH_PLAN preview**")
    if st.session_state.get("workflow_id"):
        st.success("Workflow active — check Plans/ vault folder for RESEARCH_PLAN.md")
    else:
        st.caption("_Preview will appear here after hypothesis generation._")

    if st.button("Proceed to Builder"):
        st.switch_page("pages/3_No_Code_Builder.py")
