"""Volume data loader and preprocess for volume-based edge."""
import pandas as pd
import numpy as np
from typing import Tuple, Optional

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import MinMaxScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def load_volume_data(
    symbol: str = "US30",
    file_path: Optional[str] = None,
    limit: int = 10000,
) -> pd.DataFrame:
    if file_path and __import__("os").path.exists(file_path):
        df = pd.read_csv(file_path)
        df.columns = [c.strip().capitalize() for c in df.columns]
        if "Timestamp" not in df.columns and "Time" in df.columns:
            df = df.rename(columns={"Time": "Timestamp"})
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            df.set_index("Timestamp", inplace=True)
        if "Volume" not in df.columns:
            df["Volume"] = 0
        df["volume_delta"] = df["Volume"].diff().fillna(0)
        df["avg_volume"] = df["Volume"].rolling(window=20).mean().fillna(df["Volume"])
        df["spike_ratio"] = (df["Volume"] / df["avg_volume"]).fillna(1.0)
        return df.dropna()
    return pd.DataFrame()


def preprocess_volume_data(
    df: pd.DataFrame, n_components: float = 0.95
) -> Tuple[pd.DataFrame, Optional[object], Optional[object]]:
    if df.empty or not HAS_SKLEARN:
        return df, None, None
    cols = [c for c in ["Volume", "volume_delta", "spike_ratio", "Open", "High", "Low", "Close"] if c in df.columns]
    if not cols:
        return df, None, None
    features = df[cols].fillna(0)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(features)
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(scaled)
    out = pd.DataFrame(reduced, index=df.index, columns=[f"PC{i+1}" for i in range(reduced.shape[1])])
    out["spike_label"] = (df["spike_ratio"] > 1.5).astype(int) if "spike_ratio" in df.columns else 0
    return out, scaler, pca
