"""No-Code Strategy Builder — Wizard + Specs-Driven mode with Agent-managed Code | Specs columns."""

from __future__ import annotations

import streamlit as st
from src.dashboard.config import (
    LAYOUT_SIDEBAR_MAIN_WIDE,
    BUILDER_STEP_NAMES,
    COLAB_NOTEBOOK_URL,
    COLAB_DRIVE_STRATEGY_PATH,
)
from src.dashboard.components import apply_theme, plotly_layout
from src.dashboard.session_state import init_session_state
from src.dashboard.builder_agent import code_to_specs, specs_to_code
import plotly.graph_objects as go


def _render_wizard() -> None:
    step = st.session_state.get("wizard_step", 1)
    step_names = BUILDER_STEP_NAMES
    tabs = st.tabs([step_names[i] if i < len(step_names) else f"Step {i+1}" for i in range(8)])
    with tabs[step - 1]:
        st.selectbox("Model", options=["LSTM", "CNN", "Combo"], key=f"model_step{step}")
        st.slider("Layers", 1, 5, 2, key=f"layers_step{step}")
        st.slider("Dropout", 0.0, 0.5, 0.2, key=f"dropout_step{step}")
        if st.button("Next"):
            st.rerun()
    st.divider()
    if st.button("Generate Code"):
        st.info("Strategist will write draft to src/models/drafts/. Use Specs-Driven mode for Code ↔ Specs sync.")
    with st.expander("Advanced Code View"):
        st.code("# Editable Python snippet", language="python")


def _render_specs_driven() -> None:
    blocks: list[dict] = st.session_state.builder_blocks
    step_names = BUILDER_STEP_NAMES
    st.markdown("### Specs input (optional)")
    st.session_state.builder_specs_input = st.text_area(
        "e.g. Build workflow: Entry on RSI<30, exit ATR*2",
        value=st.session_state.get("builder_specs_input", ""),
        height=80,
        key="global_specs_ta",
    )
    col_gen, _ = st.columns([1, 3])
    with col_gen:
        if st.button("Generate Code/Description from specs above"):
            spec_text = st.session_state.get("builder_specs_input", "")
            if spec_text.strip():
                generated = specs_to_code(spec_text, [])
                if not blocks:
                    blocks.append({"code": generated, "specs": spec_text, "agent_comment": "Generated from global specs."})
                else:
                    blocks[0]["code"] = generated
                    blocks[0]["specs"] = spec_text
                st.session_state.builder_blocks = blocks
                st.success("Code/description updated from specs.")
            else:
                st.warning("Enter specs first.")
            st.rerun()
    st.divider()
    st.markdown("### Agent-managed blocks (Code | Specs)")
    st.caption("Edit code → click **Submit** on a block to re-evaluate and update specs. Edit specs → click **Apply Specs** to update code.")
    if not blocks:
        blocks = [{"code": "", "specs": "", "agent_comment": ""}]
        st.session_state.builder_blocks = blocks

    # Workflow metrics
    n_steps = len(blocks)
    n_params = sum(1 for b in blocks if b.get("code") and "=" in (b.get("code") or ""))  # rough param count
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Workflow Efficiency (steps)", n_steps, "OK" if n_steps < 10 else "Consider <10")
    with m2:
        st.metric("Indicator Complexity (params)", min(n_params, 5), "OK if <5")

    # Flowchart: workflow viz (nodes = blocks, edges = sequence)
    step_names = BUILDER_STEP_NAMES
    labels = [step_names[i] if i < len(step_names) else f"Block {i+1}" for i in range(len(blocks))]
    if len(labels) >= 1:
        try:
            import networkx as nx
            G = nx.DiGraph()
            for i, lb in enumerate(labels):
                G.add_node(i, label=lb)
            for i in range(len(labels) - 1):
                G.add_edge(i, i + 1)
            pos = nx.spring_layout(G, k=1.5, iterations=50)
            node_x = [pos[i][0] for i in range(len(labels))]
            node_y = [pos[i][1] for i in range(len(labels))]
            edge_x, edge_y = [], []
            for e in G.edges():
                x0, y0 = pos[e[0]]
                x1, y1 = pos[e[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1.5, color="#8b949e"), hoverinfo="none"))
            fig_flow.add_trace(go.Scatter(x=node_x, y=node_y, mode="text+markers", text=labels, textposition="top center", marker=dict(size=20, color="#58a6ff"), textfont=dict(size=10)))
            fig_flow.update_layout(showlegend=False, **plotly_layout(height=220), xaxis=dict(showticklabels=False, zeroline=False), yaxis=dict(showticklabels=False, zeroline=False), title="Workflow")
            with st.expander("Flowchart: Workflow Viz", expanded=False):
                st.plotly_chart(fig_flow, use_container_width=True)
        except ImportError:
            with st.expander("Flowchart: Workflow Viz", expanded=False):
                st.caption("Install networkx for flowchart: pip install networkx")
                st.markdown(" → ".join(labels))

    for i in range(len(blocks)):
        step_label = step_names[i] if i < len(step_names) else f"Block {i+1}"
        with st.expander(f"**{step_label}**", expanded=(i == len(blocks) - 1)):
            code_col, specs_col = st.columns(2)
            with code_col:
                st.markdown("**Code**")
                blocks[i]["code"] = st.text_area("Code", value=blocks[i].get("code", ""), height=180, key=f"code_{i}", label_visibility="collapsed")
                if st.button("Submit", key=f"submit_code_{i}"):
                    prev_specs = [b.get("specs", "") for b in blocks[:i]]
                    specs_text, agent_comment = code_to_specs(blocks[i]["code"], prev_specs, step_name=step_label)
                    blocks[i]["specs"] = specs_text
                    blocks[i]["agent_comment"] = agent_comment
                    st.session_state.builder_blocks = blocks
                    st.success("Re-evaluated. Specs updated.")
                    st.rerun()
            with specs_col:
                st.markdown("**Specs**")
                blocks[i]["specs"] = st.text_area("Specs", value=blocks[i].get("specs", ""), height=180, key=f"specs_{i}", label_visibility="collapsed")
                if st.button("Apply Specs → Code", key=f"apply_specs_{i}"):
                    prev_code = [b.get("code", "") for b in blocks[:i]]
                    new_code = specs_to_code(blocks[i].get("specs", ""), prev_code, step_name=step_label)
                    blocks[i]["code"] = new_code
                    blocks[i]["agent_comment"] = "Code updated from specs."
                    st.session_state.builder_blocks = blocks
                    st.success("Code updated from specs.")
                    st.rerun()
            if blocks[i].get("agent_comment"):
                st.info(f"**Agent:** {blocks[i]['agent_comment']}")
    if st.button("+ Add block"):
        blocks.append({"code": "", "specs": "", "agent_comment": ""})
        st.session_state.builder_blocks = blocks
        st.rerun()
    st.divider()
    st.markdown("### Export & run on Colab")
    full_code = "\n\n".join(b.get("code", "") for b in blocks if b.get("code"))
    if full_code:
        with st.expander("Generated workflow code"):
            st.code(full_code, language="python")
        st.markdown(f"**Trigger Colab:** Open the notebook, paste or sync this code (e.g. to `{COLAB_DRIVE_STRATEGY_PATH}`), then run.")
        st.link_button("Open Colab notebook", url=COLAB_NOTEBOOK_URL, type="secondary")
    else:
        st.info("Add at least one block with code, then use **Run on Colab** in the sidebar or link below.")
        st.link_button("Open Colab notebook", url=COLAB_NOTEBOOK_URL, type="secondary")


