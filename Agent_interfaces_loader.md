Gemini said
To move your project into the implementation phase, here is the Python code for the first three critical components. You can feed these directly to Claude Code to have it create the files in your WSL2 environment.

1. Agent Interfaces (src/agents/base_agent.py)
This file establishes the "Contract" for your 10-year system. By using Abstract Base Classes (ABC), you ensure that every agent—whether it's the Librarian today or a Quantum-AI agent in 2030—follows the same communication protocol.

Python
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
        self.logger.setLevel(logging.INFO)

    @abstractmethod
    async def perceive(self, input_data: Any) -> Any:
        """Observe data from the environment (e.g., read a file or API)."""
        pass

    @abstractmethod
    async def reason(self, state: Any) -> Dict[str, Any]:
        """Process observations and determine the next action."""
        pass

    @abstractmethod
    async def act(self, plan: Dict[str, Any]) -> bool:
        """Execute the chosen action (e.g., write a file or trade)."""
        pass

    def log_action(self, action_name: str, status: str):
        self.logger.info(f"Action: {action_name} | Status: {status}")
2. US30 Data Loader (src/data/us30_loader.py)
This component standardizes your OHLCV data. It includes Min-Max Scaling, which is crucial for the Deep Learning (LSTM) and Reinforcement Learning (PPO) models you will build next.

Python
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class US30Loader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.scaler = MinMaxScaler()

    def load_clean_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.file_path)
        
        # Standardize Column Names
        df.columns = [c.capitalize() for c in df.columns]
        
        # Ensure DateTime Index
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
        
        # Drop NaNs and sort
        df.dropna(inplace=True)
        df.sort_index(inplace=True)
        
        return df

    def get_rl_features(self, df: pd.DataFrame) -> np.ndarray:
        """Normalizes OHLCV for RL/DL model input."""
        features = df[['Open', 'High', 'Low', 'Close', 'Volume']].values
        return self.scaler.fit_transform(features)

**"prompt, I have the core logic. Please:

Create src/agents/base_agent.py, src/data/us30_loader.py, and src/tools/monte_carlo.py using the provided logic.

Update requirements.txt to include pandas, numpy, scikit-learn, and stable-baselines3.
**

