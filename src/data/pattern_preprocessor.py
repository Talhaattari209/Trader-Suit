"""Pattern-based edge: OHLCV preprocess and chart-to-image for CNN."""
import numpy as np
import pandas as pd
from typing import Dict

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def preprocess_ohlcv(
    df: pd.DataFrame, window_size: int = 60
) -> Dict[str, np.ndarray | pd.DataFrame]:
    """Normalize OHLCV, optional PCA, return scaled/reduced dict. No image for speed."""
    if df.empty or len(df) < window_size:
        return {"scaled": np.array([]), "reduced": np.array([])}
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    if not cols:
        return {"scaled": np.array([]), "reduced": np.array([])}
    X = df[cols].fillna(0)
    if HAS_SKLEARN:
        scaler = MinMaxScaler()
        scaled = scaler.fit_transform(X)
        pca = PCA(n_components=0.95)
        reduced = pca.fit_transform(scaled)
        return {"scaled": scaled, "reduced": reduced, "df": df}
    return {"scaled": X.values, "reduced": X.values, "df": df}
