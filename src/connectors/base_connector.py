"""
Unified connector interface (Pluggable Senses).
All brokers (MT5, Alpaca) implement this base to ensure the Actor/Critic can swap brokers without code changes.
"""
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseConnector(ABC):
    """
    Abstract base for financial data and execution connectors.
    No trading logic—only translation of broker-specific APIs into a standardized internal format.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Initialize session and authenticate. Returns True on success."""
        pass

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        Fetch historical data in standardized OHLCV format.
        Returns DataFrame with columns: Open, High, Low, Close, Volume; index = Timestamp (datetime).
        """
        pass

    @abstractmethod
    def execute_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str,
        **kwargs: Any,
    ) -> dict:
        """
        Standardized order execution (e.g. 'market' or 'limit').
        Returns dict with at least: status ('success' | 'rejected' | 'error'), order_id (if success), message (if error).
        """
        pass

    @abstractmethod
    def get_account_state(self) -> dict:
        """Returns Balance, Equity, and current drawdown/margin info."""
        pass
