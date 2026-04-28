"""
connectors_tester/main.py
==========================
Streamlit entry point for the Connectors Tester.

Run:
  cd connectors_tester
  uv run streamlit run main.py
  # or:  streamlit run main.py

LAYOUT:
  Sidebar  : Broker selector (Alpaca-1 / Alpaca-2 / MT5) + connection status
  Main     : Six tabs:
               1. Account Summary
               2. Open Positions  (with SL/TP controls)
               3. Active Orders   (pending + open)
               4. Trade History
               5. Order Placement (manual form — all order types)
               6. Price Levels    (reuses price_level_detector from main project)
  Widget   : Floating autonomous AI agent (bottom-right, orange, draggable)

The agent receives the current broker from session state so every chat message
is scoped to the selected broker automatically.
"""

import sys
import os
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────────────
# We need access to:
#   1. connectors_tester/src/   (local modules)
#   2. parent project root       (src.tools.llm_client, src.autonomous_agent.database)
_TESTER_ROOT = Path(__file__).resolve().parent      # connectors_tester/
_MAIN_ROOT   = _TESTER_ROOT.parent                  # project root (claude/)
sys.path.insert(0, str(_TESTER_ROOT))               # so "src.*" resolves in tester
sys.path.insert(0, str(_MAIN_ROOT))                 # so main project's src.* is reachable
os.chdir(str(_TESTER_ROOT))                         # CWD = tester root for DataStore/ paths

from dotenv import load_dotenv
load_dotenv(_TESTER_ROOT / ".env", override=False)  # load tester-specific .env

import streamlit as st
import pandas as pd

