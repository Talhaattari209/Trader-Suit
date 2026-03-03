"""Optimization Lab — PPO, Genetic, Ensemble; Run on Colab, overfitting diagnostics, train/val loss, Sharpe gap."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, COLAB_NOTEBOOK_URL
from src.dashboard.components import apply_theme, plotly_layout
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
    st.markdown("Tune RL/DL: PPO, Genetic, Ensemble. Run on Colab for heavy training; overfitting diagnostics below.")
    tab1, tab2, tab3 = st.tabs(["PPO", "Genetic", "Ensemble"])
    with tab1:
        st.slider("Epochs", 10, 500, 100, key="opt_epochs")
        if st.button("Train Model"):
            st.info("Run training on Colab/remote per project rules.")
        if st.button("Run on Colab", type="primary", key="opt_colab_ppo"):
            st.success("Params passed to Colab. Open notebook to run.")
            st.link_button("Open Colab notebook", url=COLAB_NOTEBOOK_URL, type="secondary")
    with tab2:
        st.caption("Genetic algorithm params.")
    with tab3:
        st.caption("Ensemble voting weights.")

    st.divider()
    st.markdown("**Best params** (placeholder)")
    st.dataframe(pd.DataFrame([
        {"Mode": "PPO", "Sharpe": 1.2, "Sortino": 1.5, "Kelly": 0.02},
        {"Mode": "Genetic", "Sharpe": 1.0, "Sortino": 1.2, "Kelly": 0.015},
    ]), use_container_width=True, hide_index=True)
    st.button("Save to Strategy")

    # Overfitting diagnostics
    with st.expander("Overfitting Diagnostics", expanded=True):
        st.markdown("**Model Metrics (in-sample vs out-of-sample)**")
        df_metrics = pd.DataFrame([
            {"Split": "In-Sample", "Sharpe": 1.4, "DD": 10},
            {"Split": "Out-of-Sample", "Sharpe": 0.9, "DD": 16},
        ])
        st.dataframe(df_metrics, use_container_width=True, hide_index=True)
        overfit_gap = 1.4 - 0.9
        if overfit_gap >= 0.5:
            st.error("Overfit detected: Sharpe gap (IS vs OOS) >= 0.5. Consider regularization or more data.")
        st.metric("Overfit Gap (Sharpe diff)", f"{overfit_gap:.2f}", "Target <0.5")
        st.metric("Generalization Ratio", "0.64", "Target >0.8")

    # Charts: Train vs Val Loss; In-Sample vs OOS Sharpe scatter
    st.markdown("**Train vs Validation Loss**")
    epochs = list(range(1, 51))
    train_loss = [2.0 - 0.03 * i + 0.001 * i**2 * 0.01 for i in epochs]
    val_loss = [2.0 - 0.02 * i + 0.002 * i**2 * 0.02 for i in epochs]
    fig_loss = go.Figure()
    fig_loss.add_trace(go.Scatter(x=epochs, y=train_loss, name="Train", line=dict(color="#58a6ff")))
    fig_loss.add_trace(go.Scatter(x=epochs, y=val_loss, name="Validation", line=dict(color="#f59e0b")))
    fig_loss.update_layout(**plotly_layout(height=280), xaxis_title="Epoch", yaxis_title="Loss")
    st.plotly_chart(fig_loss, use_container_width=True)
    st.caption("Diverging train vs validation → overfitting.")

    st.markdown("**In-Sample vs Out-of-Sample Sharpe**")
    is_sharpe = np.array([1.2, 1.4, 1.0, 1.3, 1.1])
    oos_sharpe = np.array([0.8, 0.9, 0.7, 0.85, 0.75])
    fig_scatter = go.Figure(go.Scatter(x=is_sharpe, y=oos_sharpe, mode="markers", marker=dict(size=12, color="#58a6ff")))
    fig_scatter.add_trace(go.Scatter(x=[0, 1.5], y=[0, 1.5], mode="lines", line=dict(dash="dash", color="#8b949e"), name="y=x"))
    fig_scatter.update_layout(**plotly_layout(height=280), xaxis_title="In-Sample Sharpe", yaxis_title="Out-of-Sample Sharpe")
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("Points below diagonal indicate overfit.")

    with st.expander("Code hooks"):
        st.caption("Editable for engineers.")
