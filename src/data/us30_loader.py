import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..connectors.base_connector import BaseConnector


class US30Loader:
    """
    Load and standardize US30 OHLC(V) data.
    Supports: (1) CSV via file_path and load_clean_data();
    (2) Broker API via load_from_connector(connector, symbol, timeframe, count).
    Volume is optional in CSV; if missing, filled with 0 for get_rl_features.
    """

    def __init__(self, file_path: str | None = None):
        self.file_path = file_path
        self.scaler = MinMaxScaler()

    def load_clean_data(self) -> pd.DataFrame:
        """Load from CSV. Requires file_path to be set."""
        if self.file_path is None:
            raise ValueError("file_path is required for load_clean_data(); use load_from_connector() for broker data.")
        df = pd.read_csv(self.file_path)

        # Standardize column names (capitalize)
        df.columns = [c.strip().capitalize() for c in df.columns]

        # Map common variants to expected names
        if "Timestamp" not in df.columns and "Time" in df.columns:
            df = df.rename(columns={"Time": "Timestamp"})
        if "Timestamp" not in df.columns and "Date" in df.columns:
            df = df.rename(columns={"Date": "Timestamp"})

        # Ensure datetime index
        if "Timestamp" in df.columns:
            ts = df["Timestamp"]
            if pd.api.types.is_numeric_dtype(ts):
                # Epoch ms (e.g. 1759968000000)
                df["Timestamp"] = pd.to_datetime(ts, unit="ms")
            else:
                df["Timestamp"] = pd.to_datetime(ts)
            df.set_index("Timestamp", inplace=True)

        # Add Volume with 0 if missing (for get_rl_features)
        if "Volume" not in df.columns:
            df["Volume"] = 0

        # Drop NaNs and sort
        df.dropna(inplace=True)
        df.sort_index(inplace=True)

        return df

    def load_from_connector(
        self,
        connector: "BaseConnector",
        symbol: str = "US30",
        timeframe: str = "1h",
        count: int = 5000,
    ) -> pd.DataFrame:
        """
        Load OHLCV from a pluggable connector (Alpaca or MT5).
        Returns DataFrame in the same format as load_clean_data() for use with get_rl_features/get_returns_series.
        """
        if not connector.connect():
            raise RuntimeError("Connector failed to connect")
        df = connector.get_ohlcv(symbol, timeframe, count)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        # Connectors return index=Timestamp; ensure Volume exists
        if "Volume" not in df.columns:
            df["Volume"] = 0
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        df.sort_index(inplace=True)
        return df

    def get_rl_features(self, df: pd.DataFrame) -> np.ndarray:
        """Normalizes OHLCV for RL/DL model input. Uses available columns."""
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"DataFrame missing required column: {col}")
        features = df[required].values
        return self.scaler.fit_transform(features)

    def get_returns_series(self, df: pd.DataFrame) -> pd.Series:
        """Compute period returns from Close for Monte Carlo / backtest use."""
        if "Close" not in df.columns:
            raise ValueError("DataFrame must have 'Close' column for returns.")
        return df["Close"].pct_change().dropna()
