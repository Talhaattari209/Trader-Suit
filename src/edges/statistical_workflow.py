"""
Statistical edge workflow: data -> models -> validate -> execute.
"""
import os
from typing import Any, Dict

import pandas as pd

from .base_workflow import BaseEdgeWorkflow
from .statistical_edges import StatisticalModels, pairs_trading_signals

try:
    from src.data.preprocessor import load_and_preprocess_data
except ImportError:
    load_and_preprocess_data = None


class StatisticalWorkflow(BaseEdgeWorkflow):
    def __init__(
        self,
        csv_path: str | None = None,
        assets: list | None = None,
    ):
        self.csv_path = csv_path or os.environ.get("US30_CSV_PATH", "")
        self.assets = assets or ["US30"]

    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        if load_and_preprocess_data and self.csv_path and os.path.exists(self.csv_path):
            reduced, _ = load_and_preprocess_data(
                self.csv_path, assets=self.assets, n_components=0.95
            )
            if not reduced.empty:
                return reduced
        # Fallback: raw CSV
        if self.csv_path and os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().capitalize() for c in df.columns]
            if "Close" in df.columns:
                df["returns"] = df["Close"].pct_change().fillna(0)
            return df.fillna(0)
        return pd.DataFrame()

    def run_models(self, state: Any) -> Any:
        if isinstance(state, pd.DataFrame) and state.empty:
            return None
        data = state if isinstance(state, pd.DataFrame) else state.get("data")
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return None
        models = StatisticalModels(data)
        models.unsupervised_clustering(n_clusters=5)
        _, _, preds, mse = models.supervised_prediction("returns")
        # Pairs signals if we have multiple columns
        pair_returns = None
        if isinstance(data, pd.DataFrame) and len(data.columns) >= 2:
            pair_returns = pairs_trading_signals(data, threshold=2.0)
        return {
            "models": models,
            "predictions": preds,
            "pair_returns": pair_returns,
            "mse": mse,
        }

    def validate(
        self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0
    ) -> tuple[bool, Dict[str, Any]]:
        if isinstance(signals_or_returns, dict):
            pr = signals_or_returns.get("pair_returns")
            if pr is not None and len(pr) > 2:
                return super().validate(pr, data, initial_capital)
        return super().validate(signals_or_returns, data, initial_capital)


def run_statistical_workflow(
    csv_path: str | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """One-shot: get data, run models, validate. Returns (approved, metrics)."""
    w = StatisticalWorkflow(csv_path=csv_path)
    data = w.get_data()
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return False, {"reason": "No data"}
    out = w.run_models(data)
    if out is None:
        return False, {"reason": "Models failed"}
    returns = out.get("pair_returns")
    if returns is None:
        returns = pd.Series(out.get("predictions", []))
    return w.validate(returns, data, initial_capital=100000.0)
