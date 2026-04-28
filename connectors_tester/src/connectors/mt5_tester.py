"""
connectors_tester/src/connectors/mt5_tester.py
================================================
Full MetaTrader 5 connector for the tester project.

ORDER TYPES SUPPORTED (per official MetaTrader5 Python package docs):
  Market orders (instant execution):
    ORDER_TYPE_BUY           — market buy
    ORDER_TYPE_SELL          — market sell

  Pending orders (placed in the order book):
    ORDER_TYPE_BUY_LIMIT     — buy when price drops to limit level
    ORDER_TYPE_SELL_LIMIT    — sell when price rises to limit level
    ORDER_TYPE_BUY_STOP      — buy when price rises to stop level
    ORDER_TYPE_SELL_STOP     — sell when price falls to stop level
    ORDER_TYPE_BUY_STOP_LIMIT  — buy stop that becomes a limit once triggered
    ORDER_TYPE_SELL_STOP_LIMIT — sell stop that becomes a limit once triggered

SL/TP:
  Attached to any order via sl= and tp= fields in the order_send request.
  Modification of existing positions uses TRADE_ACTION_SLTP.

POSITION MANAGEMENT:
  - get_positions()   — mt5.positions_get()
  - get_orders()      — mt5.orders_get() (pending orders)
  - get_history()     — mt5.history_deals_get() (closed deals)
  - modify_sl_tp()    — TRADE_ACTION_SLTP
  - close_position()  — TRADE_ACTION_DEAL in opposite direction

DEBUG OUTPUT (every call):
  === MT5 REQUEST ===   (printed before the call)
  === MT5 RESPONSE ===  (printed after, with first 800 chars)

PLATFORM NOTE:
  MetaTrader5 is a native Windows DLL.  On non-Windows systems all functions
  return {"error": "MT5 is Windows-only"} instead of raising so the Streamlit
  UI can display a clean message rather than crashing.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("connectors_tester.mt5")

_IS_WINDOWS = sys.platform == "win32"   # MT5 package only installs on Windows


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass


def _debug(section: str, data: Any) -> None:
    """Print a delimited debug block — same style as alpaca_tester.py."""
    text = json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data
    print(f"\n{'='*60}\n{section}\n{text[:800]}\n{'='*60}")


def _not_windows() -> dict:
    """Return a clean error dict when called on a non-Windows platform."""
    return {"error": "MT5 is Windows-only. This function is unavailable on non-Windows systems."}


def _get_mt5():
    """
    Lazy import of MetaTrader5.

    We defer the import so the rest of the tester can load on Linux/macOS
    for development purposes.  The actual MT5 functions will simply return
    error dicts on non-Windows.
    """
    if not _IS_WINDOWS:
        raise RuntimeError("MetaTrader5 package is not available on non-Windows systems.")
    import MetaTrader5 as mt5
    return mt5


def _mt5_timeframe(tf: str):
    """Map a human-readable timeframe string to the MT5 TIMEFRAME_ constant."""
    mt5 = _get_mt5()
    mapping = {
        "1m":  mt5.TIMEFRAME_M1,
        "5m":  mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h":  mt5.TIMEFRAME_H1,
        "2h":  mt5.TIMEFRAME_H2,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
        "1w":  mt5.TIMEFRAME_W1,
    }
    return mapping.get(tf.lower(), mt5.TIMEFRAME_H1)


# ─────────────────────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────────────────────

_connected: bool = False   # module-level flag; MT5 is a singleton DLL


def connect() -> dict:
    """
    Initialize the MT5 terminal connection.

    Reads MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH from environment.
    Returns a status dict so callers can surface success/failure in the UI.
    """
    global _connected
    if not _IS_WINDOWS:
        return _not_windows()

    _load_env()
    mt5      = _get_mt5()
    path     = os.environ.get("MT5_PATH", "").strip() or None
    login    = int(os.environ.get("MT5_LOGIN", "0") or "0")
    password = os.environ.get("MT5_PASSWORD", "").strip()
    server   = os.environ.get("MT5_SERVER", "").strip()

    req = {"login": login, "server": server, "path": path}
    _debug("=== MT5 REQUEST === initialize", req)

    # mt5.initialize() accepts path, login, password, server
    if path:
        ok = mt5.initialize(path=path, login=login, password=password, server=server)
    else:
        ok = mt5.initialize(login=login, password=password, server=server)

    if not ok:
        err  = mt5.last_error()
        result = {"connected": False, "error": str(err)}
        _debug("=== MT5 RESPONSE === initialize FAILED", result)
        return result

    _connected = True
    info = mt5.terminal_info()
    result = {
        "connected": True,
        "build":     getattr(info, "build", "unknown"),
        "platform":  "MetaTrader5",
    }
    _debug("=== MT5 RESPONSE === initialize OK", result)
    return result


def disconnect() -> None:
    """Shutdown the MT5 connection (call on app teardown)."""
    global _connected
    if not _IS_WINDOWS or not _connected:
        return
    _get_mt5().shutdown()
    _connected = False


def _ensure_connected() -> dict | None:
    """
    Auto-connect if not already connected.

    Returns an error dict if connection fails (caller should surface this),
    or None if all good.
    """
    if not _IS_WINDOWS:
        return _not_windows()
    if not _connected:
        result = connect()
        if not result.get("connected"):
            return result
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Account & Data
# ─────────────────────────────────────────────────────────────────────────────

def get_account() -> dict:
    """Return MT5 account_info as a plain dict."""
    err = _ensure_connected()
    if err:
        return err

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === account_info", {})
    acc = mt5.account_info()
    if acc is None:
        result = {"error": str(mt5.last_error())}
        _debug("=== MT5 RESPONSE === account_info FAILED", result)
        return result

    result = {
        "login":        getattr(acc, "login",        0),
        "name":         getattr(acc, "name",          ""),
        "server":       getattr(acc, "server",        ""),
        "currency":     getattr(acc, "currency",      ""),
        "balance":      float(getattr(acc, "balance",       0) or 0),
        "equity":       float(getattr(acc, "equity",        0) or 0),
        "margin":       float(getattr(acc, "margin",        0) or 0),
        "free_margin":  float(getattr(acc, "margin_free",   0) or 0),
        "margin_level": float(getattr(acc, "margin_level",  0) or 0),
        "profit":       float(getattr(acc, "profit",        0) or 0),
        "leverage":     int(getattr(acc, "leverage",         1) or 1),
        "source":       "mt5",
    }
    _debug("=== MT5 RESPONSE === account_info", result)
    return result


def get_positions(symbol: str | None = None) -> list[dict]:
    """
    Return all open MT5 positions (or positions for a specific symbol).

    Uses mt5.positions_get() with optional symbol filter.
    """
    err = _ensure_connected()
    if err:
        return [err]

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === positions_get", {"symbol": symbol})

    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if positions is None:
        result = [{"error": str(mt5.last_error())}]
        _debug("=== MT5 RESPONSE === positions_get FAILED", result)
        return result

    result = [
        {
            "ticket":       int(p.ticket),
            "symbol":       str(p.symbol),
            "type":         "buy" if p.type == 0 else "sell",   # 0=BUY, 1=SELL
            "volume":       float(p.volume),
            "open_price":   float(p.price_open),
            "current_price":float(p.price_current),
            "sl":           float(p.sl) if p.sl else None,
            "tp":           float(p.tp) if p.tp else None,
            "swap":         float(p.swap),
            "profit":       float(p.profit),
            "comment":      str(p.comment),
            "magic":        int(p.magic),
            "time":         str(p.time),
        }
        for p in positions
    ]
    _debug("=== MT5 RESPONSE === positions_get", result)
    return result


def get_orders(symbol: str | None = None) -> list[dict]:
    """
    Return all PENDING orders (not yet filled).

    Uses mt5.orders_get() — these are limit, stop, and stop-limit orders
    waiting to be triggered.
    """
    err = _ensure_connected()
    if err:
        return [err]

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === orders_get", {"symbol": symbol})

    orders = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
    if orders is None:
        return [{"error": str(mt5.last_error())}]

    # Map MT5 order type constants to readable strings
    type_names = {
        mt5.ORDER_TYPE_BUY:              "buy",
        mt5.ORDER_TYPE_SELL:             "sell",
        mt5.ORDER_TYPE_BUY_LIMIT:        "buy_limit",
        mt5.ORDER_TYPE_SELL_LIMIT:       "sell_limit",
        mt5.ORDER_TYPE_BUY_STOP:         "buy_stop",
        mt5.ORDER_TYPE_SELL_STOP:        "sell_stop",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT:   "buy_stop_limit",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT:  "sell_stop_limit",
    }
    result = [
        {
            "ticket":      int(o.ticket),
            "symbol":      str(o.symbol),
            "type":        type_names.get(o.type, str(o.type)),
            "volume":      float(o.volume_initial),
            "price":       float(o.price_open),
            "sl":          float(o.sl) if o.sl else None,
            "tp":          float(o.tp) if o.tp else None,
            "price_stoplimit": float(o.price_stoplimit) if o.price_stoplimit else None,
            "comment":     str(o.comment),
            "time_setup":  str(o.time_setup),
        }
        for o in orders
    ]
    _debug("=== MT5 RESPONSE === orders_get", result)
    return result


def get_history(from_date: str | None = None, to_date: str | None = None, limit: int = 100) -> list[dict]:
    """
    Return closed deals (trade history) via mt5.history_deals_get().

    from_date / to_date: ISO-8601 strings.  Defaults to last 30 days.
    """
    err = _ensure_connected()
    if err:
        return [err]

    mt5 = _get_mt5()
    from datetime import datetime, timedelta, timezone

    if from_date:
        dt_from = datetime.fromisoformat(from_date).astimezone(timezone.utc)
    else:
        dt_from = datetime.now(timezone.utc) - timedelta(days=30)   # default: 30-day window

    if to_date:
        dt_to = datetime.fromisoformat(to_date).astimezone(timezone.utc)
    else:
        dt_to = datetime.now(timezone.utc)

    _debug("=== MT5 REQUEST === history_deals_get", {"from": str(dt_from), "to": str(dt_to)})

    deals = mt5.history_deals_get(dt_from, dt_to)
    if deals is None:
        return [{"error": str(mt5.last_error())}]

    result = [
        {
            "ticket":    int(d.ticket),
            "order":     int(d.order),
            "symbol":    str(d.symbol),
            "type":      "buy" if d.type == 0 else "sell",
            "volume":    float(d.volume),
            "price":     float(d.price),
            "commission":float(d.commission),
            "swap":      float(d.swap),
            "profit":    float(d.profit),
            "comment":   str(d.comment),
            "time":      str(d.time),
        }
        for d in list(deals)[-limit:]   # last N deals
    ]
    _debug("=== MT5 RESPONSE === history_deals_get", {"count": len(result)})
    return result


def get_bars(symbol: str, timeframe: str = "1h", count: int = 100) -> list[dict]:
    """Return OHLCV bars from MT5 via mt5.copy_rates_from_pos()."""
    err = _ensure_connected()
    if err:
        return [err]

    mt5 = _get_mt5()
    tf  = _mt5_timeframe(timeframe)
    _debug("=== MT5 REQUEST === copy_rates_from_pos", {"symbol": symbol, "tf": timeframe, "count": count})

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None:
        return [{"error": str(mt5.last_error())}]

    result = [
        {
            "timestamp": str(r["time"]),
            "open":      float(r["open"]),
            "high":      float(r["high"]),
            "low":       float(r["low"]),
            "close":     float(r["close"]),
            "volume":    int(r["tick_volume"]),
        }
        for r in rates
    ]
    _debug("=== MT5 RESPONSE === copy_rates_from_pos", {"count": len(result)})
    return result


def get_latest_tick(symbol: str) -> dict:
    """Return the latest tick (bid/ask/last) for a symbol."""
    err = _ensure_connected()
    if err:
        return err

    mt5   = _get_mt5()
    _debug("=== MT5 REQUEST === symbol_info_tick", {"symbol": symbol})
    tick  = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"error": str(mt5.last_error())}

    result = {
        "symbol": symbol,
        "bid":    float(tick.bid),
        "ask":    float(tick.ask),
        "last":   float(tick.last),
        "volume": int(tick.volume),
        "time":   str(tick.time),
    }
    _debug("=== MT5 RESPONSE === symbol_info_tick", result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Order Placement — all official MT5 order types
# ─────────────────────────────────────────────────────────────────────────────

def place_order(
    symbol:      str,
    order_type:  str,          # see MT5_ORDER_TYPES in order_types_handler.py
    volume:      float,
    price:       float | None = None,    # required for pending; auto-filled for market
    sl:          float | None = None,
    tp:          float | None = None,
    price_stoplimit: float | None = None,  # for buy/sell_stop_limit: the limit price
    comment:     str = "ConnectorsTester",
    magic:       int = 12345,
) -> dict:
    """
    Send any MT5 order type via mt5.order_send().

    Action mapping:
      market orders  → TRADE_ACTION_DEAL   (immediate execution)
      pending orders → TRADE_ACTION_PENDING (enter the order book)

    Type constants mapped from string names so the caller never needs to
    import MetaTrader5 directly.
    """
    err = _ensure_connected()
    if err:
        return err

    mt5 = _get_mt5()

    req_data = {
        "symbol": symbol, "type": order_type, "volume": volume,
        "price": price, "sl": sl, "tp": tp, "comment": comment,
    }
    _debug("=== MT5 REQUEST === place_order", req_data)

    # Map order type string → (action, type_constant)
    ot = order_type.lower().strip()
    type_map = {
        "buy":              (mt5.TRADE_ACTION_DEAL,    mt5.ORDER_TYPE_BUY),
        "sell":             (mt5.TRADE_ACTION_DEAL,    mt5.ORDER_TYPE_SELL),
        "buy_limit":        (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_LIMIT),
        "sell_limit":       (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_LIMIT),
        "buy_stop":         (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_STOP),
        "sell_stop":        (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_STOP),
        "buy_stop_limit":   (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_STOP_LIMIT),
        "sell_stop_limit":  (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_STOP_LIMIT),
    }
    if ot not in type_map:
        return {"error": f"Unknown MT5 order_type: '{order_type}'."}

    action, mt5_type = type_map[ot]

    # For market orders auto-fill price from current tick (required by order_send)
    if action == mt5.TRADE_ACTION_DEAL and price is None:
        tick  = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"Cannot get tick for {symbol}: {mt5.last_error()}"}
        price = float(tick.ask) if "buy" in ot else float(tick.bid)

    if action == mt5.TRADE_ACTION_PENDING and price is None:
        return {"error": f"'price' is required for pending order type '{order_type}'."}

    request: dict[str, Any] = {
        "action":        action,
        "symbol":        symbol,
        "volume":        round(float(volume), 2),
        "type":          mt5_type,
        "price":         float(price),
        "magic":         magic,
        "comment":       comment,
        "type_time":     mt5.ORDER_TIME_GTC,       # GTC: good till cancelled
        "type_filling":  mt5.ORDER_FILLING_IOC,    # IOC: immediate or cancel
    }
    if sl is not None:
        request["sl"] = float(sl)
    if tp is not None:
        request["tp"] = float(tp)
    # buy_stop_limit / sell_stop_limit require the stoplimit (limit) price
    if price_stoplimit is not None:
        request["price_stoplimit"] = float(price_stoplimit)

    result_raw = mt5.order_send(request)
    if result_raw is None:
        result = {"error": str(mt5.last_error())}
        _debug("=== MT5 RESPONSE === place_order FAILED", result)
        return result

    retcode = getattr(result_raw, "retcode", None)
    if retcode != mt5.TRADE_RETCODE_DONE:
        result = {
            "retcode": retcode,
            "error":   getattr(result_raw, "comment", str(retcode)),
            "order":   getattr(result_raw, "order", None),
        }
        _debug("=== MT5 RESPONSE === place_order ERROR", result)
        return result

    result = {
        "order":   int(getattr(result_raw, "order",  0)),
        "deal":    int(getattr(result_raw, "deal",   0)),
        "volume":  float(getattr(result_raw, "volume", volume)),
        "price":   float(getattr(result_raw, "price",  price)),
        "comment": str(getattr(result_raw, "comment", "")),
        "retcode": retcode,
        "status":  "filled" if action == mt5.TRADE_ACTION_DEAL else "pending",
        "source":  "mt5",
    }
    _debug("=== MT5 RESPONSE === place_order OK", result)
    return result


def modify_sl_tp(ticket: int, sl: float | None = None, tp: float | None = None) -> dict:
    """
    Modify stop-loss and/or take-profit on an open position.

    Uses TRADE_ACTION_SLTP — the correct action for in-place SL/TP modification
    (no cancel-and-replace needed, unlike Alpaca).
    """
    err = _ensure_connected()
    if err:
        return err

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === modify_sl_tp", {"ticket": ticket, "sl": sl, "tp": tp})

    # Fetch current position to fill in unchanged fields
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {"error": f"No position with ticket {ticket}: {mt5.last_error()}"}

    pos = positions[0]
    request = {
        "action":  mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol":   pos.symbol,
        "sl":       float(sl) if sl is not None else pos.sl,    # keep existing SL if not changing
        "tp":       float(tp) if tp is not None else pos.tp,    # keep existing TP if not changing
    }
    result_raw = mt5.order_send(request)
    if result_raw is None or getattr(result_raw, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        result = {"error": str(mt5.last_error()), "retcode": getattr(result_raw, "retcode", None)}
        _debug("=== MT5 RESPONSE === modify_sl_tp FAILED", result)
        return result

    result = {"ticket": ticket, "sl": sl, "tp": tp, "status": "modified"}
    _debug("=== MT5 RESPONSE === modify_sl_tp OK", result)
    return result


def close_position(ticket: int, volume: float | None = None) -> dict:
    """
    Close an open MT5 position by sending an opposite TRADE_ACTION_DEAL.

    volume=None → close full volume.
    volume=X    → partial close.
    """
    err = _ensure_connected()
    if err:
        return err

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === close_position", {"ticket": ticket, "volume": volume})

    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {"error": f"No open position with ticket {ticket}"}

    pos         = positions[0]
    close_volume= float(volume) if volume else float(pos.volume)
    # Close by sending the opposite direction
    close_type  = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
    tick        = mt5.symbol_info_tick(pos.symbol)
    close_price = float(tick.bid) if pos.type == 0 else float(tick.ask)

    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "position":  ticket,
        "symbol":    pos.symbol,
        "volume":    round(close_volume, 2),
        "type":      close_type,
        "price":     close_price,
        "comment":   "Close by ConnectorsTester",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result_raw = mt5.order_send(request)
    if result_raw is None or getattr(result_raw, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        result = {"error": str(mt5.last_error()), "retcode": getattr(result_raw, "retcode", None)}
        _debug("=== MT5 RESPONSE === close_position FAILED", result)
        return result

    result = {
        "ticket":  ticket,
        "deal":    int(getattr(result_raw, "deal", 0)),
        "volume":  close_volume,
        "price":   float(getattr(result_raw, "price", 0)),
        "status":  "closed",
        "source":  "mt5",
    }
    _debug("=== MT5 RESPONSE === close_position OK", result)
    return result


def cancel_order(ticket: int) -> dict:
    """Cancel a pending MT5 order by ticket number."""
    err = _ensure_connected()
    if err:
        return err

    mt5 = _get_mt5()
    _debug("=== MT5 REQUEST === cancel_order", {"ticket": ticket})

    request = {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket}
    result_raw = mt5.order_send(request)
    if result_raw is None or getattr(result_raw, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        result = {"error": str(mt5.last_error())}
        _debug("=== MT5 RESPONSE === cancel_order FAILED", result)
        return result

    result = {"ticket": ticket, "status": "cancelled"}
    _debug("=== MT5 RESPONSE === cancel_order OK", result)
    return result
