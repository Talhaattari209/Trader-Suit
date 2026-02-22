"""AI-enhanced edge workflow dispatcher (sentiment, factor, momentum, hybrid)."""
import os
from typing import Any, Dict

import pandas as pd
from .base_workflow import BaseEdgeWorkflow
from .factor_mining import mine_factors
from .momentum_reversion import forecast_next_return

try:
    from src.data.us30_loader import US30Loader
except ImportError:
    US30Loader = None


class AIEnhancedWorkflow(BaseEdgeWorkflow):
    def __init__(self, csv_path: str | None = None):
        self.csv_path = csv_path or os.environ.get("US30_CSV_PATH", "")

    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        if US30Loader and self.csv_path and os.path.exists(self.csv_path):
            loader = US30Loader(self.csv_path)
            df = loader.load_clean_data()
        elif self.csv_path and os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().capitalize() for c in df.columns]
            if "Close" in df.columns:
                df["returns"] = df["Close"].pct_change().fillna(0)
            return df
        return pd.DataFrame()

    def run_models(self, state: Any) -> Any:
        if isinstance(state, pd.DataFrame) and state.empty:
            return None
        df = state
        if "returns" not in df.columns:
            df["returns"] = df["Close"].pct_change().fillna(0) if "Close" in df.columns else 0.0
        factors = mine_factors(df, target="returns")
        pred = forecast_next_return(df["returns"] if "returns" in df.columns else pd.Series())
        return {"factors": factors, "prediction": pred, "returns": df["returns"]}

    def validate(self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0) -> tuple[bool, Dict[str, Any]]:
        if isinstance(signals_or_returns, dict):
            ret = signals_or_returns.get("returns")
            if ret is not None and len(ret) > 2:
                return super().validate(ret, data, initial_capital)
        return super().validate(signals_or_returns, data, initial_capital)


def run_ai_enhanced_edge(csv_path: str | None = None) -> tuple[bool, Dict[str, Any]]:
    w = AIEnhancedWorkflow(csv_path=csv_path)
    data = w.get_data()
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return False, {"reason": "No data"}
    out = w.run_models(data)
    if out is None:
        return False, {"reason": "Models failed"}
    return w.validate(out, data, initial_capital=100000.0)
