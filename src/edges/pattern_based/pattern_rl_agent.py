"""PPO for pattern-based position sizing."""
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


def train_rl_pattern(data: pd.DataFrame, total_timesteps: int = 5000) -> Optional[Any]:
    if not HAS_SB3 or data is None or len(data) < 100:
        return None

    class PatternEnv(gym.Env):
        def __init__(self, df: pd.DataFrame):
            super().__init__()
            self.df = df.reset_index(drop=True)
            self.current_step = 0
            self.observation_space = spaces.Box(
                low=0, high=1, shape=(min(60, len(df.columns)) * 5,),
            )
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,))

        def reset(self, seed=None, options=None):
            self.current_step = 0
            return self._obs(), {}

        def _obs(self):
            row = self.df.iloc[self.current_step]
            return np.array(row.values[: self.observation_space.shape[0]], dtype=np.float32)

        def step(self, action):
            reward = 0.0
            if "returns" in self.df.columns and self.current_step + 1 < len(self.df):
                r = self.df["returns"].iloc[self.current_step + 1]
                reward = float(action[0] * r)
            self.current_step += 1
            done = self.current_step >= len(self.df) - 1
            return self._obs(), reward, done, False, {}

    env = DummyVecEnv([lambda: PatternEnv(data)])
    model = PPO("MlpPolicy", env, learning_rate=1e-4, verbose=0)
    model.learn(total_timesteps=min(total_timesteps, max(500, len(data))))
    return model


def execute_pattern_rl(model: Any, state: np.ndarray) -> float:
    if model is None or state is None:
        return 0.0
    action, _ = model.predict(state)
    return float(action[0]) if hasattr(action, "__getitem__") else float(action)
