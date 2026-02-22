"""
Base workflow interface for edge modules.
Each edge implements: get_data -> run_models -> validate -> execute.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd


class BaseEdgeWorkflow(ABC):
    """Abstract workflow: Perceive (data) -> Reason (models) -> Validate -> Execute."""

    @abstractmethod
    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        """Load and preprocess data. Return DataFrame or dict of data artifacts."""
        pass

    @abstractmethod
    def run_models(self, state: Any) -> Any:
        """Run ML/DL/RL models; return signals, weights, or strategy state."""
        pass

    def validate(
        self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Validate with Monte Carlo / risk metrics.
        Return (approved: bool, metrics: dict).
        Override for edge-specific validation.
        """
        try:
            from src.tools.monte_carlo_pro import MonteCarloPro
        except ImportError:
            try:
                from ...tools.monte_carlo_pro import MonteCarloPro
            except ImportError:
                return True, {}
        if isinstance(signals_or_returns, pd.Series):
            returns = signals_or_returns
        else:
            returns = pd.Series(signals_or_returns) if signals_or_returns is not None else pd.Series()
        if len(returns) < 2:
            return False, {"reason": "Insufficient returns"}
        mc = MonteCarloPro(iterations=5000)
        friction = mc.inject_execution_friction(returns, slippage_pct=0.0002)
        sim = mc.simulate_paths(friction, initial_capital=initial_capital)
        approved = sim["prob_of_ruin"] < 0.05
        return approved, {
            "prob_of_ruin": sim["prob_of_ruin"],
            "var_95": sim["var_95"],
            "expected_shortfall": sim["expected_shortfall"],
        }

    def execute(
        self, signals_or_weights: Any, connector: Optional[Any] = None
    ) -> None:
        """
        Execute trades via connector. Override for live execution.
        """
        if connector is not None:
            pass  # Subclass implements actual order placement
        return None
