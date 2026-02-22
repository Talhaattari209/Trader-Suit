"""
Statistical edges: pairs trading, mean reversion, XGBoost/LSTM/PPO.
"""
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import mean_squared_error
    from sklearn.feature_selection import SelectFromModel
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from gym import spaces, Env
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

try:
    from src.tools.cointegration import pairs_trading_test
except ImportError:
    from ..tools.cointegration import pairs_trading_test


class StatisticalModels:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.features = data.drop(columns=["returns"], errors="ignore")
        if "returns" not in self.data.columns and len(self.data.columns) > 0:
            self.data["returns"] = self.data.iloc[:, 0].pct_change().fillna(0)

    def unsupervised_clustering(self, n_clusters: int = 5) -> pd.DataFrame:
        if not HAS_SKLEARN:
            return self.data
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(self.features.fillna(0))
        self.data = self.data.copy()
        self.data["cluster"] = labels
        return self.data

    def supervised_prediction(
        self, target_col: str = "returns"
    ) -> tuple[Any, List[str], np.ndarray, float]:
        if not HAS_XGB or not HAS_SKLEARN:
            return None, [], np.zeros(len(self.data)), 0.0
        X = self.features.fillna(0)
        if target_col not in self.data.columns:
            return None, [], np.zeros(len(self.data)), 0.0
        y = self.data[target_col]
        model = XGBRegressor(
            objective="reg:squarederror", n_estimators=100, random_state=42
        )
        model.fit(X, y)
        selector = SelectFromModel(model, threshold="median", prefit=True)
        try:
            selected = selector.get_support()
            selected_features = list(X.columns[selected])
        except Exception:
            selected_features = list(X.columns)
        preds = model.predict(X)
        mse = mean_squared_error(y, preds)
        return model, selected_features, preds, mse

    def dl_lstm_forecast(
        self, seq_len: int = 60, epochs: int = 50
    ) -> Optional[Any]:
        if not HAS_TORCH:
            return None
        if "returns" not in self.data.columns:
            return None
        X_seq, y_seq = [], []
        feats = self.features.fillna(0)
        for i in range(len(self.data) - seq_len):
            X_seq.append(feats.iloc[i : i + seq_len].values)
            y_seq.append(self.data["returns"].iloc[i + seq_len])
        if not X_seq:
            return None
        X_arr = np.array(X_seq, dtype=np.float32)
        y_arr = np.array(y_seq, dtype=np.float32)

        class LSTM(nn.Module):
            def __init__(self, input_size: int, hidden_size: int = 50):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, 1, batch_first=True)
                self.fc = nn.Linear(hidden_size, 1)

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])

        dataset = TensorDataset(
            torch.tensor(X_arr), torch.tensor(y_arr).unsqueeze(1)
        )
        loader = DataLoader(dataset, batch_size=32, shuffle=True)
        model = LSTM(input_size=X_arr.shape[2])
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        for _ in range(min(epochs, 10)):
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                out = model(batch_x)
                loss = criterion(out, batch_y)
                loss.backward()
                optimizer.step()
        return model

    def rl_arb_optimization(self, env: Optional[Any] = None) -> Optional[Any]:
        if not HAS_SB3:
            return None

        class ArbEnv(Env):
            def __init__(self, data: pd.DataFrame):
                super().__init__()
                self.data = data.reset_index(drop=True)
                self.current_step = 0
                self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,))
                self.observation_space = spaces.Box(
                    low=-np.inf, high=np.inf,
                    shape=(len(self.data.columns),),
                )

            def reset(self, **_):
                self.current_step = 0
                return self.data.iloc[0].values.astype(np.float32)

            def step(self, action):
                r = self.data["returns"].iloc[self.current_step] if "returns" in self.data.columns else 0.0
                reward = float(action[0] * r)
                self.current_step += 1
                done = self.current_step >= len(self.data) - 1
                obs = self.data.iloc[min(self.current_step, len(self.data) - 1)].values.astype(np.float32)
                return obs, reward, done, False, {}

        df = self.data.fillna(0)
        vec_env = DummyVecEnv([lambda: ArbEnv(df)])
        model = PPO("MlpPolicy", vec_env, learning_rate=1e-4, verbose=0)
        model.learn(total_timesteps=min(5000, max(100, len(df))))
        return model


def pairs_trading_signals(
    data: pd.DataFrame,
    col1: str = "Close",
    col2: Optional[str] = None,
    threshold: float = 2.0,
) -> Optional[pd.Series]:
    """Return series of strategy returns from pairs trading or None."""
    if col2 is None:
        if len(data.columns) >= 2:
            col2 = data.columns[1]
        else:
            return None
    if col1 not in data.columns or col2 not in data.columns:
        return None
    result = pairs_trading_test(data[col1], data[col2], threshold=threshold)
    if result is None:
        return None
    entry_signals, _ = result
    # Strategy return: signal * next period return of spread
    spread_ret = data[col1].pct_change() - data[col2].pct_change()
    ret = pd.Series(entry_signals, index=data.index[: len(entry_signals)]).shift(1).fillna(0) * spread_ret
    return ret.reindex(data.index).fillna(0)
