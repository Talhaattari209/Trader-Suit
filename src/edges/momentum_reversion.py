"""Momentum/mean reversion edge (LSTM/ARIMA stub)."""
import pandas as pd
import numpy as np
from typing import Optional

def forecast_next_return(series: pd.Series) -> float:
    return 0.0 if series is None or len(series) == 0 else float(series.iloc[-1] * 0.01)
