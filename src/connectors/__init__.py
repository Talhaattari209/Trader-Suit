"""
Pluggable Senses: multi-broker connectivity (Alpaca, MetaTrader 5).
All connectors implement BaseConnector for unified data and execution.
Advanced: CacheManager, ExecutionManager for production-grade architecture.
"""
from .base_connector import BaseConnector
from .cache_manager import CacheManager
from .connector_factory import get_connector
from .exceptions import (
    AuthenticationError,
    BrokerConnectionError,
    ConnectorError,
    InsufficientLiquidityError,
)
from .execution_manager import ExecutionManager

__all__ = [
    "BaseConnector",
    "CacheManager",
    "ExecutionManager",
    "get_connector",
    "ConnectorError",
    "BrokerConnectionError",
    "InsufficientLiquidityError",
    "AuthenticationError",
]