st.set_page_config(page_title="No-Code Builder — Trader-Suit", page_icon="🔧", layout="wide")
apply_theme()
init_session_state()

# Ensure builder_blocks in session state (list of {code, specs, agent_comment})
if "builder_blocks" not in st.session_state:
    st.session_state.builder_blocks = []
if "builder_specs_input" not in st.session_state:
    st.session_state.builder_specs_input = ""
if "builder_colab_triggered" not in st.session_state:
    st.session_state.builder_colab_triggered = False

with st.sidebar:
    st.markdown("## 🔧 No-Code Builder")
    mode = st.radio("Mode", ["Wizard", "Specs-Driven"], horizontal=True, key="builder_mode")
    st.divider()
    st.caption("**Agent:** Manages Code ↔ Specs. Submit a block to re-evaluate; edit specs to update code.")
    if mode == "Specs-Driven":
        st.markdown("**Workflow metrics**")
        blocks = st.session_state.builder_blocks
        st.metric("Blocks", len(blocks), delta=None)
        st.caption("Steps <10 recommended")
        st.divider()
        if st.button("▶ Run on Colab", type="primary", use_container_width=True, key="colab_btn"):
            st.session_state.builder_colab_triggered = True
            st.rerun()
        if st.session_state.get("builder_colab_triggered"):
            st.success("Open Colab to run model code (see link in main).")
    else:
        step = st.slider("Step", 1, 8, 1, key="wizard_step")
        st.progress(step / 8)
        st.caption("Agent suggestions appear below after each step.")

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_WIDE)

with main_col:
    st.markdown("# 🔧 No-Code Strategy Builder")
    st.markdown("Step-by-step wizard or **Specs-Driven** mode: code and specs stay in sync via the agent.")

    if mode == "Wizard":
        _render_wizard()
    else:
        _render_specs_driven()
