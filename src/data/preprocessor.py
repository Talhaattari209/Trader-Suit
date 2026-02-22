"""
Shared data preprocessing: PCA, normalization, feature prep for edges.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def load_and_preprocess_data(
    file_path_or_api: str,
    assets: Optional[List[str]] = None,
    freq: str = "1min",
    n_components: float = 0.95,
) -> Tuple[pd.DataFrame, Optional[np.ndarray]]:
    """
    Load OHLCV from CSV or API, compute returns/correlations, apply PCA.
    Returns (reduced_df, explained_variance_ratio or None).
    """
    assets = assets or ["US30", "AAPL"]
    if not HAS_SKLEARN:
        # Fallback: load CSV only, no PCA
        try:
            df = pd.read_csv(file_path_or_api) if file_path_or_api.endswith(".csv") else pd.DataFrame()
            if not df.empty and "Close" in df.columns:
                df["returns"] = df["Close"].pct_change().fillna(0)
            return df, None
        except Exception:
            return pd.DataFrame(), None

    data = {}
    if file_path_or_api == "polygon":
        try:
            from polygon import RESTClient
            client = RESTClient()
            for asset in assets:
                bars = client.get_aggs(asset, 1, freq, from_="2020-01-01", to="2026-02-20")
                df = pd.DataFrame(bars)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                data[asset] = df[["open", "high", "low", "close", "volume"]].copy()
                data[asset].columns = [c.capitalize() for c in data[asset].columns]
        except Exception:
            pass
    else:
        try:
            df = pd.read_csv(file_path_or_api)
            df.columns = [c.strip().capitalize() for c in df.columns]
            if "Timestamp" not in df.columns and "Time" in df.columns:
                df = df.rename(columns={"Time": "Timestamp"})
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"])
                df.set_index("Timestamp", inplace=True)
            if "Volume" not in df.columns:
                df["Volume"] = 0
            data["US30"] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        except Exception:
            return pd.DataFrame(), None

    if not data:
        return pd.DataFrame(), None

    for asset, df in data.items():
        df["returns"] = df["Close"].pct_change().fillna(0)
        if len(assets) > 1 and list(data.keys())[0] != asset:
            other = list(data.values())[0]
            roll = df["Close"].rolling(252).corr(other["Close"])
            df["correlation"] = roll

    combined = pd.concat(data.values(), axis=1, keys=list(data.keys()))
    combined = combined.ffill().dropna()
    if combined.empty:
        return pd.DataFrame(), None

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(combined)
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(scaled)
    reduced_df = pd.DataFrame(
        reduced,
        index=combined.index,
        columns=[f"PC{i+1}" for i in range(reduced.shape[1])],
    )
    return reduced_df, getattr(pca, "explained_variance_ratio_", None)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """MinMax scale OHLCV columns. Returns copy with scaled values."""
    if not HAS_SKLEARN:
        return df.copy()
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    if not cols:
        return df.copy()
    scaler = MinMaxScaler()
    out = df.copy()
    out[cols] = scaler.fit_transform(df[cols])
    return out
