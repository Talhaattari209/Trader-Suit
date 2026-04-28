"""
Alpaca-backed data for Trader-Suit API.
Uses ALPACA_API_KEY and ALPACA_SECRET_KEY when set; otherwise callers fall back to mock.
Paper trading by default (ALPACA_PAPER=true).
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional: symbol for "live ticker" when using Alpaca (US equities; no US30 CFD)
ALPACA_TICKER_SYMBOL = os.environ.get("ALPACA_TICKER_SYMBOL", "SPY")

_connector = None


def _get_connector():
    """Lazy AlpacaConnector; returns None if keys missing or import fails."""
    global _connector
    if _connector is not None:
        return _connector
    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        logger.debug("Alpaca credentials not set; API will use mock data")
        return None
    try:
        from src.connectors.alpaca_connector import AlpacaConnector
        paper = os.environ.get("ALPACA_PAPER", "true").strip().lower() in ("1", "true", "yes")
        _connector = AlpacaConnector(api_key=key, secret_key=secret, paper=paper)
        _connector.connect()
        return _connector
    except Exception as e:
        logger.warning("Alpaca connector not available: %s", e)
        return None


def is_alpaca_available() -> bool:
    return _get_connector() is not None


def get_account() -> Optional[dict[str, Any]]:
    """Return account summary (equity, cash, buying_power). None if Alpaca unavailable."""
    conn = _get_connector()
    if not conn:
        return None
    try:
        state = conn.get_account_state()
        return {
            "equity": state.get("equity"),
            "cash": state.get("balance"),
            "buying_power": state.get("buying_power"),
            "drawdown_pct": state.get("drawdown"),
        }
    except Exception as e:
        logger.exception("get_account failed: %s", e)
        return None


def get_positions() -> list[dict[str, Any]]:
    """Return open positions (symbol, qty, side, market_value, unrealized_pl)."""
    conn = _get_connector()
    if not conn:
        return []
    try:
        tc = getattr(conn, "_trading_client", None)
        if tc is None:
            return []
        positions = tc.get_all_positions()
        out = []
        for p in positions or []:
            qty_raw = getattr(p, "qty", 0) or 0
            try:
                qty = float(qty_raw)
            except (TypeError, ValueError):
                qty = 0
            side = "long" if qty >= 0 else "short"
            def _f(v):
                try:
                    return float(v) if v is not None else 0
                except (TypeError, ValueError):
                    return 0
            out.append({
                "symbol": getattr(p, "symbol", "") or "",
                "qty": abs(qty),
                "side": side,
                "market_value": _f(getattr(p, "market_value", None)),
                "unrealized_pl": _f(getattr(p, "unrealized_pl", None)),
                "entry_price": _f(getattr(p, "avg_entry_price", None)),
                "current_price": _f(getattr(p, "current_price", None)),
            })
        return out
    except Exception as e:
        logger.exception("get_positions failed: %s", e)
        return []


def get_portfolio_history(days: int = 30) -> Optional[list[dict[str, Any]]]:
    """Return portfolio equity history for P&L curve (from symbol bars when Alpaca has no direct history)."""
    conn = _get_connector()
    if not conn:
        return None
    return _portfolio_history_from_bars(conn, days)


def _portfolio_history_from_bars(conn, days: int) -> Optional[list[dict[str, Any]]]:
    """Fallback: synthetic equity curve from SPY (or ALPACA_TICKER_SYMBOL) bars."""
    try:
        symbol = ALPACA_TICKER_SYMBOL
        df = conn.get_ohlcv(symbol, "1d", min(days * 2, 252))
        if df is None or df.empty:
            return None
        base = float(df["Close"].iloc[0]) if len(df) > 0 else 100
        out = []
        for ts, row in df.iterrows():
            pct = (float(row["Close"]) / base - 1.0) * 100 if base else 0
            out.append({
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "equity": float(row["Close"]),
                "pnl_pct": round(pct, 2),
            })
        return out
    except Exception as e:
        logger.debug("_portfolio_history_from_bars failed: %s", e)
        return None


def get_closed_orders(limit: int = 50) -> list[dict[str, Any]]:
    """Return closed/filled orders from Alpaca with entry price, side, qty, P&L."""
    conn = _get_connector()
    if not conn:
        return []
    try:
        tc = getattr(conn, "_trading_client", None)
        if tc is None:
            return []
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=limit)
        orders = tc.get_orders(filter=req) or []
        out = []
        for o in orders:
            def _f(v):
                try:
                    return float(v) if v is not None else None
                except (TypeError, ValueError):
                    return None
            filled_qty  = _f(getattr(o, "filled_qty", None))
            filled_avg  = _f(getattr(o, "filled_avg_price", None))
            limit_price = _f(getattr(o, "limit_price", None))
            stop_price  = _f(getattr(o, "stop_price", None))
            out.append({
                "order_id":    str(getattr(o, "id", "")),
                "symbol":      getattr(o, "symbol", ""),
                "side":        str(getattr(o, "side", "")),
                "type":        str(getattr(o, "type", "")),
                "qty":         _f(getattr(o, "qty", None)),
                "filled_qty":  filled_qty,
                "filled_price": filled_avg,
                "limit_price": limit_price,
                "stop_price":  stop_price,
                "status":      str(getattr(o, "status", "")),
                "created_at":  str(getattr(o, "created_at", "")),
                "filled_at":   str(getattr(o, "filled_at", "")),
                "notional":    _f(getattr(o, "notional", None)),
            })
        return out
    except Exception as e:
        logger.exception("get_closed_orders failed: %s", e)
        return []


def get_last_quote(symbol: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Return latest quote for symbol (for live ticker). Uses ALPACA_TICKER_SYMBOL if symbol not given."""
    conn = _get_connector()
    if not conn:
        return None
    sym = (symbol or ALPACA_TICKER_SYMBOL).upper()
    try:
        dc = getattr(conn, "_data_client", None)
        if dc is None or not hasattr(dc, "get_latest_quote"):
            return _last_quote_from_bars(conn, sym)
        quote = dc.get_latest_quote(sym)
        if quote is None:
            return _last_quote_from_bars(conn, sym)
        ap = getattr(quote, "ask_price", None) or 0
        bp = getattr(quote, "bid_price", None) or 0
        return {
            "symbol": sym,
            "bid": float(bp),
            "ask": float(ap),
            "mid": (float(ap) + float(bp)) / 2 if (ap and bp) else None,
            "timestamp": getattr(quote, "timestamp", None),
        }
    except Exception as e:
        logger.debug("get_last_quote failed: %s", e)
        return _last_quote_from_bars(conn, sym)


def _last_quote_from_bars(conn, symbol: str) -> Optional[dict[str, Any]]:
    """Fallback: use last close from 1m bars."""
    try:
        df = conn.get_ohlcv(symbol, "1m", 1)
        if df is None or df.empty:
            return None
        close = float(df["Close"].iloc[-1])
        return {"symbol": symbol, "bid": close, "ask": close, "mid": close, "timestamp": None}
    except Exception:
        return None
