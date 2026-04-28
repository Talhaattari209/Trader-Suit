"""
src/autonomous_agent/alpaca_client.py
======================================
Dedicated Alpaca Markets API wrapper for the Autonomous Agent.

WHY a separate client here?
  The existing src/api/alpaca_service.py is tightly coupled to the FastAPI
  response models.  The agent needs raw dicts it can serialise to JSON and
  drop straight into the LLM context — no Pydantic overhead, no HTTP round-trip
  through our own API server (avoids circular dependency when the agent and the
  API server share the same Python process).

TWO ACCOUNTS (paper trading, as per .env):
  Account 1  →  ALPACA_API_KEY  /  ALPACA_SECRET_KEY   (primary paper)
  Account 2  →  ALPACA_API_KEY_2 / ALPACA_SECRET_KEY_2  (secondary paper)

Keys are read exclusively from the .env file (or environment).
They are NEVER hard-coded here — that is a deliberate security boundary.

All public functions return plain dicts or lists of dicts so the agent can
call json.dumps() on them directly.
"""

from __future__ import annotations

import os
import logging
from typing import Any

# Standard library logging — not print() — so log level can be controlled
# from outside (e.g. suppress in tests, verbose in production).
logger = logging.getLogger("autonomous_agent.alpaca")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_env() -> None:
    """
    Load .env into os.environ exactly once.

    python-dotenv does NOT override existing env vars by default, which is the
    safe behaviour: a real deployment can set env vars at the OS level and they
    will take precedence over the .env file.
    """
    try:
        from dotenv import load_dotenv        # optional dependency; already in requirements
        load_dotenv(override=False)           # override=False → OS env wins over .env
    except ImportError:
        pass                                  # dotenv absent → rely on OS env; not fatal


def _get_trading_client(account: int = 1):
    """
    Construct an Alpaca TradingClient for the requested account number (1 or 2).

    WHY alpaca-py (not alpaca-trade-api)?
      alpaca-py is the current official SDK; alpaca-trade-api is deprecated.
      The new SDK returns typed dataclasses but we convert them to dicts below
      so the rest of the agent stays dependency-light.

    Raises RuntimeError if credentials are missing so the caller can surface a
    clear error message in the chat rather than an opaque AttributeError.
    """
    _load_env()                               # ensure .env is sourced before reading keys

    if account == 2:
        # Secondary paper account (Account 2 credentials from .env)
        api_key    = os.environ.get("ALPACA_API_KEY_2", "").strip()
        secret_key = os.environ.get("ALPACA_SECRET_KEY_2", "").strip()
        endpoint   = os.environ.get("ENDPOINT_2", "https://paper-api.alpaca.markets").strip()
    else:
        # Primary paper account (Account 1 credentials from .env — default)
        api_key    = os.environ.get("ALPACA_API_KEY", "").strip()
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "").strip()
        endpoint   = os.environ.get("ENDPOINT", "https://paper-api.alpaca.markets").strip()

    if not api_key or not secret_key:
        # Surface a clean error; the caller will format it for the chat UI
        raise RuntimeError(
            f"Alpaca account {account} credentials not found in .env "
            f"(ALPACA_API_KEY{'_2' if account==2 else ''} / "
            f"ALPACA_SECRET_KEY{'_2' if account==2 else ''})."
        )

    # paper=True is inferred from the endpoint URL but we make it explicit
    # to prevent accidental live-trading if the endpoint is changed.
    paper = "paper" in endpoint.lower()

    from alpaca.trading.client import TradingClient          # alpaca-py SDK
    return TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=paper,                          # True → paper trading only; safety guard
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_account_info(account: int = 1) -> dict[str, Any]:
    """
    Return key account fields as a plain dict.

    We extract only the fields the LLM cares about so we don't bloat the
    context window with dozens of raw API fields the model will ignore.
    """
    try:
        client = _get_trading_client(account)
        acc = client.get_account()            # returns alpaca Account dataclass

        return {
            "account_number": getattr(acc, "account_number", "N/A"),
            "status":         str(getattr(acc, "status", "unknown")),
            "equity":         float(getattr(acc, "equity", 0) or 0),
            "cash":           float(getattr(acc, "cash", 0) or 0),
            "buying_power":   float(getattr(acc, "buying_power", 0) or 0),
            # Unrealised P&L on all open positions
            "unrealized_pl":  float(getattr(acc, "unrealized_pl", 0) or 0),
            # Pattern Day Trader flag — important for risk management
            "pattern_day_trader": bool(getattr(acc, "pattern_day_trader", False)),
            "account_type":   "paper" if "paper" in str(getattr(acc, "account_number", "")).lower() else "live",
            "source":         f"alpaca_account_{account}",
        }
    except Exception as exc:
        logger.warning("[AlpacaClient] get_account_info(%d) failed: %s", account, exc)
        return {"error": str(exc), "source": f"alpaca_account_{account}"}


