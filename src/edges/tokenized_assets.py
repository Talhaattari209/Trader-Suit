"""Tokenized asset edge: discrepancy detection (stub for CoinGecko)."""
import pandas as pd
from typing import Dict, Any

def detect_arb(prices_df: pd.DataFrame, threshold: float = 0.01) -> Dict[str, Any]:
    """Detect cross-asset price discrepancies. Stub without CoinGecko."""
    if prices_df is None or prices_df.empty:
        return {"opportunities": [], "spread": None}
    return {"opportunities": [], "spread": None}
