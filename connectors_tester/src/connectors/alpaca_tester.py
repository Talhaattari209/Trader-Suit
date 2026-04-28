"""
connectors_tester/src/connectors/alpaca_tester.py
===================================================
Full Alpaca connector for the tester project.

TWO INTEGRATION PATHS:
  1. Direct SDK (alpaca-py)   — used for all real order/account operations.
     This is the primary path: every function calls the official SDK directly
     so we have full control over request parameters and error handling.

  2. Alpaca MCP Server (HTTP) — used ADDITIONALLY when ALPACA_MCP_URL is set.
     The official Alpaca MCP server (npx @alpaca-markets/mcp-server) exposes
     all broker operations as MCP tools over a local HTTP port.
     We call it via httpx and print full debug output.
     This path is OPTIONAL: the tester works without the MCP sidecar.

ORDER TYPES SUPPORTED (per official alpaca-py docs):
  market         — immediate fill at market price
  limit          — fill at limit_price or better
  stop           — becomes market when stop_price is triggered
  stop_limit     — becomes limit when stop_price is triggered
  trailing_stop  — stop that moves with the price by trail_price or trail_percent

BRACKET ORDERS:
  Alpaca supports bracket orders natively via order_class="bracket" with
  take_profit and stop_loss legs submitted in one call.

TIME-IN-FORCE:
  day, gtc, opg, cls, ioc, fok  — see AlpacaTIF enum

CREDENTIALS:
  Read exclusively from environment (loaded from .env by load_dotenv()).
  Never hard-coded here.

DEBUG OUTPUT (every call):
  === ALPACA REQUEST ===   (printed before the SDK call)
  === ALPACA RESPONSE ===  (printed after, with first 500 chars)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("connectors_tester.alpaca")


# ─────────────────────────────────────────────────────────────────────────────
# Environment helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_env() -> None:
    """Load .env once.  override=False → OS env always wins."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass   # dotenv absent → rely on OS env; not fatal


def _creds(account: int = 1) -> tuple[str, str, bool]:
    """
    Return (api_key, secret_key, paper) for the requested account number.

    paper is inferred from the endpoint URL so a misconfigured endpoint
    cannot accidentally route to a live account.
    """
    _load_env()
    if account == 2:
        key    = os.environ.get("ALPACA_API_KEY_2", "").strip()
        secret = os.environ.get("ALPACA_SECRET_KEY_2", "").strip()
        ep     = os.environ.get("ALPACA_ENDPOINT_2", "https://paper-api.alpaca.markets").strip()
    else:
        key    = os.environ.get("ALPACA_API_KEY", "").strip()
        secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
        ep     = os.environ.get("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets").strip()

    if not key or not secret:
        raise RuntimeError(
            f"Alpaca account {account} credentials missing in .env  "
            f"(ALPACA_API_KEY{'_2' if account==2 else ''} / "
            f"ALPACA_SECRET_KEY{'_2' if account==2 else ''})"
        )
    paper = "paper" in ep.lower()   # explicit paper flag derived from endpoint
    return key, secret, paper


def _trading_client(account: int = 1):
    """
    Build a TradingClient for the given account.
    Lazy: created on each call (cheap — no network round-trip until first API call).
    """
    from alpaca.trading.client import TradingClient
    key, secret, paper = _creds(account)
    return TradingClient(api_key=key, secret_key=secret, paper=paper)


