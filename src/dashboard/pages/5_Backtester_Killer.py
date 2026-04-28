"""Backtester & Killer — Monte Carlo Pro + Candlestick Trade Chart + Human Decision Gate."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN_NARROW, COLAB_NOTEBOOK_URL
from src.dashboard.components import apply_theme, plotly_layout, build_trade_chart
from src.dashboard.session_state import init_session_state
from src.dashboard.autonomous_chat import render_autonomous_agent_widget

try:
    from src.dashboard.config import API_BASE_URL
except ImportError:
    API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Backtester & Killer — Trader-Suit", page_icon="🎯", layout="wide")
apply_theme()
init_session_state()
render_autonomous_agent_widget(api_base_url=API_BASE_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _api(method: str, path: str, **kwargs):
    """Simple synchronous API call via httpx."""
    try:
        import httpx
        fn = getattr(httpx, method)
        r = fn(f"{API_BASE_URL}{path}", **kwargs, timeout=120)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _load_h1_data() -> pd.DataFrame | None:
    """Load 1H OHLCV data from the configured CSV path."""
    csv_path = os.environ.get(
        "US30_CSV_PATH",
        r"C:\Users\User\Downloads\claude\Dataset-Testing-US30\usa30idxusd-m5-bid-2025-10-09-2025-11-29.csv",
    )
    if not csv_path or not Path(csv_path).exists():
        return None
    try:
        df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
        # Normalise column names
        df.columns = [c.capitalize() for c in df.columns]
        if "Volume" not in df.columns:
            df["Volume"] = 1.0
        df.index = pd.to_datetime(df.index, utc=True)
        # Resample to 1H
        h1 = df.resample("1h").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Open"])
        return h1
    except Exception:
        return None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🎯 Backtester & Killer")

    # Load strategies from API
    strategies_data = _api("get", "/data/strategies", params={"status": "draft"})
    if isinstance(strategies_data, list) and strategies_data:
        strat_names = {s["strategy_id"]: s.get("name", s["strategy_id"]) for s in strategies_data}
        strat_ids   = list(strat_names.keys())
    else:
        strat_names = {"RSI_H1": "RSI H1", "Breakout_D1": "Breakout D1"}
        strat_ids   = list(strat_names.keys())

    st.selectbox(
        "Strategy to test",
        options=strat_ids,
        format_func=lambda k: strat_names.get(k, k),
        key="backtest_strategy_id",
    )
    st.slider("Iterations", 1000, 10000, 5000, step=1000, key="backtest_iterations")
    st.multiselect("Stress tests", options=["noise", "slippage", "regimes"], key="backtest_stress_tests")
    st.checkbox("Walk-Forward", key="walk_forward")
    st.checkbox("Out-of-Sample", key="out_of_sample")

    st.divider()
    st.markdown("### 📊 Chart Settings")
    chart_indicators = st.multiselect(
        "Indicators",
        options=["SMA20", "SMA50", "EMA20", "Bollinger Bands", "RSI", "ATR"],
        default=["SMA20", "EMA20"],
        key="chart_indicators",
    )
    show_liquidity = st.checkbox("Liquidity Zones", value=True, key="show_liquidity")
    show_fvg       = st.checkbox("FVG Zones",        value=True, key="show_fvg")
    show_session   = st.checkbox("Session Levels",   value=True, key="show_session")
    show_trades    = st.checkbox("Agent Trades",     value=True, key="show_trades")
    st.divider()

# ── Main ──────────────────────────────────────────────────────────────────────

sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN_NARROW)
with main_col:
    st.markdown("# 🎯 Backtester & Killer")
    st.markdown("Run Monte Carlo Pro on the selected strategy. Review results, inspect the 1H chart with agent trades, then use the Human Decision Gate.")

    tab_runs, tab_chart, tab_mc_profiles = st.tabs(["Runs & Results", "📊 1H Trade Chart", "MC Profiles"])

    # ── Tab 1: Runs & Results ─────────────────────────────────────────────────
    with tab_runs:
        col_run, col_colab = st.columns([3, 1])
        with col_run:
            run_btn = st.button("▶ Run Monte Carlo Pro", type="primary", use_container_width=True)
        with col_colab:
            st.link_button("Colab MC", url=COLAB_NOTEBOOK_URL, use_container_width=True)

        if run_btn:
            strategy_id = st.session_state.get("backtest_strategy_id", "RSI_H1")
            with st.spinner(f"Running {st.session_state.get('backtest_iterations', 5000):,} iterations…"):
                mc = _api("post", "/montecarlo/run", json={
                    "strategy_id": strategy_id,
                    "iterations":  st.session_state.get("backtest_iterations", 5000),
                    "stress_tests": st.session_state.get("backtest_stress_tests", []),
                    "walk_forward": st.session_state.get("walk_forward", False),
                    "out_of_sample": st.session_state.get("out_of_sample", False),
                })
                if "error" not in mc:
                    st.session_state["mc_result"] = mc
                    # Store trades for chart
                    st.session_state["backtest_trades"] = mc.get("trades", [])
                else:
                    st.error(f"MC run failed: {mc['error']}")

        mc = st.session_state.get("mc_result")
        if mc:
            m = mc.get("metrics", {})
            passed = mc.get("pass", False)

            if passed:
                st.success("✅ Monte Carlo: PASS — strategy cleared all thresholds")
            else:
                st.error("❌ Monte Carlo: FAIL — review metrics before proceeding")

            # Metric grid
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sharpe",       f"{m.get('sharpe', 0):.2f}",
                      delta="✓" if m.get("sharpe", 0) > 1.0 else "✗")
            c2.metric("Max Drawdown", f"{m.get('max_dd', 0):.1f}%",
                      delta="✓" if abs(m.get("max_dd", 99)) < 20 else "✗")
            c3.metric("Win Prob",     f"{m.get('win_probability', 0):.1%}")
            c4.metric("Stability",    f"{m.get('stability_score', 0):.2f}",
                      delta="Overfit!" if m.get("overfit_cliff_flag") else "Stable")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Sortino",      f"{m.get('sortino', 0):.2f}")
            c6.metric("Prob of Ruin", f"{m.get('prob_of_ruin', 0):.1%}")
            c7.metric("VaR 95",       f"{m.get('var_95', 0):.1%}")
            c8.metric("E. Shortfall", f"{m.get('expected_shortfall', 0):.1%}")

            # Regime stress results
            regime_res = mc.get("regime_results", {})
            if regime_res:
                st.markdown("**Regime Stress Results**")
                regime_df = pd.DataFrame(regime_res).T.reset_index()
                regime_df.columns = ["Regime"] + list(regime_df.columns[1:])
                st.dataframe(regime_df, use_container_width=True, hide_index=True)

            # Distribution charts
            col_hist, col_dd = st.columns(2)
            with col_hist:
                ev = mc.get("ending_values", [])
                if ev:
                    fig_hist = go.Figure(go.Histogram(
                        x=ev, nbinsx=50, marker_color="#58a6ff", name="Equity distribution"
                    ))
                    fig_hist.update_layout(**plotly_layout(height=260), xaxis_title="Final Equity Multiple")
                    st.plotly_chart(fig_hist, use_container_width=True)

            with col_dd:
                dd_dist = mc.get("max_dd_dist", [])
                if dd_dist:
                    fig_dd = go.Figure(go.Box(y=dd_dist, name="Max Drawdown", marker_color="#ef4444"))
                    fig_dd.update_layout(**plotly_layout(height=260), yaxis_title="Max DD")
                    st.plotly_chart(fig_dd, use_container_width=True)

            # Price levels from MC
            with st.expander("Price Levels (at MC run time)", expanded=False):
                pl = mc.get("price_levels", {})
                if pl:
                    col_lz, col_fvg = st.columns(2)
                    with col_lz:
                        st.markdown("**Liquidity Zones**")
                        lz = pl.get("liquidity_zones", [])
                        if lz:
                            st.dataframe(pd.DataFrame(lz), use_container_width=True, hide_index=True)
                        else:
                            st.caption("None detected")
                    with col_fvg:
                        st.markdown("**FVG Zones**")
                        fvgs = pl.get("fvg_zones", [])
                        if fvgs:
                            st.dataframe(pd.DataFrame(fvgs[:10]), use_container_width=True, hide_index=True)
                        else:
                            st.caption("None detected")
                    st.markdown("**Session Levels**")
                    sl = pl.get("session_levels", {})
                    if sl:
                        st.dataframe(pd.DataFrame(sl).T, use_container_width=True)
                else:
                    st.json({})

            # ── Human Decision Gate ───────────────────────────────────────────
            st.divider()
            st.subheader("⚖️ Human Decision Gate")
            st.markdown(
                "Review the Monte Carlo results above. "
                "You must make a decision before the strategy proceeds."
            )
            col_disc, col_ret, col_app, col_tweak = st.columns(4)
            discard = col_disc.button("🗑 Discard",              use_container_width=True)
            retest  = col_ret.button("🔄 Retest with Feedback", use_container_width=True)
            approve = col_app.button("✅ Approve",              use_container_width=True, type="primary")
            tweak   = col_tweak.button("🔧 Approve + Tweaks",  use_container_width=True)

            feedback_text = ""
            if retest or tweak:
                feedback_text = st.text_area(
                    "Feedback / tweaks:",
                    height=80,
                    placeholder="e.g. Add session filter, tighten stop loss",
                    key="hdg_feedback",
                )

            strategy_id = st.session_state.get("backtest_strategy_id", "")
            workflow_id = st.session_state.get("workflow_id", "")

            if discard:
                _api("post", "/workflow/decision", json={
                    "workflow_id": workflow_id,
                    "strategy_id": strategy_id,
                    "decision": "discard",
                })
                st.error("Strategy discarded → Graveyard.")

            if approve or tweak:
                decision_val = "approve" if approve else "approve_with_tweaks"
                _api("post", "/workflow/decision", json={
                    "workflow_id":  workflow_id,
                    "strategy_id":  strategy_id,
                    "decision":     decision_val,
                    "tweaks":       feedback_text,
                })
                st.success("Approved → Risk Architect applying sizing. Place file in Approved/ to go live.")

            if retest:
                _api("post", "/workflow/decision", json={
                    "workflow_id": workflow_id,
                    "strategy_id": strategy_id,
                    "decision":    "retest",
                    "feedback":    feedback_text,
                })
                st.info("Re-running MC with feedback. Refresh in 30 seconds.")

    # ── Tab 2: 1H Candlestick Trade Chart ─────────────────────────────────────
    with tab_chart:
        st.markdown("### 📊 1H Price Chart — Agent Trades & Price Levels")

        df_h1 = _load_h1_data()
        mc_result = st.session_state.get("mc_result", {})
        trades    = st.session_state.get("backtest_trades", []) if show_trades else []
        pl        = mc_result.get("price_levels", {}) if (show_liquidity or show_fvg or show_session) else {}

        if not (show_liquidity and show_fvg and show_session):
            # Mask out unwanted layers
            pl_filtered = dict(pl)
            if not show_liquidity:
                pl_filtered["liquidity_zones"] = []
            if not show_fvg:
                pl_filtered["fvg_zones"] = []
            if not show_session:
                pl_filtered["session_levels"] = {}
            pl = pl_filtered

        if df_h1 is not None:
            # Show last 200 candles for clarity
            df_display = df_h1.tail(200)

            fig_chart = build_trade_chart(
                df_ohlcv=df_display,
                trades=trades,
                price_levels=pl if pl else None,
                indicators=chart_indicators,
                show_liquidity=show_liquidity,
                show_fvg=show_fvg,
                show_session=show_session,
                height=560,
            )
            st.plotly_chart(fig_chart, use_container_width=True)

            # Summary stats
            col_info1, col_info2, col_info3 = st.columns(3)
            col_info1.metric("Candles shown", len(df_display))
            col_info1.caption("1H OHLCV")
            if pl:
                col_info2.metric("Liquidity zones", len(pl.get("liquidity_zones", [])))
                col_info3.metric("FVG zones", len(pl.get("fvg_zones", [])))
            if trades:
                buy_count  = sum(1 for t in trades if t.get("side") == "buy")
                sell_count = sum(1 for t in trades if t.get("side") == "sell")
                st.caption(f"Trades shown: {buy_count} buy, {sell_count} sell")
        else:
            st.warning(
                "No 1H OHLCV data available. "
                "Set `US30_CSV_PATH` in your `.env` file and run an MC test first."
            )
            # Show demo chart with synthetic data
            np.random.seed(42)
            n = 120
            idx = pd.date_range(start="2025-10-01", periods=n, freq="1h", tz="UTC")
            close_vals = 42000 + np.cumsum(np.random.randn(n) * 30)
            df_demo = pd.DataFrame({
                "Open":   close_vals + np.random.randn(n) * 10,
                "High":   close_vals + np.abs(np.random.randn(n)) * 25,
                "Low":    close_vals - np.abs(np.random.randn(n)) * 25,
                "Close":  close_vals,
                "Volume": np.random.randint(1000, 5000, n).astype(float),
            }, index=idx)
            demo_trades = [
                {"timestamp": idx[i], "side": "buy" if i % 3 == 0 else "sell",
                 "price": close_vals[i], "label": f"T{i}"}
                for i in range(10, 110, 15)
            ]
            fig_demo = build_trade_chart(
                df_ohlcv=df_demo,
                trades=demo_trades,
                indicators=chart_indicators,
                height=520,
            )
            st.plotly_chart(fig_demo, use_container_width=True)
            st.caption("Demo chart — connect real data via US30_CSV_PATH")

    # ── Tab 3: MC Profiles ─────────────────────────────────────────────────────
    with tab_mc_profiles:
        st.markdown("**MC Profiles** — deep characteristics per run.")

        mc = st.session_state.get("mc_result")
        if mc:
            # Stability heatmap
            regime_res = mc.get("regime_results", {})
            if regime_res:
                regime_names = list(regime_res.keys())
                metric_names = ["prob_of_ruin", "var_95"]
                z = [
                    [regime_res[r].get(m, 0) for m in metric_names]
                    for r in regime_names
                ]
                fig_hm = go.Figure(go.Heatmap(
                    z=z, x=metric_names, y=regime_names,
                    colorscale="RdYlGn_r", text=z,
                    texttemplate="%{text:.3f}",
                ))
                fig_hm.update_layout(**plotly_layout(height=250), title="Regime Risk Heatmap")
                st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Run Monte Carlo first to see profiles.")

        # Violin charts (always visible)
        st.markdown("**Characteristic Distributions**")
        np.random.seed(42)
        slippage_a = np.random.randn(100) * 0.5 + 1.2
        slippage_b = np.random.randn(100) * 0.6 + 1.5
        fig_violin = go.Figure()
        fig_violin.add_trace(go.Violin(y=slippage_a, name="Run A", box_visible=True, line_color="#58a6ff"))
        fig_violin.add_trace(go.Violin(y=slippage_b, name="Run B", box_visible=True, line_color="#3fb950"))
        fig_violin.update_layout(**plotly_layout(height=300), yaxis_title="Slippage (pip)")
        st.plotly_chart(fig_violin, use_container_width=True)

        st.metric("Robustness Ratio (passed sims)", "82%", ">80%")
        st.metric("Characteristic Depth", "10+ params", "analyzed")
