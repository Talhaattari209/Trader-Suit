"""PPO for volume-based execution (VWAP-style)."""
import numpy as np
import pandas as pd
from typing import Any, Optional

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    import gym
    from gym import spaces
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

from src.config.computation_budget import budget as CB


def train_rl_volume(
    df: pd.DataFrame,
    total_timesteps: int | None = None,
) -> Optional[Any]:
    """Train a PPO agent on volume/OHLCV features.

    total_timesteps defaults to CB.rl_max_episodes * CB.backtest_bars
    (60,000 on local / 4,000,000 on colab).  Pass an explicit value to override.
    """
    if not HAS_SB3 or df is None or len(df) < 50:
        return None

    # Apply backtest data window from budget — focus on recent, clean data
    if len(df) > CB.backtest_bars:
        df = df.tail(CB.backtest_bars)

    _total_ts = total_timesteps if total_timesteps is not None else (
        CB.rl_max_episodes * min(len(df), CB.backtest_bars)
    )

    class VolumeEnv(gym.Env):
        def __init__(self, data: pd.DataFrame):
            super().__init__()
            self.df = data.reset_index(drop=True)
            self.current_step = 0
            feats = [c for c in self.df.columns if c != "spike_label"]
            self.observation_space = spaces.Box(low=0, high=1, shape=(len(feats),))
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,))

        def reset(self, seed=None, options=None):
            self.current_step = 0
            return self.df.iloc[0].drop("spike_label", errors="ignore").values.astype(np.float32), {}

        def step(self, action):
            row = self.df.iloc[self.current_step]
            slippage = abs(action[0]) * 0.0001
            reward = -slippage
            if "returns" in row.index:
                reward += float(row["returns"] * action[0])
            self.current_step += 1
            done = self.current_step >= len(self.df) - 1
            next_obs = self.df.iloc[min(self.current_step, len(self.df) - 1)].drop("spike_label", errors="ignore").values.astype(np.float32)
            return next_obs, reward, done, False, {}

    env = DummyVecEnv([lambda: VolumeEnv(df)])
    model = PPO(
        "MlpPolicy", env,
        learning_rate = 1e-4,
        n_steps       = 64 if CB.rl_batch_size <= 32 else 256,
        batch_size    = CB.rl_batch_size,
        n_epochs      = 3 if CB.rl_batch_size <= 32 else 10,
        verbose       = 0,
    )
    model.learn(total_timesteps=min(_total_ts, max(1000, len(df))))
    return model
