"""Geopolitical edge workflow (stub until Polygon EM/X data)."""
import os
from typing import Any, Dict
import pandas as pd
from .base_workflow import BaseEdgeWorkflow


class GeoWorkflow(BaseEdgeWorkflow):
    def __init__(self, csv_path: str | None = None):
        self.csv_path = csv_path or os.environ.get("US30_CSV_PATH", "")

    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        if self.csv_path and __import__("os").path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().capitalize() for c in df.columns]
            if "Close" in df.columns:
                df["returns"] = df["Close"].pct_change().fillna(0)
            return df
        return pd.DataFrame()

    def run_models(self, state: Any) -> Any:
        if isinstance(state, pd.DataFrame) and not state.empty and "returns" in state.columns:
            return {"returns": state["returns"]}
        return {"returns": pd.Series(dtype=float)}

    def validate(self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0) -> tuple[bool, Dict[str, Any]]:
        if isinstance(signals_or_returns, dict):
            ret = signals_or_returns.get("returns")
            if ret is not None and len(ret) > 2:
                return super().validate(ret, data, initial_capital)
        return super().validate(signals_or_returns, data, initial_capital)


def run_geo_edge(csv_path: str | None = None) -> tuple[bool, Dict[str, Any]]:
    w = GeoWorkflow(csv_path=csv_path)
    data = w.get_data()
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return False, {"reason": "No data"}
    out = w.run_models(data)
    return w.validate(out, data, initial_capital=100000.0)
