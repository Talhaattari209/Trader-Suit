"""Pattern-based edge workflow."""
import os
from typing import Any, Dict

import numpy as np
import pandas as pd

try:
    from src.edges.base_workflow import BaseEdgeWorkflow
except ImportError:
    from ..base_workflow import BaseEdgeWorkflow

try:
    from src.data.us30_loader import US30Loader
except ImportError:
    US30Loader = None

try:
    from src.data.pattern_preprocessor import preprocess_ohlcv
except ImportError:
    from ...data.pattern_preprocessor import preprocess_ohlcv

from .pattern_detector_ml import ml_pattern_classifier, detect_pattern_ml
from .pattern_rl_agent import train_rl_pattern, execute_pattern_rl


class PatternWorkflow(BaseEdgeWorkflow):
    def __init__(self, csv_path: str | None = None):
        self.csv_path = csv_path or os.environ.get("US30_CSV_PATH", "")

    def get_data(self) -> pd.DataFrame | Dict[str, Any]:
        if US30Loader and self.csv_path and os.path.exists(self.csv_path):
            loader = US30Loader(self.csv_path)
            return loader.load_clean_data()
        if self.csv_path and os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().capitalize() for c in df.columns]
            if "Close" in df.columns:
                df["returns"] = df["Close"].pct_change().fillna(0)
            return df
        return pd.DataFrame()

    def run_models(self, state: Any) -> Any:
        if isinstance(state, pd.DataFrame) and state.empty:
            return None
        df = state if isinstance(state, pd.DataFrame) else state.get("data")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return None
        preprocessed = preprocess_ohlcv(df, window_size=60)
        if preprocessed.get("reduced") is None or len(preprocessed.get("reduced", [])) == 0:
            return None
        X = np.asarray(preprocessed["reduced"])
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        n = len(X)
        if "returns" in df.columns and len(df) >= n:
            y = (df["returns"].iloc[:n] > 0).astype(int).values
        else:
            y = np.zeros(n, dtype=int)
        if len(y) != n:
            y = np.zeros(n, dtype=int)
        rf = ml_pattern_classifier(X, y)
        rl_model = train_rl_pattern(df)
        return {"rf": rf, "rl_model": rl_model, "preprocessed": preprocessed, "df": df}

    def validate(
        self, signals_or_returns: Any, data: Any, initial_capital: float = 100000.0
    ) -> tuple[bool, Dict[str, Any]]:
        if isinstance(signals_or_returns, dict):
            df = signals_or_returns.get("df")
            if df is not None and "returns" in df.columns:
                return super().validate(df["returns"], data, initial_capital)
        return super().validate(signals_or_returns, data, initial_capital)


def run_pattern_edge(csv_path: str | None = None) -> tuple[bool, Dict[str, Any]]:
    w = PatternWorkflow(csv_path=csv_path)
    data = w.get_data()
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return False, {"reason": "No data"}
    out = w.run_models(data)
    if out is None:
        return False, {"reason": "Models failed"}
    return w.validate(out, data, initial_capital=100000.0)
