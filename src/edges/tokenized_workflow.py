"""Tokenized assets workflow (stub until CoinGecko connector)."""
from typing import Any, Dict
import pandas as pd
from .base_workflow import BaseEdgeWorkflow
from .tokenized_assets import detect_arb


class TokenizedWorkflow(BaseEdgeWorkflow):
    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        return pd.DataFrame()

    def run_models(self, state: Any) -> Any:
        result = detect_arb(state if isinstance(state, pd.DataFrame) else None)
        return {"result": result, "returns": pd.Series(dtype=float)}

    def validate(self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0) -> tuple[bool, Dict[str, Any]]:
        return False, {"reason": "Tokenized workflow requires CoinGecko connector"}


def run_tokenized_edge() -> tuple[bool, Dict[str, Any]]:
    w = TokenizedWorkflow()
    return False, {"reason": "Tokenized edge stub; add coingecko_connector"}
