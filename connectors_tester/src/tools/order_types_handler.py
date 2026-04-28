"""
connectors_tester/src/tools/order_types_handler.py
====================================================
Centralised order-type catalogue and validation for every supported broker.

WHY a separate module?
  The Streamlit form, the autonomous agent, and the connector wrappers all
  need to know which order types are valid for a given broker — and what
  required/optional fields each type needs.  Centralising this avoids
  duplication and ensures the UI and the execution layer are always in sync.

USAGE:
    from src.tools.order_types_handler import (
        get_order_types,    # returns list of valid type strings for a broker
        validate_order,     # raises ValueError with a clear message if invalid
        required_fields,    # returns dict of {field: description} for a type
        ORDER_CATALOGUE,    # full catalogue for inspection
    )
"""

from __future__ import annotations

from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Order Type Catalogues
# ─────────────────────────────────────────────────────────────────────────────

# Each entry describes one order type:
#   "display"    : human-readable label for the UI dropdown
#   "required"   : fields the user MUST supply
#   "optional"   : fields the user MAY supply
#   "description": one-line explanation for the agent prompt

ALPACA_ORDER_TYPES: dict[str, dict] = {
    "market": {
        "display":     "Market",
        "required":    ["symbol", "side", "qty"],
        "optional":    ["time_in_force", "take_profit", "stop_loss"],
        "description": "Fill immediately at the best available market price.",
    },
    "limit": {
        "display":     "Limit",
        "required":    ["symbol", "side", "qty", "limit_price"],
        "optional":    ["time_in_force", "take_profit", "stop_loss"],
        "description": "Fill at limit_price or better.  Rests in the book if price not met.",
    },
    "stop": {
        "display":     "Stop",
        "required":    ["symbol", "side", "qty", "stop_price"],
        "optional":    ["time_in_force"],
        "description": "Becomes a market order when price reaches stop_price.",
    },
    "stop_limit": {
        "display":     "Stop-Limit",
        "required":    ["symbol", "side", "qty", "stop_price", "limit_price"],
        "optional":    ["time_in_force"],
        "description": "Becomes a limit order (at limit_price) when stop_price is triggered.",
    },
    "trailing_stop": {
        "display":     "Trailing Stop",
        "required":    ["symbol", "side", "qty"],
        "optional":    ["trail_price", "trail_percent", "time_in_force"],
        "description": (
            "Stop that moves with the market by trail_price (absolute) "
            "or trail_percent (%).  Locks in profit as price moves favorably."
        ),
    },
}

# Time-in-force options for Alpaca
ALPACA_TIF: list[str] = ["day", "gtc", "opg", "cls", "ioc", "fok"]