# ── Page config (must be FIRST Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Connectors Tester — Trader-Suit",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.dashboard.components.autonomous_chat_tester import render_connectors_agent_widget
from src.tools.order_types_handler import (
    get_order_types,
    get_order_type_labels,
    required_fields,
    optional_fields,
    validate_order,
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────────────────────

if "broker" not in st.session_state:
    st.session_state["broker"] = "alpaca_1"   # default: primary Alpaca paper account

# ─────────────────────────────────────────────────────────────────────────────
# Global dark theme injection
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""<style>
body, .stApp { background-color: #0d1117 !important; color: #e6edf3 !important; }
.stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { color: #8b949e; }
.stTabs [aria-selected="true"] { color: #f0883e !important; border-bottom: 2px solid #f0883e; }
div[data-testid="stMetricValue"] { color: #58a6ff; }
.stDataFrame { border: 1px solid #30363d; }
hr { border-color: #30363d; }
.stSelectbox label, .stNumberInput label, .stTextInput label { color: #8b949e; }
.stButton > button {
  background: #1c2128; border: 1px solid #30363d; color: #e6edf3;
  border-radius: 6px; transition: border-color .15s;
}
.stButton > button:hover { border-color: #f0883e; color: #f0883e; }
.stSuccess { background: rgba(63,185,80,.12) !important; }
.stError   { background: rgba(248,81,73,.12) !important; }
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _call_alpaca(fn_name: str, **kwargs):
    """
    Safely call an alpaca_tester function by name.

    Returns the result, or an error dict on failure.
    """
    try:
        import src.connectors.alpaca_tester as at
        acc_num = 2 if st.session_state["broker"] == "alpaca_2" else 1
        fn      = getattr(at, fn_name)
        return fn(account=acc_num, **kwargs)
    except Exception as exc:
        return {"error": str(exc)}


def _call_mt5(fn_name: str, **kwargs):
    """Safely call an mt5_tester function by name."""
    try:
        import src.connectors.mt5_tester as mt
        fn = getattr(mt, fn_name)
        return fn(**kwargs)
    except Exception as exc:
        return {"error": str(exc)}


def _broker_call(fn_alpaca: str, fn_mt5: str, alpaca_kwargs: dict = None, mt5_kwargs: dict = None):
    """
    Dispatch to the correct connector based on session broker.

    Returns the connector's result (dict or list).
    """
    broker = st.session_state["broker"]
    if broker in ("alpaca_1", "alpaca_2"):
        return _call_alpaca(fn_alpaca, **(alpaca_kwargs or {}))
    else:
        return _call_mt5(fn_mt5, **(mt5_kwargs or {}))


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar: broker selector + connection status
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔌 Connectors Tester")
    st.markdown("**Broker Testing & AI Agent**")
    st.divider()

    broker_choice = st.selectbox(
        "Select Broker",
        options=["alpaca_1", "alpaca_2", "mt5"],
        format_func=lambda b: {"alpaca_1": "Alpaca Account 1 (Paper)", "alpaca_2": "Alpaca Account 2 (Paper)", "mt5": "MetaTrader 5"}[b],
        index=["alpaca_1", "alpaca_2", "mt5"].index(st.session_state["broker"]),
        key="broker_select",
    )
    st.session_state["broker"] = broker_choice   # persist broker choice

    st.divider()

    # ── Connection test ────────────────────────────────────────────────────────
    if st.button("🔍 Test Connection", use_container_width=True):
        broker = st.session_state["broker"]
        with st.spinner("Connecting…"):
            if broker in ("alpaca_1", "alpaca_2"):
                result = _call_alpaca("get_account")
            else:
                result = _call_mt5("connect")

            if "error" in result:
                st.error(f"Connection failed: {result['error']}")
            else:
                st.success("Connected ✓")
                if broker in ("alpaca_1", "alpaca_2"):
                    st.caption(f"Equity: ${result.get('equity', 0):,.2f}")
                else:
                    st.caption(f"Balance: {result.get('balance', 0):,.2f} | Build: {result.get('build', '?')}")

    st.divider()

    # ── MCP status ─────────────────────────────────────────────────────────────
    mcp_url = os.environ.get("ALPACA_MCP_URL", "").strip()
    if mcp_url:
        st.caption(f"🟢 Alpaca MCP: `{mcp_url}`")
    else:
        st.caption("🟡 Alpaca MCP: not configured (set ALPACA_MCP_URL in .env)")

    if sys.platform == "win32":
        st.caption("🟢 MT5: available (Windows)")
    else:
        st.caption("🔴 MT5: Windows-only (unavailable on this OS)")

    st.divider()
    st.caption("Run with:\n```\nstreamlit run main.py\n```")


# ─────────────────────────────────────────────────────────────────────────────
# Main content — six tabs
# ─────────────────────────────────────────────────────────────────────────────

broker  = st.session_state["broker"]
broker_label = {"alpaca_1": "Alpaca-1", "alpaca_2": "Alpaca-2", "mt5": "MT5"}[broker]

st.markdown(f"# 🔌 Connectors Tester — **{broker_label}**")
st.divider()

tab_account, tab_positions, tab_orders, tab_history, tab_order_form, tab_prices = st.tabs([
    "📊 Account", "📋 Positions", "⏳ Orders", "📜 Trade History",
    "🚀 Place Order", "🎯 Price Levels",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Account Summary
# ══════════════════════════════════════════════════════════════════════════════
with tab_account:
    st.subheader(f"Account Summary — {broker_label}")

    if st.button("🔄 Refresh Account", key="refresh_account"):
        st.session_state["account_data"] = _broker_call("get_account", "get_account")

    acc = st.session_state.get("account_data", {})
    if not acc:
        acc = _broker_call("get_account", "get_account")
        st.session_state["account_data"] = acc

    if "error" in acc:
        st.error(f"Cannot fetch account: {acc['error']}")
    else:
        if broker in ("alpaca_1", "alpaca_2"):
            # Show Alpaca-specific fields
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Equity",        f"${acc.get('equity', 0):,.2f}")
            c2.metric("Cash",          f"${acc.get('cash', 0):,.2f}")
            c3.metric("Buying Power",  f"${acc.get('buying_power', 0):,.2f}")
            c4.metric("Unrealised P&L",f"${acc.get('unrealized_pl', 0):+,.2f}")
            st.caption(f"Account: {acc.get('account_number', 'N/A')} | Status: {acc.get('status', '?')} | PDT: {acc.get('pattern_day_trader', False)}")
        else:
            # MT5 fields
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Balance",      f"{acc.get('balance', 0):,.2f} {acc.get('currency','')}")
            c2.metric("Equity",       f"{acc.get('equity', 0):,.2f}")
            c3.metric("Profit",       f"{acc.get('profit', 0):+,.2f}")
            c4.metric("Margin Level", f"{acc.get('margin_level', 0):.1f}%")
            st.caption(f"Login: {acc.get('login','?')} | Server: {acc.get('server','?')} | Leverage: 1:{acc.get('leverage',1)}")

    # ── Portfolio history (Alpaca only) ────────────────────────────────────────
    if broker in ("alpaca_1", "alpaca_2"):
        st.divider()
        st.markdown("#### P&L History (30 days)")
        hist = _call_alpaca("get_portfolio_history", days=30)
        if isinstance(hist, list) and hist and "error" not in hist[0]:
            df_hist = pd.DataFrame(hist)
            if "timestamp" in df_hist.columns:
                df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"], errors="coerce")
            if "pnl_pct" in df_hist.columns:
                import plotly.graph_objects as go
                fig = go.Figure(go.Scatter(
                    x=df_hist.get("timestamp", df_hist.index),
                    y=df_hist["pnl_pct"],
                    mode="lines", line=dict(color="#f0883e", width=2),
                ))
                fig.update_layout(
                    paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                    font_color="#e6edf3", height=260,
                    margin=dict(t=10, b=20, l=40, r=10),
                    xaxis_title="", yaxis_title="P&L %",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("P&L history unavailable — check Alpaca credentials.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Open Positions with SL/TP controls
# ══════════════════════════════════════════════════════════════════════════════
with tab_positions:
    st.subheader(f"Open Positions — {broker_label}")

    col_refresh, col_close_all = st.columns([1, 1])
    with col_refresh:
        if st.button("🔄 Refresh Positions", key="refresh_pos"):
            st.session_state["positions_data"] = _broker_call("get_positions", "get_positions")

    positions = st.session_state.get("positions_data", [])
    if not positions:
        positions = _broker_call("get_positions", "get_positions")
        st.session_state["positions_data"] = positions

    if isinstance(positions, dict) and "error" in positions:
        st.error(f"Cannot fetch positions: {positions['error']}")
    elif not positions or (isinstance(positions, list) and "error" in (positions[0] if positions else {})):
        st.info("No open positions.")
    else:
        # Render positions as a table
        df_pos = pd.DataFrame(positions)
        st.dataframe(df_pos, use_container_width=True, hide_index=True)

        # ── SL/TP controls per position ────────────────────────────────────────
        st.divider()
        st.markdown("#### Modify SL / TP or Close Position")

        for i, pos in enumerate(positions[:10]):   # max 10 for UI clarity
            if broker in ("alpaca_1", "alpaca_2"):
                symbol = pos.get("symbol", "?")
                qty    = pos.get("qty", 0)
                side   = pos.get("side", "?")
                pl     = pos.get("unrealized_pl", 0)
            else:
                symbol = pos.get("symbol", "?")
                qty    = pos.get("volume", 0)
                side   = pos.get("type", "?")
                pl     = pos.get("profit", 0)
                ticket = pos.get("ticket", 0)

            with st.expander(f"{symbol}  {side.upper()}  {qty}  |  P&L {pl:+.2f}", expanded=False):
                if broker == "mt5":
                    c_sl, c_tp, c_btn = st.columns([1, 1, 1])
                    with c_sl:
                        new_sl = st.number_input("New SL", value=float(pos.get("sl") or 0), key=f"sl_{i}_{ticket}")
                    with c_tp:
                        new_tp = st.number_input("New TP", value=float(pos.get("tp") or 0), key=f"tp_{i}_{ticket}")
                    with c_btn:
                        st.write("")   # vertical align
                        if st.button("Update SL/TP", key=f"update_sltp_{i}"):
                            result = _call_mt5("modify_sl_tp", ticket=ticket, sl=new_sl or None, tp=new_tp or None)
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                st.success(f"SL/TP updated on ticket {ticket}")

                    if st.button(f"Close {symbol}", key=f"close_pos_{i}"):
                        result = _call_mt5("close_position", ticket=ticket)
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.success(f"Position {ticket} closed.")
                            st.session_state.pop("positions_data", None)   # invalidate cache
                            st.rerun()

                else:
                    # Alpaca: close_position or modify_stop_loss (on bracket orders)
                    c_qty, c_btn = st.columns([2, 1])
                    with c_qty:
                        close_qty = st.number_input("Close qty (blank = all)", value=0.0, key=f"cqty_{i}_{symbol}")
                    with c_btn:
                        st.write("")
                        if st.button(f"Close {symbol}", key=f"close_alpaca_{i}"):
                            result = _call_alpaca("close_position", symbol=symbol, qty=close_qty if close_qty > 0 else None)
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                st.success(f"Close order submitted for {symbol}")
                                st.session_state.pop("positions_data", None)
                                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Active / Pending Orders
# ══════════════════════════════════════════════════════════════════════════════
with tab_orders:
    st.subheader(f"Active Orders — {broker_label}")

    if st.button("🔄 Refresh Orders", key="refresh_orders"):
        st.session_state["orders_data"] = _broker_call(
            "get_orders", "get_orders",
            alpaca_kwargs={"status": "open"},
        )

    orders = st.session_state.get("orders_data", [])
    if not orders:
        orders = _broker_call("get_orders", "get_orders", alpaca_kwargs={"status": "open"})
        st.session_state["orders_data"] = orders

    if isinstance(orders, list) and orders and "error" not in (orders[0] if orders else {}):
        df_ord = pd.DataFrame(orders)
        st.dataframe(df_ord, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Cancel an Order")
        id_field = "id" if broker in ("alpaca_1", "alpaca_2") else "ticket"
        order_ids = [str(o.get(id_field, "")) for o in orders if o.get(id_field)]
        if order_ids:
            selected_id = st.selectbox("Select order to cancel", options=order_ids)
            if st.button("Cancel Order", key="cancel_btn"):
                if broker in ("alpaca_1", "alpaca_2"):
                    result = _call_alpaca("cancel_order", order_id=selected_id)
                else:
                    result = _call_mt5("cancel_order", ticket=int(selected_id))
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(f"Order {selected_id} cancelled.")
                    st.session_state.pop("orders_data", None)
                    st.rerun()
    else:
        st.info("No active/pending orders.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Trade History
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader(f"Trade History — {broker_label}")

    col_lim, _ = st.columns([1, 3])
    with col_lim:
        hist_limit = st.number_input("Limit", min_value=5, max_value=500, value=50, step=5, key="hist_limit")

    if st.button("🔄 Load History", key="load_history"):
        history_data = _broker_call(
            "get_trade_history", "get_history",
            alpaca_kwargs={"limit": hist_limit},
            mt5_kwargs={"limit": hist_limit},
        )
        st.session_state["history_data"] = history_data

    history_data = st.session_state.get("history_data", [])
    if history_data and "error" not in (history_data[0] if isinstance(history_data, list) and history_data else {}):
        df_hist = pd.DataFrame(history_data)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        # ── Quick P&L summary from local DB ────────────────────────────────────
        try:
            sys.path.insert(0, str(_MAIN_ROOT))
            from src.autonomous_agent.database import AgentDatabase
            db      = AgentDatabase()
            summary = db.pnl_summary(broker=broker)
            if summary.get("total_trades", 0) > 0:
                st.divider()
                st.markdown("#### Local DB P&L Summary")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Trades",    summary.get("total_trades", 0))
                c2.metric("Realised P&L",    f"${summary.get('total_realized_pl', 0):+,.2f}")
                c3.metric("Hit Rate",        f"{summary.get('hit_rate', 0)*100:.1f}%")
                c4.metric("Avg P&L / Trade", f"${summary.get('avg_pl_per_trade', 0):+,.2f}")
        except Exception:
            pass
    else:
        st.info("No history loaded. Click 'Load History' to fetch.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Order Placement Form
# ══════════════════════════════════════════════════════════════════════════════
with tab_order_form:
    st.subheader(f"Place Order — {broker_label}")
    st.caption("Fields shown/hidden based on the selected order type.")

    # Get valid order types for current broker from the central catalogue
    valid_types  = get_order_types(broker)
    type_labels  = get_order_type_labels(broker)

    col_sym, col_type = st.columns(2)
    with col_sym:
        symbol = st.text_input("Symbol", value="AAPL" if broker != "mt5" else "US30", key="form_symbol")
    with col_type:
        order_type = st.selectbox(
            "Order Type",
            options=valid_types,
            format_func=lambda t: type_labels.get(t, t),
            key="form_order_type",
        )

    # Show required fields dynamically based on the selected order type
    req = required_fields(broker, order_type)
    opt = optional_fields(broker, order_type)

    if broker in ("alpaca_1", "alpaca_2"):
        col_side, col_qty = st.columns(2)
        with col_side:
            side = st.selectbox("Side", ["buy", "sell"], key="form_side")
        with col_qty:
            qty  = st.number_input("Quantity", min_value=0.01, value=1.0, step=0.01, key="form_qty")

        # Conditional price fields
        limit_price = None
        stop_price  = None
        trail_price = None
        trail_pct   = None
        tif         = "day"
        take_profit_price = None
        stop_loss_price   = None

        if "limit_price" in req:
            limit_price = st.number_input("Limit Price", min_value=0.01, value=100.0, key="form_limit")
        if "stop_price" in req:
            stop_price  = st.number_input("Stop Price",  min_value=0.01, value=100.0, key="form_stop")
        if order_type == "trailing_stop":
            trail_col1, trail_col2 = st.columns(2)
            with trail_col1:
                trail_price = st.number_input("Trail Price ($)", value=0.0, key="form_trail_p")
                if trail_price == 0:
                    trail_price = None
            with trail_col2:
                trail_pct = st.number_input("Trail Percent (%)", value=0.0, key="form_trail_pct")
                if trail_pct == 0:
                    trail_pct = None

        tif = st.selectbox("Time-in-Force", ["day", "gtc", "ioc", "fok", "opg", "cls"], key="form_tif")

        # Optional bracket SL/TP
        with st.expander("🛡 Bracket Order (optional SL / TP)", expanded=False):
            col_tp, col_sl = st.columns(2)
            with col_tp:
                take_profit_price = st.number_input("Take Profit Limit", value=0.0, key="form_tp")
                if take_profit_price == 0:
                    take_profit_price = None
            with col_sl:
                stop_loss_price = st.number_input("Stop Loss Stop", value=0.0, key="form_sl_stop")
                sl_limit_price  = st.number_input("Stop Loss Limit (optional)", value=0.0, key="form_sl_limit")
                if stop_loss_price == 0:
                    stop_loss_price = None

        st.divider()
        if st.button("🚀 Submit Order", use_container_width=True, key="submit_alpaca"):
            params = {
                "symbol": symbol, "side": side, "qty": qty,
                "order_type": order_type, "limit_price": limit_price,
                "stop_price": stop_price, "trail_price": trail_price,
                "trail_percent": trail_pct, "time_in_force": tif,
                "take_profit": {"limit_price": take_profit_price} if take_profit_price else None,
                "stop_loss": {"stop_price": stop_loss_price, "limit_price": sl_limit_price or None} if stop_loss_price else None,
            }
            try:
                validate_order(broker, order_type, params)
                with st.spinner("Submitting…"):
                    result = _call_alpaca("place_order", **{k: v for k, v in params.items() if k != "account"})
                if "error" in result:
                    st.error(f"Order failed: {result['error']}")
                else:
                    st.success(f"✅ Order {result.get('order_id', '?')} submitted — status: {result.get('status', '?')}")
                    st.json(result)
                    # Auto-log to local trade database
                    try:
                        sys.path.insert(0, str(_MAIN_ROOT))
                        from src.autonomous_agent.database import AgentDatabase
                        AgentDatabase().log_trade({
                            "symbol": symbol, "side": side, "qty": qty,
                            "order_type": order_type,
                            "fill_price": 0,                 # filled price arrives via order status callback
                            "broker": broker,
                            "broker_order_id": result.get("order_id", ""),
                            "status": result.get("status", "submitted"),
                        })
                    except Exception:
                        pass
            except ValueError as ve:
                st.error(str(ve))

    else:
        # MT5 order form
        col_vol, col_price = st.columns(2)
        with col_vol:
            volume = st.number_input("Volume (lots)", min_value=0.01, value=0.1, step=0.01, key="form_mt5_vol")
        with col_price:
            price  = st.number_input("Price (0 = market fill)", value=0.0, key="form_mt5_price")
            if price == 0 and order_type in ("buy", "sell"):
                price = None   # market order — price auto-filled in mt5_tester

        col_sl, col_tp = st.columns(2)
        with col_sl:
            sl = st.number_input("Stop Loss (0 = none)", value=0.0, key="form_mt5_sl")
            if sl == 0:
                sl = None
        with col_tp:
            tp = st.number_input("Take Profit (0 = none)", value=0.0, key="form_mt5_tp")
            if tp == 0:
                tp = None

        price_stoplimit = None
        if "price_stoplimit" in req:
            price_stoplimit = st.number_input("Stop-Limit Price", value=0.0, key="form_mt5_psl")

        comment = st.text_input("Comment", value="ConnectorsTester", key="form_mt5_comment")

        st.divider()
        if st.button("🚀 Submit MT5 Order", use_container_width=True, key="submit_mt5"):
            params = {"symbol": symbol, "volume": volume, "order_type": order_type}
            try:
                validate_order("mt5", order_type, params)
                with st.spinner("Submitting…"):
                    result = _call_mt5("place_order",
                        symbol=symbol, order_type=order_type, volume=volume,
                        price=price, sl=sl, tp=tp,
                        price_stoplimit=price_stoplimit,
                        comment=comment,
                    )
                if "error" in result:
                    st.error(f"Order failed: {result['error']}")
                else:
                    st.success(f"✅ Order ticket {result.get('order','?')} — {result.get('status','?')}")
                    st.json(result)
                    try:
                        from src.autonomous_agent.database import AgentDatabase
                        AgentDatabase().log_trade({
                            "symbol": symbol, "side": "buy" if "buy" in order_type else "sell",
                            "qty": volume, "order_type": order_type,
                            "fill_price": result.get("price", 0),
                            "broker": "mt5",
                            "broker_order_id": str(result.get("order", "")),
                            "sl": sl, "tp": tp,
                            "status": result.get("status", "submitted"),
                        })
                    except Exception:
                        pass
            except ValueError as ve:
                st.error(str(ve))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: Price Levels
# ══════════════════════════════════════════════════════════════════════════════
with tab_prices:
    st.subheader("US30 Price Levels")
    st.caption("Liquidity zones, FVG, session/day/week/month highs, lows, mids, opens, closes.")

    csv_path = os.environ.get("US30_CSV_PATH", "").strip()
    if not csv_path or not Path(csv_path).exists():
        st.warning(
            "US30 CSV not found.  Set `US30_CSV_PATH` in `.env` to enable price level detection.  "
            "Example: `US30_CSV_PATH=../Dataset-Testing-US30/us30_m5.csv`"
        )
    else:
        if st.button("🎯 Detect Price Levels", key="detect_levels"):
            with st.spinner("Running price level detection…"):
                try:
                    import pandas as pd
                    sys.path.insert(0, str(_MAIN_ROOT))
                    from src.tools.price_level_detector import detect_all_price_levels

                    df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
                    df = df.iloc[-5000:] if len(df) > 5000 else df
                    levels = detect_all_price_levels(df)
                    st.session_state["price_levels"] = levels
                except Exception as exc:
                    st.error(f"Detection failed: {exc}")

        levels = st.session_state.get("price_levels", {})
        if levels:
            for level_type, data in levels.items():
                with st.expander(f"📍 {level_type}", expanded=False):
                    if isinstance(data, list):
                        if data and isinstance(data[0], dict):
                            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                        else:
                            st.write(data)
                    elif isinstance(data, dict):
                        st.json(data)
                    else:
                        st.write(data)
        else:
            st.info("Click 'Detect Price Levels' to run the detector.")


# ─────────────────────────────────────────────────────────────────────────────
# Floating autonomous agent widget (always rendered, every page)
# ─────────────────────────────────────────────────────────────────────────────
# We use http://localhost:8000 as the API base — this is the FastAPI server
# from the main project if the user has it running.  The tester agent's
# /ct/agent/chat endpoint is served by the tester's own FastAPI (future work).
# For Streamlit-only usage the widget sends messages to the backend via httpx
# internally (the agent runs in the Streamlit session, not a separate server).
render_connectors_agent_widget(
    broker=broker,
    api_base_url=os.environ.get("API_BASE_URL", "http://localhost:8000"),
)
