"""
Pluggable Senses: multi-broker connectivity (Alpaca, MetaTrader 5).
All connectors implement BaseConnector for unified data and execution.
"""
from .base_connector import BaseConnector
from .connector_factory import get_connector
from .exceptions import (
    AuthenticationError,
    BrokerConnectionError,
    ConnectorError,
    InsufficientLiquidityError,
)

__all__ = [
    "BaseConnector",
    "get_connector",
    "ConnectorError",
    "BrokerConnectionError",
    "InsufficientLiquidityError",
    "AuthenticationError",
]
