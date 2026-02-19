"""
Base strategy contract for executable trading strategies.
Strategist-generated code implements these methods; Killer Agent validates backtest results.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseStrategy(ABC):
    """
    Algorithmic strategy interface. Subclasses must implement entry, exit, and risk.
    Used by the Strategist Agent to generate strategy_<name>.py in src/models/drafts/.
    """

    @abstractmethod
    def entry(self, state: Dict[str, Any]) -> bool:
        """
        True if the strategy signals an entry (e.g. go long/short) given current state.
        state typically contains: Open, High, Low, Close, Volume, and optional indicators.
        """
        pass

    @abstractmethod
    def exit(self, state: Dict[str, Any]) -> bool:
        """
        True if the strategy signals an exit (close position) given current state.
        """
        pass

    @abstractmethod
    def risk(self, state: Dict[str, Any]) -> float:
        """
        Position size or risk amount for the current bar (e.g. fraction of capital, or 0).
        """
        pass
