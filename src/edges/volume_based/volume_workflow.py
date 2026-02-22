"""Volume-based edge workflow."""
import os
from typing import Any, Dict

import pandas as pd

try:
    from src.edges.base_workflow import BaseEdgeWorkflow
except ImportError:
    from ..base_workflow import BaseEdgeWorkflow

try:
    from src.data.volume_loader import load_volume_data, preprocess_volume_data
except ImportError:
    from ...data.volume_loader import load_volume_data, preprocess_volume_data

from .volume_analyzer import train_volume_classifier
from .volume_rl_agent import train_rl_volume


class VolumeWorkflow(BaseEdgeWorkflow):
    def __init__(self, csv_path: str | None = None):
        self.csv_path = csv_path or os.environ.get("US30_CSV_PATH", "")

    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        df = load_volume_data(file_path=self.csv_path)
        if df.empty:
            return pd.DataFrame()
        processed, _, _ = preprocess_volume_data(df)
        processed["returns"] = df["Close"].reindex(processed.index).pct_change().fillna(0) if "Close" in df.columns else 0.0
        return processed

    def run_models(self, state: Any) -> Any:
        if isinstance(state, pd.DataFrame) and state.empty:
            return None
        df = state
        rf, acc, prec, _ = train_volume_classifier(df)
        rl_model = train_rl_volume(df)
        returns = df["returns"] if isinstance(df, pd.DataFrame) and "returns" in df.columns else pd.Series(0.0, index=range(len(df)))
        return {"rf": rf, "rl_model": rl_model, "accuracy": acc, "returns": returns}

    def validate(
        self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0
    ) -> tuple[bool, Dict[str, Any]]:
        if isinstance(signals_or_returns, dict):
            ret = signals_or_returns.get("returns")
            if ret is not None and len(ret) > 2:
                return super().validate(ret, data, initial_capital)
        return super().validate(signals_or_returns, data, initial_capital)


def run_volume_edge(csv_path: str | None = None) -> tuple[bool, Dict[str, Any]]:
    w = VolumeWorkflow(csv_path=csv_path)
    data = w.get_data()
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return False, {"reason": "No data"}
    out = w.run_models(data)
    if out is None:
        return False, {"reason": "Models failed"}
    return w.validate(out, data, initial_capital=100000.0)
