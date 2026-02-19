"""
Connector factory: initializes the correct broker connector from environment (BROKER_TYPE).
Handles OS-specific imports: MT5 is Windows-only; on Linux/WSL we fail gracefully and document the bridge option.
"""
import logging
import os
import sys
from typing import Optional

from .base_connector import BaseConnector
from .exceptions import BrokerConnectionError

logger = logging.getLogger(__name__)

# Canonical env key for broker selection
BROKER_TYPE_ENV = "BROKER_TYPE"
# Supported values
BROKER_ALPACA = "alpaca"
BROKER_MT5 = "mt5"


def _is_wsl_or_linux() -> bool:
    """True if running under WSL2 or Linux (MT5 is not available natively)."""
    if sys.platform == "linux":
        return True
    # WSL2 often reports linux; sometimes we can detect via env
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    return False


def _get_alpaca_connector() -> Optional["BaseConnector"]:
    """Conditional import and build of AlpacaConnector."""
    try:
        from .alpaca_connector import AlpacaConnector

        return AlpacaConnector()
    except Exception as e:
        logger.warning("Alpaca connector not available: %s", e)
        return None


def _get_mt5_connector() -> Optional["BaseConnector"]:
    """
    MT5 is Windows-only. On WSL2/Linux, return None and log instructions for a Windows Bridge.
    """
    if _is_wsl_or_linux():
        logger.warning(
            "MT5 connector is Windows-native and cannot run directly in WSL2/Linux. "
            "For future use: run a lightweight REST or Socket bridge on the Windows host "
            "that talks to the MT5 terminal, and point this connector to that bridge."
        )
        return None

    try:
        from .mt5_connector import MT5Connector

        return MT5Connector()
    except ImportError as e:
        logger.warning("MT5 connector not available (MetaTrader5 package or init failed): %s", e)
        return None
    except Exception as e:
        logger.warning("MT5 connector failed to initialize: %s", e)
        return None


def get_connector(broker_type: Optional[str] = None) -> BaseConnector:
    """
    Factory: return the connector for the given broker type.
    If broker_type is None, uses env BROKER_TYPE (defaults to 'alpaca' if unset).
    Raises BrokerConnectionError if the requested connector is not available.
    """
    broker = (broker_type or os.environ.get(BROKER_TYPE_ENV) or BROKER_ALPACA).strip().lower()

    if broker == BROKER_ALPACA:
        conn = _get_alpaca_connector()
        if conn is None:
            raise BrokerConnectionError(
                "Alpaca connector could not be initialized. Check ALPACA_API_KEY and ALPACA_SECRET_KEY."
            )
        return conn

    if broker == BROKER_MT5:
        conn = _get_mt5_connector()
        if conn is None:
            raise BrokerConnectionError(
                "MT5 connector is not available. On Windows: ensure MetaTrader5 is installed and the terminal is running. "
                "On WSL2/Linux: use a Windows-hosted REST/Socket bridge to MT5 (see API_Connectors.md)."
            )
        return conn

    raise BrokerConnectionError(f"Unknown BROKER_TYPE: {broker}. Use 'alpaca' or 'mt5'.")
