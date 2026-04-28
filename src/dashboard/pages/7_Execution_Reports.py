"""Execution & Reports — Live positions, full trade history (SL/TP/P&L), vault reports."""
from __future__ import annotations

import requests
import streamlit as st
import pandas as pd
from src.dashboard.config import API_BASE_URL, REFRESH_INTERVAL_SECONDS
from src.dashboard.components import apply_theme
from src.dashboard.session_state import init_session_state
from src.dashboard.autonomous_chat import render_autonomous_agent_widget
from src.dashboard.cockpit import render_cockpit

st.set_page_config(page_title="Execution & Reports — Trader-Suit", page_icon="📡", layout="wide")
apply_theme()
init_session_state()
render_autonomous_agent_widget(api_base_url=API_BASE_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(endpoint: str, fallback=None):
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return fallback


def _color_pnl(val):
    """Pandas Styler: green positive, red negative P&L."""
    try:
        v = float(val)
        color = "#3fb950" if v >= 0 else "#f85149"
        return f"color: {color}; font-weight: 600"
    except Exception:
        return ""


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📡 Execution & Reports")
    refresh = st.slider("Refresh (s)", 2, 60, REFRESH_INTERVAL_SECONDS)
    auto_refresh = st.toggle("Auto-refresh", value=st.session_state.get("auto_refresh", True))
    st.session_state["auto_refresh"] = auto_refresh
    st.divider()
    alpaca_ok = (_fetch("/alpaca/status", {}) or {}).get("connected", False)
    if alpaca_ok:
        st.success("✅ Alpaca connected")
    else:
        st.warning("⚠️ Alpaca not connected")
        st.caption("Set ALPACA_API_KEY + ALPACA_SECRET_KEY in .env")
    st.divider()
    st.caption(f"API: `{API_BASE_URL}`")

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_exec, tab_trades, tab_reports = st.tabs(
    ["📡 Execution Monitor", "📊 Trade History", "📋 Reports"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Execution Monitor
# ══════════════════════════════════════════════════════════════════════════════
with tab_exec:
    st.markdown("## 📡 Execution Monitor")

    # Live ticker
    quote = _fetch("/quote", None)
    if quote and (quote.get("bid") or quote.get("ask")):
        sym = quote.get("symbol", "—")
        bid = float(quote.get("bid", 0) or 0)
        ask = float(quote.get("ask", 0) or 0)
        mid = (bid + ask) / 2 if (bid or ask) else 0
        st.markdown(
            f"**Live ticker ({sym})** — "
            f"Mid: `{mid:.4f}` | Bid: `{bid:.4f}` | Ask: `{ask:.4f}`"
        )
    else:
        st.caption("Live ticker: set ALPACA_API_KEY and ALPACA_TICKER_SYMBOL.")

    st.divider()

    # Open positions with full detail
    st.markdown("### 🟢 Open Positions")
    positions = _fetch("/positions", []) or []
    if positions:
        rows = []
        for p in positions:
            entry = float(p.get("entry_price") or 0)
            current = float(p.get("current_price") or 0)
            pnl = float(p.get("unrealized_pl") or 0)
            pnl_pct = ((current - entry) / entry * 100) if entry else 0
            rows.append({
                "Symbol":    p.get("symbol", ""),
                "Side":      p.get("side", "").upper(),
                "Qty":       p.get("qty", 0),
                "Entry":     f"{entry:.4f}" if entry else "—",
                "Current":   f"{current:.4f}" if current else "—",
                "Unr. P&L":  round(pnl, 2),
                "P&L %":     f"{pnl_pct:+.2f}%",
                "Mkt Value": round(float(p.get("market_value") or 0), 2),
            })
        df = pd.DataFrame(rows)
        styled = df.style.applymap(_color_pnl, subset=["Unr. P&L"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions.")

    st.divider()
    render_cockpit(refresh_interval_sec=refresh, auto_refresh=auto_refresh)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Trade History (closed orders)
# ══════════════════════════════════════════════════════════════════════════════
with tab_trades:
    st.markdown("## 📊 Trade History")

    limit = st.slider("Max trades", 10, 200, 50, key="trade_limit")
    data = _fetch(f"/trades/history?limit={limit}", None)

    if data is None:
        st.error("Could not load trade history — is the API running?")
    else:
        source = data.get("source", "unknown")
        trades = data.get("trades", [])
        count  = data.get("count", 0)

        source_label = {"alpaca": "✅ Alpaca", "datastore": "📁 DataStore",
                        "demo": "🔵 Demo data", "vault": "📂 Vault logs"}.get(source, source)
        st.caption(f"Source: **{source_label}** | {count} trade(s) loaded")

        if source == "demo":
            st.info(
                "Showing demo data. Connect Alpaca (ALPACA_API_KEY + ALPACA_SECRET_KEY) "
                "to see real closed orders with SL/TP."
            )

        if trades:
            # Build display dataframe
            rows = []
            for t in trades:
                pnl = t.get("pnl")
                rows.append({
                    "ID":         str(t.get("trade_id", ""))[:12],
                    "Symbol":     t.get("symbol", "—"),
                    "Side":       (t.get("side") or "—").upper(),
                    "Type":       t.get("type", "—"),
                    "Qty":        t.get("qty", "—"),
                    "Entry":      t.get("entry_price", "—"),
                    "SL":         t.get("sl", "—"),
                    "TP":         t.get("tp", "—"),
                    "P&L":        round(pnl, 2) if pnl is not None else "—",
                    "Sharpe":     t.get("sharpe", "—"),
                    "Max DD":     t.get("max_dd", "—"),
                    "Status":     t.get("status", "—"),
                    "Opened":     str(t.get("opened_at", ""))[:19],
                    "Closed":     str(t.get("closed_at", ""))[:19],
                    "Src":        t.get("source", "—"),
                })
            df = pd.DataFrame(rows)

            # Apply P&L colour
            numeric_pnl = pd.to_numeric(df["P&L"], errors="coerce")
            styled = df.style.applymap(_color_pnl, subset=["P&L"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Summary stats
            numeric_pnl_clean = numeric_pnl.dropna()
            if len(numeric_pnl_clean):
                c1, c2, c3, c4 = st.columns(4)
                wins = (numeric_pnl_clean > 0).sum()
                total = len(numeric_pnl_clean)
                c1.metric("Total P&L", f"{numeric_pnl_clean.sum():+.2f}")
                c2.metric("Win Rate", f"{wins/total*100:.1f}%")
                c3.metric("Best Trade", f"{numeric_pnl_clean.max():+.2f}")
                c4.metric("Worst Trade", f"{numeric_pnl_clean.min():+.2f}")
        else:
            st.caption("No trades found.")

        # Download button
        if trades:
            csv = pd.DataFrame(trades).to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name="trade_history.csv",
                mime="text/csv",
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Reports (vault briefings, graveyard, approved)
# ══════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.markdown("## 📋 Reports")

    col_left, col_right = st.columns([3, 1])
    with col_right:
        refresh_report = st.button("🔄 Refresh", use_container_width=True)

    report_data = _fetch("/trades/report", None)

    if report_data is None:
        st.error("Could not load reports — is the API running?")
    else:
        generated = report_data.get("generated_at", "")
        sections  = report_data.get("sections", {})

        st.caption(f"Generated: {generated[:19]} UTC")

        if not sections or all(not v for v in sections.values()):
            st.info(
                "No vault content yet. Submit an alpha idea on the Alpha Idea Lab page "
                "to begin the workflow and generate reports."
            )
        else:
            folder_icons = {
                "Reports":   "📄",
                "Approved":  "✅",
                "Plans":     "📝",
                "Graveyard": "⚰️",
            }
            for folder, content in sections.items():
                icon = folder_icons.get(folder, "📁")
                with st.expander(f"{icon} {folder}", expanded=(folder == "Reports")):
                    if content:
                        st.markdown(content, unsafe_allow_html=False)
                    else:
                        st.caption("Empty.")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📧 Send Report (Gmail/Telegram)", use_container_width=True):
                st.info("Reporter agent not yet wired — coming in next sprint.")
        with c2:
            if st.button("⚰️ Graveyard Summary", use_container_width=True):
                st.info("Use the Vault Explorer to browse Graveyard/ directly.")
