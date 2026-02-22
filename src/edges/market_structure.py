"""Market structure: BOS, FVG, regime (Hurst)."""
import pandas as pd
import numpy as np
from typing import Dict, Any

try:
    from src.ml.regime_classifier import compute_hurst, classify_regime
except ImportError:
    from ...ml.regime_classifier import compute_hurst, classify_regime


def detect_swing_highs_lows(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    df = df.copy()
    if "High" in df.columns:
        df["swing_high"] = df["High"].rolling(window=window, center=True).max()
    if "Low" in df.columns:
        df["swing_low"] = df["Low"].rolling(window=window, center=True).min()
    return df


def structure_agent_result(df: pd.DataFrame) -> Dict[str, Any]:
    """Placeholder for LLM structure agent. Returns BOS/FVG flags."""
    if df is None or len(df) < 50:
        return {"bos": False, "fvg": [], "order_blocks": []}
    df = classify_regime(df)
    last = df.iloc[-1]
    bos = bool(last.get("regime", 0) == 1 and last.get("swing_high", 0) > 0)
    return {"bos": bos, "fvg": [], "order_blocks": []}