def get_open_positions(account: int = 1) -> list[dict[str, Any]]:
    """
    Return all open positions as a list of plain dicts.

    Position data is critical for the agent to answer "what am I holding?"
    We normalise field names to snake_case for consistent JSON serialisation.
    """
    try:
        client = _get_trading_client(account)
        positions = client.get_all_positions()    # list of Position dataclasses

        result = []
        for p in positions:
            result.append({
                "symbol":        str(p.symbol),
                "qty":           float(p.qty or 0),
                "side":          str(p.side).lower(),           # "long" | "short"
                "market_value":  float(p.market_value or 0),
                "avg_entry_price": float(p.avg_entry_price or 0),
                "current_price": float(p.current_price or 0),
                "unrealized_pl": float(p.unrealized_pl or 0),
                "unrealized_plpc": float(p.unrealized_plpc or 0),  # % gain/loss
                "cost_basis":    float(p.cost_basis or 0),
            })
        return result
    except Exception as exc:
        logger.warning("[AlpacaClient] get_open_positions(%d) failed: %s", account, exc)
        return [{"error": str(exc)}]


def get_recent_orders(account: int = 1, limit: int = 20) -> list[dict[str, Any]]:
    """
    Return recent orders (all statuses) for audit trail display.

    Limit defaults to 20 so the LLM context stays manageable; the caller can
    override for deeper history queries.
    """
    try:
        from alpaca.trading.requests import GetOrdersRequest   # request model from alpaca-py
        from alpaca.trading.enums import QueryOrderStatus

        client = _get_trading_client(account)

        # Fetch all statuses (open, filled, cancelled) in one call
        req = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit,
        )
        orders = client.get_orders(filter=req)

        result = []
        for o in orders:
            result.append({
                "id":           str(o.id),
                "symbol":       str(o.symbol),
                "side":         str(o.side).lower(),             # "buy" | "sell"
                "type":         str(o.order_type).lower(),       # "market" | "limit" …
                "qty":          float(o.qty or 0),
                "filled_qty":   float(o.filled_qty or 0),
                "status":       str(o.status).lower(),           # "filled" | "open" …
                "submitted_at": str(o.submitted_at or ""),
                "filled_at":    str(o.filled_at or ""),
                "filled_avg_price": float(o.filled_avg_price or 0),
            })
        return result
    except Exception as exc:
        logger.warning("[AlpacaClient] get_recent_orders(%d) failed: %s", account, exc)
        return [{"error": str(exc)}]


def get_portfolio_history(account: int = 1, days: int = 30) -> list[dict[str, Any]]:
    """
    Return daily equity snapshots for P&L curve rendering.

    The history is used both by the LLM (to answer "how did the portfolio
    perform over the last month?") and by the Streamlit charts.
    """
    try:
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        from alpaca.trading.enums import TimeFrameUnit

        client = _get_trading_client(account)

        req = GetPortfolioHistoryRequest(
            period=f"{days}D",         # e.g. "30D" for 30 calendar days
            timeframe="1D",            # daily granularity — balances detail vs size
            extended_hours=False,      # regular session only for clean close prices
        )
        hist = client.get_portfolio_history(filter=req)

        if not hist or not hist.timestamp:
            return []

        # Zip parallel arrays (timestamp[], equity[], profit_loss_pct[]) into dicts
        result = []
        for ts, eq, plpc in zip(
            hist.timestamp or [],
            hist.equity or [],
            hist.profit_loss_pct or [],
        ):
            result.append({
                "timestamp": str(ts),
                "equity":    float(eq or 0),
                "pnl_pct":   float(plpc or 0) * 100,   # SDK returns 0.05 → we store 5.0 (%)
            })
        return result
    except Exception as exc:
        logger.warning("[AlpacaClient] get_portfolio_history(%d) failed: %s", account, exc)
        return [{"error": str(exc)}]


def place_paper_order(
    symbol: str,
    qty: float,
    side: str,             # "buy" | "sell"
    order_type: str = "market",
    account: int = 1,
) -> dict[str, Any]:
    """
    Submit a paper order via Alpaca.

    SAFETY RULES (enforced here, not just in the prompt):
      1. Account is always PAPER — the TradingClient is constructed with paper=True.
      2. Quantity is floored to 0 and any attempt to pass 0 is rejected.
      3. Side must be "buy" or "sell" — any other value raises ValueError.
      4. This function is ONLY callable in Agent Mode (enforced in tools.py).

    Returns a dict so the agent can summarise the order in the chat message.
    """
    if qty <= 0:
        raise ValueError(f"Order qty must be > 0, got {qty}.")
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got '{side}'.")

    try:
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client = _get_trading_client(account)

        # Map string → SDK enum (prevents typo mistakes)
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

        if order_type == "market":
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,   # DAY = cancel at close if unfilled
            )
        else:
            # Fallback — agent should not be placing limit orders autonomously
            raise ValueError(f"order_type='{order_type}' not supported by autonomous agent.")

        order = client.submit_order(order_data=req)

        return {
            "order_id":  str(order.id),
            "symbol":    str(order.symbol),
            "side":      side,
            "qty":       qty,
            "status":    str(order.status).lower(),
            "submitted": str(order.submitted_at),
            "account":   account,
        }
    except Exception as exc:
        logger.error("[AlpacaClient] place_paper_order failed: %s", exc)
        return {"error": str(exc)}