# MT5 order types — split into market and pending for clarity
MT5_ORDER_TYPES: dict[str, dict] = {
    "buy": {
        "display":     "Market Buy",
        "required":    ["symbol", "volume"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Instant execution buy at current ask price.",
    },
    "sell": {
        "display":     "Market Sell",
        "required":    ["symbol", "volume"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Instant execution sell at current bid price.",
    },
    "buy_limit": {
        "display":     "Buy Limit",
        "required":    ["symbol", "volume", "price"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Buy when price drops to price (price < current ask).",
    },
    "sell_limit": {
        "display":     "Sell Limit",
        "required":    ["symbol", "volume", "price"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Sell when price rises to price (price > current bid).",
    },
    "buy_stop": {
        "display":     "Buy Stop",
        "required":    ["symbol", "volume", "price"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Buy when price rises to price (price > current ask).",
    },
    "sell_stop": {
        "display":     "Sell Stop",
        "required":    ["symbol", "volume", "price"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": "Sell when price drops to price (price < current bid).",
    },
    "buy_stop_limit": {
        "display":     "Buy Stop-Limit",
        "required":    ["symbol", "volume", "price", "price_stoplimit"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": (
            "Buy stop that becomes a buy limit when price reaches price. "
            "price_stoplimit is the limit price for subsequent execution."
        ),
    },
    "sell_stop_limit": {
        "display":     "Sell Stop-Limit",
        "required":    ["symbol", "volume", "price", "price_stoplimit"],
        "optional":    ["sl", "tp", "comment", "magic"],
        "description": (
            "Sell stop that becomes a sell limit when price reaches price. "
            "price_stoplimit is the limit price for subsequent execution."
        ),
    },
}

# Master catalogue — keyed by broker name
ORDER_CATALOGUE: dict[str, dict] = {
    "alpaca_1": ALPACA_ORDER_TYPES,
    "alpaca_2": ALPACA_ORDER_TYPES,   # same types for both Alpaca accounts
    "mt5":      MT5_ORDER_TYPES,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_order_types(broker: str) -> list[str]:
    """
    Return the list of valid order type strings for a given broker.

    Used by the Streamlit dropdown to populate the order type selector.
    Returns an empty list for unknown brokers so the UI can display a warning.
    """
    catalogue = ORDER_CATALOGUE.get(broker, {})
    return list(catalogue.keys())


def get_order_type_labels(broker: str) -> dict[str, str]:
    """
    Return a dict of {type_string: display_label} for the broker.

    Used to render human-friendly names in the UI dropdown.
    """
    catalogue = ORDER_CATALOGUE.get(broker, {})
    return {k: v["display"] for k, v in catalogue.items()}


def required_fields(broker: str, order_type: str) -> list[str]:
    """Return the list of required field names for a specific order type."""
    catalogue = ORDER_CATALOGUE.get(broker, {})
    entry     = catalogue.get(order_type, {})
    return entry.get("required", [])


def optional_fields(broker: str, order_type: str) -> list[str]:
    """Return the list of optional field names for a specific order type."""
    catalogue = ORDER_CATALOGUE.get(broker, {})
    entry     = catalogue.get(order_type, {})
    return entry.get("optional", [])


def describe_order_type(broker: str, order_type: str) -> str:
    """Return a one-line description of the order type for the given broker."""
    catalogue = ORDER_CATALOGUE.get(broker, {})
    entry     = catalogue.get(order_type, {})
    return entry.get("description", "")


def validate_order(broker: str, order_type: str, params: dict[str, Any]) -> None:
    """
    Validate an order parameter dict against the catalogue for the given broker.

    Raises ValueError with a clear, actionable message if:
      - broker is unknown
      - order_type is not valid for the broker
      - a required field is missing or None

    Does NOT raise for optional fields — the caller supplies them or not.
    """
    catalogue = ORDER_CATALOGUE.get(broker)
    if catalogue is None:
        valid_brokers = list(ORDER_CATALOGUE.keys())
        raise ValueError(
            f"Unknown broker '{broker}'.  Valid brokers: {valid_brokers}"
        )

    type_entry = catalogue.get(order_type)
    if type_entry is None:
        valid_types = list(catalogue.keys())
        raise ValueError(
            f"'{order_type}' is not a valid order type for broker '{broker}'.  "
            f"Valid types: {valid_types}"
        )

    # Check every required field is present and non-None
    missing = [
        field for field in type_entry["required"]
        if field not in params or params[field] is None
    ]
    if missing:
        raise ValueError(
            f"Missing required field(s) for {broker}/{order_type}: {missing}.  "
            f"Required: {type_entry['required']}"
        )

    # Specific cross-field checks
    if order_type == "trailing_stop":
        trail_p = params.get("trail_price")
        trail_pc = params.get("trail_percent")
        if trail_p is None and trail_pc is None:
            raise ValueError(
                "trailing_stop requires either 'trail_price' (absolute) "
                "or 'trail_percent' (percentage) — neither was provided."
            )

    if broker in ("alpaca_1", "alpaca_2"):
        side = str(params.get("side", "")).lower()
        if side not in ("buy", "sell"):
            raise ValueError(f"'side' must be 'buy' or 'sell', got: '{side}'")
        qty = params.get("qty")
        if qty is not None and float(qty) <= 0:
            raise ValueError(f"'qty' must be > 0, got: {qty}")

    if broker == "mt5":
        volume = params.get("volume")
        if volume is not None and float(volume) <= 0:
            raise ValueError(f"'volume' must be > 0, got: {volume}")


def order_types_for_agent_prompt(broker: str) -> str:
    """
    Render a compact description of all order types for the agent's system prompt.

    The agent calls this to know what order types and fields are available
    for the currently selected broker — without needing to hard-code them.
    """
    catalogue = ORDER_CATALOGUE.get(broker, {})
    if not catalogue:
        return f"No order types registered for broker '{broker}'."

    lines = [f"Supported order types for {broker}:"]
    for ot, entry in catalogue.items():
        req = ", ".join(entry["required"])
        opt = ", ".join(entry.get("optional", []))
        lines.append(
            f"  {ot:20s} — {entry['description']}\n"
            f"    required: {req}"
            + (f"\n    optional: {opt}" if opt else "")
        )
    return "\n".join(lines)
