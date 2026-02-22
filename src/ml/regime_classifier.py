"""Regime detection via Hurst exponent and Random Forest."""
import numpy as np
import pandas as pd
from typing import Optional

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def compute_hurst(series: pd.Series, window: int = 100) -> float:
    if len(series) < window:
        return 0.5
    lags = range(2, min(window, len(series) // 2))
    tau = [np.std(np.subtract(series.values[lag:], series.values[:-lag])) for lag in lags]
    if not tau or len(tau) < 2:
        return 0.5
    poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return float(poly[0])


def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
    if not HAS_SKLEARN or "Close" not in df.columns or len(df) < 150:
        df = df.copy()
        df["regime"] = 0
        return df
    df = df.copy()
    df["hurst"] = df["Close"].rolling(100).apply(lambda x: compute_hurst(pd.Series(x)), raw=False)
    df["volatility"] = df["Close"].pct_change().rolling(20).std().fillna(0)
    df["returns"] = df["Close"].pct_change().fillna(0)
    feats = df[["hurst", "volatility"]].fillna(0)
    labels = (feats["hurst"] > 0.5).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(feats, labels, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)
    df["regime"] = clf.predict(feats)
    return df
