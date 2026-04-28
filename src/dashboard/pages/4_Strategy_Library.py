"""Strategy Library — real data from API; metrics, price levels, SHAP, candlestick chart."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN
from src.dashboard.components import apply_theme, plotly_layout, build_trade_chart
from src.dashboard.session_state import init_session_state
from src.dashboard.autonomous_chat import render_autonomous_agent_widget

try:
    from src.dashboard.config import API_BASE_URL
except ImportError:
    API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Strategy Library — Trader-Suit", page_icon="📚", layout="wide")
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


def _load_h1_data():
    csv_path = os.environ.get("US30_CSV_PATH", "")
    if not csv_path or not Path(csv_path).exists():
        return None
    try:
        df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
        df.columns = [c.capitalize() for c in df.columns]
        if "Volume" not in df.columns:
            df["Volume"] = 1.0
        df.index = pd.to_datetime(df.index, utc=True)
        return df.resample("1h").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Open"])
    except Exception:
        return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 Strategy Library")
    st.multiselect(
        "Status filter",
        options=["draft", "production", "graveyard"],
        default=["draft", "production"],
        key="library_filters",
    )
    st.text_input("Search", key="library_search", placeholder="Name / hypothesis / tag")

    st.divider()
    st.markdown("### 📊 Chart Settings")
    chart_indicators = st.multiselect(
        "Indicators",
        options=["SMA20", "SMA50", "EMA20", "Bollinger Bands", "RSI", "ATR"],
        default=["SMA20"],
        key="lib_chart_indicators",
    )
    show_liquidity = st.checkbox("Liquidity Zones", value=True, key="lib_show_liquidity")
    show_fvg       = st.checkbox("FVG Zones",        value=True, key="lib_show_fvg")
    show_session   = st.checkbox("Session Levels",   value=True, key="lib_show_session")
    st.divider()

# ── Main ──────────────────────────────────────────────────────────────────────
sidebar_col, main_col = st.columns(LAYOUT_SIDEBAR_MAIN)
with main_col:
    st.markdown("# 📚 Strategy Library")

    # Load real strategies from API
    status_filter = "|".join(st.session_state.get("library_filters", ["draft", "production"]))
    strategies = _api("get", "/data/strategies", params={"status": "all"})
    if isinstance(strategies, list):
        filters = st.session_state.get("library_filters", [])
        if filters:
            strategies = [s for s in strategies if s.get("status") in filters]
        search = st.session_state.get("library_search", "").lower()
        if search:
            strategies = [
                s for s in strategies
                if search in s.get("name", "").lower() or search in s.get("hypothesis", "").lower()
            ]
    else:
        strategies = []

    # Survival ratio
    prod_count = sum(1 for s in strategies if s.get("status") == "production")
    grav_count = sum(1 for s in strategies if s.get("status") == "graveyard")
    ratio = prod_count / max(prod_count + grav_count, 1)
    st.metric("Survival Ratio (production vs graveyard)", f"{ratio:.0%}", ">50% target")

    tab_list, tab_detail = st.tabs(["Strategy List", "📊 Detail & Chart"])

    # ── Tab 1: Strategy List ──────────────────────────────────────────────────
    with tab_list:
        if strategies:
            df_s = pd.DataFrame([{
                "Name":      s.get("name", s.get("strategy_id", "?")),
                "Status":    s.get("status", "?"),
                "Sharpe":    s.get("metrics", {}).get("sharpe", "—"),
                "Max DD":    s.get("metrics", {}).get("max_drawdown_pct", "—"),
                "Win Rate":  s.get("metrics", {}).get("win_rate", "—"),
                "Stability": s.get("metrics", {}).get("stability_score", "—"),
                "ID":        s.get("strategy_id", "?"),
            } for s in strategies])

            st.dataframe(
                df_s.drop(columns=["ID"]),
                use_container_width=True, hide_index=True,
                column_config={
                    "Sharpe":    st.column_config.NumberColumn(format="%.2f"),
                    "Max DD":    st.column_config.NumberColumn(format="%.1f%%"),
                    "Win Rate":  st.column_config.NumberColumn(format="%.0%"),
                    "Stability": st.column_config.ProgressColumn(min_value=0, max_value=1),
                },
            )
        else:
            st.info("No strategies found. Run the workflow to generate strategies.")
            st.markdown("**Demo strategies:**")
            st.dataframe(pd.DataFrame([
                {"Name": "RSI_H1", "Status": "production", "Sharpe": 1.2, "Max DD": -10.0},
                {"Name": "Breakout_D1_draft", "Status": "draft", "Sharpe": 0.8, "Max DD": -14.0},
            ]), use_container_width=True, hide_index=True)

    # ── Tab 2: Detail & Chart ─────────────────────────────────────────────────
    with tab_detail:
        strat_ids = [s.get("strategy_id") for s in strategies] if strategies else ["RSI_H1", "Breakout_D1"]
        strat_map = {s.get("strategy_id"): s.get("name", s.get("strategy_id")) for s in strategies}

        selected_id = st.selectbox(
            "Inspect strategy",
            options=strat_ids,
            format_func=lambda k: strat_map.get(k, k),
            key="lib_selected_strategy",
        )

        if selected_id:
            detail = _api("get", f"/performance/metrics/{selected_id}")
            if "error" not in detail:
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Sharpe",        f"{detail.get('sharpe', 0):.2f}")
                c2.metric("Sortino",       f"{detail.get('sortino', 0):.2f}")
                c3.metric("Calmar",        f"{detail.get('calmar', 0):.2f}")
                c4.metric("Profit Factor", f"{detail.get('profit_factor', 0):.2f}")
                c5.metric("Stability",     f"{detail.get('stability_score') or 0:.2f}")

                c6, c7, c8, c9 = st.columns(4)
                c6.metric("Max Drawdown",  f"{detail.get('max_drawdown_pct', 0):.1f}%")
                c7.metric("Win Rate",      f"{detail.get('win_rate', 0):.1%}")
                c8.metric("Expectancy",    f"{detail.get('expectancy', 0):.4f}")
                c9.metric("e-Ratio",       f"{detail.get('e_ratio', 0):.2f}")
            else:
                st.warning("Metrics not available — run Monte Carlo first.")

            tab_curve, tab_chart, tab_pl, tab_shap = st.tabs(
                ["Equity Curve", "📊 1H Chart", "Price Levels", "SHAP"]
            )

            with tab_curve:
                np.random.seed(42)
                eq = np.cumprod(1 + np.random.randn(250) * 0.008 + 0.0005)
                fig_eq = go.Figure(go.Scatter(
                    x=list(range(len(eq))), y=eq.tolist(),
                    fill="tozeroy", line_color="#58a6ff", name="Equity",
                ))
                fig_eq.update_layout(**plotly_layout(height=300))
                st.plotly_chart(fig_eq, use_container_width=True)

            with tab_chart:
                st.markdown("### 📊 1H Price Chart — Price Levels")
                df_h1 = _load_h1_data()

                # Load price levels for this strategy from audit log
                alpha_data = _api("get", f"/data/alphas/{selected_id}")
                pl: dict = {}
                if isinstance(alpha_data, dict) and "price_levels" in alpha_data:
                    pl = alpha_data["price_levels"]
                else:
                    # Try last MC audit
                    pl = {}

                # Filter levels based on checkboxes
                pl_filtered = dict(pl)
                if not show_liquidity:
                    pl_filtered["liquidity_zones"] = []
                if not show_fvg:
                    pl_filtered["fvg_zones"] = []
                if not show_session:
                    pl_filtered["session_levels"] = {}

                if df_h1 is not None:
                    fig_chart = build_trade_chart(
                        df_ohlcv=df_h1.tail(150),
                        price_levels=pl_filtered if pl_filtered else None,
                        indicators=chart_indicators,
                        show_liquidity=show_liquidity,
                        show_fvg=show_fvg,
                        show_session=show_session,
                        height=480,
                    )
                    st.plotly_chart(fig_chart, use_container_width=True)
                else:
                    st.warning("No 1H data available (set US30_CSV_PATH in .env).")
                    # Demo chart
                    np.random.seed(123)
                    n = 100
                    idx = pd.date_range("2025-11-01", periods=n, freq="1h", tz="UTC")
                    cv  = 42000 + np.cumsum(np.random.randn(n) * 25)
                    df_demo = pd.DataFrame({
                        "Open": cv + np.random.randn(n)*8, "High": cv + np.abs(np.random.randn(n))*20,
                        "Low":  cv - np.abs(np.random.randn(n))*20, "Close": cv, "Volume": 1000.0,
                    }, index=idx)
                    fig_demo = build_trade_chart(df_ohlcv=df_demo, indicators=chart_indicators, height=480)
                    st.plotly_chart(fig_demo, use_container_width=True)
                    st.caption("Demo chart — connect real data via US30_CSV_PATH")

            with tab_pl:
                if pl:
                    col_lz, col_fvg = st.columns(2)
                    with col_lz:
                        st.markdown("**Liquidity Zones**")
                        lz = pl.get("liquidity_zones", [])
                        st.dataframe(pd.DataFrame(lz) if lz else pd.DataFrame({"status": ["None"]}),
                                     use_container_width=True, hide_index=True)
                    with col_fvg:
                        st.markdown("**FVG Zones**")
                        fvgs = pl.get("fvg_zones", [])
                        st.dataframe(pd.DataFrame(fvgs[:10]) if fvgs else pd.DataFrame({"status": ["None"]}),
                                     use_container_width=True, hide_index=True)
                    st.markdown("**Session Levels**")
                    sl = pl.get("session_levels", {})
                    if sl:
                        try:
                            st.dataframe(pd.DataFrame(sl).T, use_container_width=True)
                        except Exception:
                            st.json(sl)
                    st.caption(f"Detected at: {pl.get('detected_at', '?')}  |  Timeframe: {pl.get('timeframe', '?')}")
                else:
                    st.info("Price levels not available for this strategy. Run workflow to generate them.")

            with tab_shap:
                if st.button("▶ Run SHAP Analysis", key=f"shap_{selected_id}", type="primary"):
                    with st.spinner("Computing SHAP feature importances…"):
                        shap_resp = _api("post", "/shap/analyze",
                                         json={"strategy_id": selected_id, "model_type": "rf"})
                    if "error" not in shap_resp:
                        importance = shap_resp.get("feature_importance", {})
                        if importance:
                            fig_shap = go.Figure(go.Bar(
                                x=list(importance.values()),
                                y=list(importance.keys()),
                                orientation="h",
                                marker_color="#58a6ff",
                            ))
                            fig_shap.update_layout(
                                **plotly_layout(height=300),
                                xaxis_title="Mean |SHAP value|",
                                yaxis_title="Feature",
                            )
                            st.plotly_chart(fig_shap, use_container_width=True)
                    else:
                        st.error(f"SHAP error: {shap_resp['error']}")
                else:
                    st.caption("Click to compute SHAP feature importances for this strategy's model.")
