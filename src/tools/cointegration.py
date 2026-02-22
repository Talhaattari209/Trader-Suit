"""Cointegration and pairs-trading utilities."""
import numpy as np
import pandas as pd
from typing import Optional, Tuple

try:
    from statsmodels.tsa.stattools import coint
    HAS_COINT = True
except ImportError:
    HAS_COINT = False


def pairs_trading_test(
    asset1_data: pd.Series,
    asset2_data: pd.Series,
    threshold: float = 2.0,
) -> Optional[Tuple[np.ndarray, pd.Series]]:
    """
    Cointegration test for pairs. Returns (entry_signals, zscore) or None if not cointegrated.
    entry_signals: 1 = long spread, -1 = short spread, 0 = no trade.
    """
    if not HAS_COINT:
        return None
    if len(asset1_data) < 20 or len(asset2_data) < 20:
        return None
    common_idx = asset1_data.index.intersection(asset2_data.index)
    a1 = asset1_data.reindex(common_idx).ffill().dropna()
    a2 = asset2_data.reindex(common_idx).ffill().dropna()
    if len(a1) < 20:
        return None
    score, pvalue, _ = coint(a1, a2)
    if pvalue > 0.05:
        return None
    spread = a1 - a2
    zscore = (spread - spread.mean()) / (spread.std() or 1e-8)
    entry_signals = np.where(
        zscore > threshold, -1, np.where(zscore < -threshold, 1, 0)
    )
    return entry_signals, zscore