def _data_client(account: int = 1):
    """
    Build a StockHistoricalDataClient (also works for crypto bars).
    Uses the same credentials as the trading client.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    key, secret, _ = _creds(account)
    return StockHistoricalDataClient(api_key=key, secret_key=secret)


# ─────────────────────────────────────────────────────────────────────────────
# Debug printer
# ─────────────────────────────────────────────────────────────────────────────

def _debug(section: str, data: Any) -> None:
    """
    Print a clearly delimited debug block to stdout.

    The === markers make it trivial to grep the terminal output for specific
    calls during a live demo or debugging session.
    """
    text = json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data
    print(f"\n{'='*60}\n{section}\n{text[:800]}\n{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────
# Alpaca MCP Server (optional sidecar)
# ─────────────────────────────────────────────────────────────────────────────

def _mcp_call(tool_name: str, args: dict) -> dict | None:
    """
    Call the official Alpaca MCP server via HTTP.

    The MCP server (npx @alpaca-markets/mcp-server) exposes all Alpaca
    operations as JSON-RPC 2.0 endpoints over a local port.
    Returns the result dict, or None if the server is not running.

    WHY call MCP in addition to the SDK?
      The MCP server handles auth refresh, rate-limit retries, and structured
      error codes that map directly to the official Alpaca API docs.  It also
      provides a single audit trail that other MCP-aware tools can read.
    """
    mcp_url = os.environ.get("ALPACA_MCP_URL", "").strip()
    if not mcp_url:
        return None   # MCP sidecar not configured — skip silently

    try:
        import httpx
        payload = {
            "jsonrpc": "2.0",
            "id":      1,
            "method":  "tools/call",          # standard MCP tools/call endpoint
            "params":  {"name": tool_name, "arguments": args},
        }
        _debug("=== ALPACA MCP REQUEST ===", {"url": mcp_url, "tool": tool_name, "args": args})
        r = httpx.post(mcp_url, json=payload, timeout=15.0)
        r.raise_for_status()
        result = r.json().get("result", {})
        _debug("=== ALPACA MCP RESPONSE ===", result)
        return result
    except Exception as exc:
        logger.warning("[AlpacaMCP] %s call failed: %s", tool_name, exc)
        return None   # MCP failure → fall through to SDK path


# ─────────────────────────────────────────────────────────────────────────────
# Account & Portfolio
# ─────────────────────────────────────────────────────────────────────────────

def get_account(account: int = 1) -> dict:
    """
    Return account summary: equity, cash, buying_power, unrealized_pl.

    Tries the MCP server first (richer error metadata), then falls back
    to direct SDK if MCP is unavailable.
    """
    req = {"account": account}
    _debug("=== ALPACA REQUEST === get_account", req)

    # MCP path (optional)
    mcp = _mcp_call("get_account", req)
    if mcp:
        _debug("=== ALPACA RESPONSE === get_account (MCP)", mcp)
        return mcp

    # SDK path (primary)
    tc  = _trading_client(account)
    acc = tc.get_account()
    result = {
        "account_number":    getattr(acc, "account_number", ""),
        "status":            str(getattr(acc, "status", "")),
        "equity":            float(getattr(acc, "equity", 0) or 0),
        "cash":              float(getattr(acc, "cash", 0) or 0),
        "buying_power":      float(getattr(acc, "buying_power", 0) or 0),
        "unrealized_pl":     float(getattr(acc, "unrealized_pl", 0) or 0),
        "pattern_day_trader":bool(getattr(acc, "pattern_day_trader", False)),
        "account_type":      "paper",
        "source":            f"alpaca_sdk_account_{account}",
    }
    _debug("=== ALPACA RESPONSE === get_account (SDK)", result)
    return result


def get_positions(account: int = 1) -> list[dict]:
    """Return all open positions for the given account as a list of dicts."""
    _debug("=== ALPACA REQUEST === get_positions", {"account": account})

    mcp = _mcp_call("get_positions", {"account": account})
    if mcp:
        _debug("=== ALPACA RESPONSE === get_positions (MCP)", mcp)
        return mcp if isinstance(mcp, list) else mcp.get("positions", [])

    tc        = _trading_client(account)
    positions = tc.get_all_positions()
    result = [
        {
            "symbol":          str(p.symbol),
            "qty":             float(p.qty or 0),
            "side":            str(p.side).lower(),
            "market_value":    float(p.market_value or 0),
            "avg_entry_price": float(p.avg_entry_price or 0),
            "current_price":   float(p.current_price or 0),
            "unrealized_pl":   float(p.unrealized_pl or 0),
            "unrealized_plpc": float(p.unrealized_plpc or 0),
            "cost_basis":      float(p.cost_basis or 0),
        }
        for p in positions
    ]
    _debug("=== ALPACA RESPONSE === get_positions (SDK)", result)
    return result


def get_orders(account: int = 1, status: str = "all", limit: int = 50) -> list[dict]:
    """
    Return recent orders.

    status: "open" | "closed" | "all"
    Alpaca uses QueryOrderStatus enum; we map the string here.
    """
    _debug("=== ALPACA REQUEST === get_orders", {"account": account, "status": status, "limit": limit})

    mcp = _mcp_call("get_orders", {"account": account, "status": status, "limit": limit})
    if mcp:
        _debug("=== ALPACA RESPONSE === get_orders (MCP)", mcp)
        return mcp if isinstance(mcp, list) else mcp.get("orders", [])

    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import QueryOrderStatus

    # Map plain string to Alpaca enum
    status_map = {
        "open":   QueryOrderStatus.OPEN,
        "closed": QueryOrderStatus.CLOSED,
        "all":    QueryOrderStatus.ALL,
    }
    req = GetOrdersRequest(status=status_map.get(status, QueryOrderStatus.ALL), limit=limit)
    tc     = _trading_client(account)
    orders = tc.get_orders(filter=req)
    result = [
        {
            "id":              str(o.id),
            "symbol":          str(o.symbol),
            "side":            str(o.side).lower(),
            "type":            str(o.order_type).lower(),
            "qty":             float(o.qty or 0),
            "filled_qty":      float(o.filled_qty or 0),
            "limit_price":     float(o.limit_price or 0),
            "stop_price":      float(o.stop_price or 0),
            "filled_avg_price":float(o.filled_avg_price or 0),
            "status":          str(o.status).lower(),
            "time_in_force":   str(o.time_in_force).lower(),
            "submitted_at":    str(o.submitted_at or ""),
            "filled_at":       str(o.filled_at or ""),
        }
        for o in orders
    ]
    _debug("=== ALPACA RESPONSE === get_orders (SDK)", result)
    return result


def get_portfolio_history(account: int = 1, days: int = 30) -> list[dict]:
    """Return daily equity snapshots for P&L curve."""
    _debug("=== ALPACA REQUEST === get_portfolio_history", {"account": account, "days": days})

    mcp = _mcp_call("get_portfolio_history", {"account": account, "period": f"{days}D"})
    if mcp:
        _debug("=== ALPACA RESPONSE === get_portfolio_history (MCP)", mcp)
        return mcp if isinstance(mcp, list) else mcp.get("history", [])

    from alpaca.trading.requests import GetPortfolioHistoryRequest
    tc   = _trading_client(account)
    req  = GetPortfolioHistoryRequest(period=f"{days}D", timeframe="1D", extended_hours=False)
    hist = tc.get_portfolio_history(filter=req)
    if not hist or not hist.timestamp:
        return []
    result = [
        {
            "timestamp": str(ts),
            "equity":    float(eq or 0),
            "pnl_pct":   float(plpc or 0) * 100,   # SDK returns fraction; convert to %
        }
        for ts, eq, plpc in zip(hist.timestamp or [], hist.equity or [], hist.profit_loss_pct or [])
    ]
    _debug("=== ALPACA RESPONSE === get_portfolio_history (SDK)", {"count": len(result)})
    return result


def get_trade_history(account: int = 1, limit: int = 50) -> list[dict]:
    """Return closed/filled orders as trade history."""
    return get_orders(account=account, status="closed", limit=limit)


def get_latest_quote(symbol: str, account: int = 1) -> dict:
    """Return latest bid/ask/mid for a symbol."""
    _debug("=== ALPACA REQUEST === get_latest_quote", {"symbol": symbol, "account": account})

    mcp = _mcp_call("get_latest_quote", {"symbol": symbol})
    if mcp:
        _debug("=== ALPACA RESPONSE === get_latest_quote (MCP)", mcp)
        return mcp

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest

    dc    = _data_client(account)
    req   = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quote = dc.get_stock_latest_quote(req)
    q     = quote.get(symbol)
    if not q:
        return {"symbol": symbol, "bid": 0, "ask": 0, "mid": 0, "error": "no quote"}
    bid = float(getattr(q, "bid_price", 0) or 0)
    ask = float(getattr(q, "ask_price", 0) or 0)
    result = {"symbol": symbol, "bid": bid, "ask": ask, "mid": (bid + ask) / 2 if bid and ask else 0}
    _debug("=== ALPACA RESPONSE === get_latest_quote (SDK)", result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Order Placement — all official Alpaca order types
# ─────────────────────────────────────────────────────────────────────────────

def place_order(
    symbol:          str,
    side:            str,            # "buy" | "sell"
    qty:             float,
    order_type:      str = "market", # see ALPACA_ORDER_TYPES in order_types_handler.py
    limit_price:     float | None = None,
    stop_price:      float | None = None,
    trail_price:     float | None = None,   # for trailing_stop: absolute offset
    trail_percent:   float | None = None,   # for trailing_stop: percentage offset
    time_in_force:   str = "day",    # "day" | "gtc" | "ioc" | "fok" | "opg" | "cls"
    take_profit:     dict | None = None,    # bracket: {"limit_price": X}
    stop_loss:       dict | None = None,    # bracket: {"stop_price": X, "limit_price": Y}
    account:         int = 1,
) -> dict:
    """
    Place any Alpaca order type using the correct SDK request class.

    WHY a single function for all types?
      A monolithic dispatcher ensures the same debug output format for every
      order type and avoids duplicating the MCP→SDK fallback logic.

    SDK classes used per type:
      market       → MarketOrderRequest
      limit        → LimitOrderRequest
      stop         → StopOrderRequest
      stop_limit   → StopLimitOrderRequest
      trailing_stop→ TrailingStopOrderRequest
    Bracket legs are attached as order_class="bracket" with take_profit/stop_loss.
    """
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        StopLimitOrderRequest,
        TrailingStopOrderRequest,
        TakeProfitRequest,
        StopLossRequest,
    )

    req_data = {
        "symbol": symbol, "side": side, "qty": qty, "order_type": order_type,
        "limit_price": limit_price, "stop_price": stop_price,
        "trail_price": trail_price, "trail_percent": trail_percent,
        "time_in_force": time_in_force, "take_profit": take_profit,
        "stop_loss": stop_loss, "account": account,
    }
    _debug("=== ALPACA REQUEST === place_order", req_data)

    # Try MCP first — it handles all order types natively
    mcp = _mcp_call("place_order", req_data)
    if mcp:
        _debug("=== ALPACA RESPONSE === place_order (MCP)", mcp)
        return mcp

    # SDK path — map strings to enums
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    tif_map = {
        "day": TimeInForce.DAY, "gtc": TimeInForce.GTC,
        "ioc": TimeInForce.IOC, "fok": TimeInForce.FOK,
        "opg": TimeInForce.OPG, "cls": TimeInForce.CLS,
    }
    tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

    # Build optional bracket legs (attached to any order type)
    tp_req = TakeProfitRequest(limit_price=take_profit["limit_price"]) if take_profit else None
    sl_req = StopLossRequest(
        stop_price=stop_loss["stop_price"],
        limit_price=stop_loss.get("limit_price"),
    ) if stop_loss else None
    order_class = "bracket" if (tp_req or sl_req) else "simple"

    # Select the correct request class
    order_type_lower = order_type.lower()
    if order_type_lower == "market":
        req = MarketOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=tif,
            order_class=order_class, take_profit=tp_req, stop_loss=sl_req,
        )
    elif order_type_lower == "limit":
        if limit_price is None:
            raise ValueError("limit_price is required for 'limit' orders.")
        req = LimitOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=tif,
            limit_price=limit_price,
            order_class=order_class, take_profit=tp_req, stop_loss=sl_req,
        )
    elif order_type_lower == "stop":
        if stop_price is None:
            raise ValueError("stop_price is required for 'stop' orders.")
        req = StopOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=tif,
            stop_price=stop_price,
        )
    elif order_type_lower == "stop_limit":
        if stop_price is None or limit_price is None:
            raise ValueError("Both stop_price and limit_price are required for 'stop_limit' orders.")
        req = StopLimitOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=tif,
            stop_price=stop_price, limit_price=limit_price,
        )
    elif order_type_lower == "trailing_stop":
        if trail_price is None and trail_percent is None:
            raise ValueError("Either trail_price or trail_percent is required for 'trailing_stop' orders.")
        req = TrailingStopOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=tif,
            trail_price=trail_price,
            trail_percent=trail_percent,
        )
    else:
        raise ValueError(f"Unknown order_type: '{order_type}'. Valid types: market, limit, stop, stop_limit, trailing_stop.")

    tc    = _trading_client(account)
    order = tc.submit_order(order_data=req)
    result = {
        "order_id":    str(order.id),
        "symbol":      str(order.symbol),
        "side":        side,
        "type":        order_type,
        "qty":         qty,
        "status":      str(order.status).lower(),
        "submitted_at":str(order.submitted_at),
        "account":     account,
        "source":      "alpaca_sdk",
    }
    _debug("=== ALPACA RESPONSE === place_order (SDK)", result)
    return result


def cancel_order(order_id: str, account: int = 1) -> dict:
    """Cancel an open order by its ID."""
    _debug("=== ALPACA REQUEST === cancel_order", {"order_id": order_id, "account": account})

    mcp = _mcp_call("cancel_order", {"order_id": order_id})
    if mcp:
        _debug("=== ALPACA RESPONSE === cancel_order (MCP)", mcp)
        return mcp

    tc = _trading_client(account)
    tc.cancel_order_by_id(order_id)
    result = {"order_id": order_id, "status": "cancelled"}
    _debug("=== ALPACA RESPONSE === cancel_order (SDK)", result)
    return result


def close_position(symbol: str, qty: float | None = None, account: int = 1) -> dict:
    """
    Close an open position.

    qty=None → close the entire position (Alpaca's close_position API).
    qty=X    → close a partial qty using a market sell/buy order.
    """
    _debug("=== ALPACA REQUEST === close_position", {"symbol": symbol, "qty": qty, "account": account})

    mcp = _mcp_call("close_position", {"symbol": symbol, "qty": qty})
    if mcp:
        _debug("=== ALPACA RESPONSE === close_position (MCP)", mcp)
        return mcp

    tc = _trading_client(account)
    if qty is None:
        # Close entire position — Alpaca has a dedicated endpoint for this
        order = tc.close_position(symbol)
    else:
        # Partial close — need to know the current side first
        positions = tc.get_all_positions()
        pos = next((p for p in positions if p.symbol == symbol), None)
        if pos is None:
            return {"error": f"No open position for {symbol}"}
        side = "sell" if str(pos.side).lower() == "long" else "buy"
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        req   = MarketOrderRequest(
            symbol=symbol, qty=qty,
            side=OrderSide.SELL if side == "sell" else OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = tc.submit_order(order_data=req)

    result = {"symbol": symbol, "order_id": str(getattr(order, "id", "")), "status": "closing"}
    _debug("=== ALPACA RESPONSE === close_position (SDK)", result)
    return result


def modify_stop_loss(order_id: str, new_stop: float, account: int = 1) -> dict:
    """
    Replace an open stop order with a new stop price.

    Alpaca does not support in-place modification of bracket legs; the
    standard approach is to cancel-and-replace.
    """
    _debug("=== ALPACA REQUEST === modify_stop_loss", {"order_id": order_id, "new_stop": new_stop})

    mcp = _mcp_call("replace_order", {"order_id": order_id, "stop_price": new_stop})
    if mcp:
        _debug("=== ALPACA RESPONSE === modify_stop_loss (MCP)", mcp)
        return mcp

    from alpaca.trading.requests import ReplaceOrderRequest
    tc     = _trading_client(account)
    result_order = tc.replace_order_by_id(
        order_id=order_id,
        order_request_data=ReplaceOrderRequest(stop_price=new_stop),
    )
    result = {"order_id": str(result_order.id), "new_stop": new_stop, "status": "replaced"}
    _debug("=== ALPACA RESPONSE === modify_stop_loss (SDK)", result)
    return result


def get_bars(symbol: str, timeframe: str = "1D", limit: int = 100, account: int = 1) -> list[dict]:
    """
    Return OHLCV bars for a symbol.

    timeframe: "1Min" | "5Min" | "15Min" | "1Hour" | "1Day"  (Alpaca format)
    """
    _debug("=== ALPACA REQUEST === get_bars", {"symbol": symbol, "timeframe": timeframe, "limit": limit})

    mcp = _mcp_call("get_bars", {"symbol": symbol, "timeframe": timeframe, "limit": limit})
    if mcp:
        _debug("=== ALPACA RESPONSE === get_bars (MCP)", mcp)
        return mcp if isinstance(mcp, list) else []

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    tf_map = {
        "1min": TimeFrame(1, TimeFrameUnit.Minute),
        "5min": TimeFrame(5, TimeFrameUnit.Minute),
        "15min":TimeFrame(15, TimeFrameUnit.Minute),
        "1hour":TimeFrame(1, TimeFrameUnit.Hour),
        "1day": TimeFrame(1, TimeFrameUnit.Day),
    }
    alpaca_tf = tf_map.get(timeframe.lower(), TimeFrame(1, TimeFrameUnit.Day))

    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=limit * 2)   # request extra; Alpaca may have gaps

    key, secret, _ = _creds(account)
    dc  = StockHistoricalDataClient(api_key=key, secret_key=secret)
    req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=alpaca_tf, start=start, end=end, limit=limit)
    bars = dc.get_stock_bars(req)
    df   = bars.df if hasattr(bars, "df") else None

    if df is None or df.empty:
        return []

    # Flatten multi-index if symbol is in the index
    if isinstance(df.index, type(df.index)) and hasattr(df.index, "levels"):
        df = df.reset_index()

    df = df.rename(columns=str.lower)
    result = []
    for _, row in df.tail(limit).iterrows():
        result.append({
            "timestamp": str(row.get("timestamp", row.name)),
            "open":   float(row.get("open",  0)),
            "high":   float(row.get("high",  0)),
            "low":    float(row.get("low",   0)),
            "close":  float(row.get("close", 0)),
            "volume": int(row.get("volume",  0)),
        })
    _debug("=== ALPACA RESPONSE === get_bars (SDK)", {"count": len(result)})
    return result
