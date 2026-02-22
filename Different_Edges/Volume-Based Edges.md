# Volume-Based Edges Implementation Script

This Markdown script provides a detailed, self-contained implementation guide for **Volume-Based Edges** within the Generative Quant Lab (autonomous quantitative trading factory, aka "Ralph Wiggum Loop"). It is designed to prevent hallucinations by the Coding Agent by including explicit code snippets, file paths, library imports, mathematical formulations, hyperparameters, evaluation metrics, and step-by-step integration instructions. All components align with the project's architecture: multi-agent system (Librarian, Strategist, Killer Agents), financial models (e.g., Monte Carlo, GARCH), AI techniques (ML, DL, RL, PCA), and tools (e.g., stable-baselines3, PyTorch, scikit-learn, pandas).

The focus is on leveraging volume as an institutional footprint (e.g., spikes indicating interest). The workflow automates research (anomaly detection, prediction) and execution (VWAP/TWAP optimization) using real-time feeds. Scalability is ensured for tick-level data via tensor operations and GPU acceleration.

## 1. Overview

**Description**: This module detects and exploits volume-based edges, such as spikes (>150% average) signaling breakouts or imbalances indicating institutional activity. It integrates:
- **ML** for anomaly classification.
- **DL** for pattern detection in volume profiles treated as "images."
- **RL** for adaptive execution (e.g., reward-maximizing VWAP in imbalances).
- **Agentic Workflow**: Volume Analyst Agent scans feeds and collaborates with other agents (e.g., Structure Agent for confirmation).

**Key Features**:
- Real-time data ingestion via connectors (e.g., Polygon API for tick data).
- Preprocessing with PCA for dimensionality reduction on volume features.
- Validation via Monte Carlo simulations with friction (slippage) and GARCH volatility.
- Execution with low-latency RL agents.
- Robustness: Stress-testing for regimes (e.g., 2.5x vol multiplier); quarterly retraining.

**Dependencies** (from `requirements.txt`):
- pandas, numpy, scikit-learn (for ML/PCA).
- torch (for DL/RL via stable-baselines3).
- statsmodels (for GARCH).
- Existing project libs: stable-baselines3 for PPO.

**File Structure Additions**:
- `src/edges/volume_based/` (new directory for modularity).
  - `volume_analyzer.py`: Core logic for detection and prediction.
  - `volume_rl_agent.py`: RL for execution.
  - `volume_agent.py`: Agentic LLM integration.
- Integrate into `run_ralph.py` for loop.

## 2. Data Ingestion and Preprocessing

**Role**: Fetch and normalize volume data for models.

**Implementation**:
- Use `src/connectors/polygon_connector.py` (add if needed; assumes API key configured).
- Preprocess: Calculate rolling averages, deltas; apply PCA to reduce features (e.g., volume, price-volume correlations).

**Code Snippet** (`src/data/volume_loader.py` - new file):
```python
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from polygon import RESTClient  # Assuming configured API

def load_volume_data(symbol='US30', timeframe='1min', limit=10000):
    client = RESTClient()  # API key auto-configured
    bars = client.get_aggs(symbol, 1, 'minute', from_='2026-01-01', to='2026-02-20', limit=limit)
    df = pd.DataFrame(bars)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['volume_delta'] = df['volume'].diff()
    df['avg_volume'] = df['volume'].rolling(window=20).mean()  # 20-period MA
    df['spike_ratio'] = df['volume'] / df['avg_volume']
    df.dropna(inplace=True)
    return df

def preprocess_data(df, n_components=0.95):
    features = df[['volume', 'volume_delta', 'spike_ratio', 'open', 'high', 'low', 'close']]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(features)
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(scaled)
    df_reduced = pd.DataFrame(reduced, index=df.index, columns=[f'PC{i+1}' for i in range(reduced.shape[1])])
    df_reduced['spike_label'] = (df['spike_ratio'] > 1.5).astype(int)  # Label for ML: 1 if spike >150%
    return df_reduced, scaler, pca

# Example usage (for testing):
# df = load_volume_data()
# processed, _, _ = preprocess_data(df)
```

**Metrics**: Explained variance >95% for PCA; handle NaNs via forward-fill.

## 3. Models Implementation

### A. Machine Learning (ML) for Anomaly Classification
**Role**: Classify volume spikes/anomalies using Random Forests; extract feature importance for deltas.

**Mathematical Formulation**: Random Forest: Ensemble of decision trees; Gini impurity for splits. Feature importance: Mean decrease in impurity.

**Code Snippet** (`src/edges/volume_based/volume_analyzer.py`):
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score

def train_volume_classifier(df_reduced):
    X = df_reduced.drop('spike_label', axis=1)
    y = df_reduced['spike_label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)
    preds = rf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    importances = rf.feature_importances_  # For deltas analysis
    return rf, acc, prec, importances

# Hyperparameters: n_estimators=100, max_depth=10 (tune via grid search if needed).
# Metrics: Accuracy >80%, Precision >70% for spike detection.
```

### B. Deep Learning (DL) for Pattern Detection
**Role**: Treat volume profiles as "images" (e.g., 2D arrays of time x features); use CNNs to detect patterns like accumulation.

**Mathematical Formulation**: CNN: Conv2D layers extract features; e.g., kernel filters on volume-time grids.

**Code Snippet** (`src/edges/volume_based/volume_analyzer.py` - append):
```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

class VolumeCNN(nn.Module):
    def __init__(self):
        super(VolumeCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(32 * 15 * 5, 128)  # Adjust based on input shape (e.g., 30x10 grid)
        self.fc2 = nn.Linear(128, 1)  # Binary: momentum post-spike

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = x.view(-1, 32 * 15 * 5)
        x = torch.relu(self.fc1(x))
        return torch.sigmoid(self.fc2(x))

def train_cnn(df_reduced, epochs=50, batch_size=32):
    # Reshape to "images": e.g., rolling windows of 30 timesteps x 10 features
    windows = np.array([df_reduced.iloc[i:i+30].values for i in range(len(df_reduced)-30)])
    labels = df_reduced['spike_label'].iloc[30:].values
    X = torch.tensor(windows[:, np.newaxis, :, :], dtype=torch.float32)  # (N, 1, 30, features)
    y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    model = VolumeCNN()
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(epochs):
        for inputs, targets in loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
    return model

# Hyperparameters: lr=0.001, epochs=50.
# Metrics: BCE loss <0.3, directional accuracy >65%.
# Scalability: Use GPU: model.to('cuda') if torch.cuda.is_available().
```

### C. Reinforcement Learning (RL) for Execution
**Role**: Optimize VWAP/TWAP in volume imbalances; rewards based on slippage minimization.

**Mathematical Formulation**: PPO: Clipped surrogate objective; rewards = -slippage + alpha_capture (e.g., Sharpe-adjusted).

**Code Snippet** (`src/edges/volume_based/volume_rl_agent.py`):
```python
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
import gym
from gym import spaces

class VolumeTradingEnv(gym.Env):
    def __init__(self, df):
        super(VolumeTradingEnv, self).__init__()
        self.df = df.reset_index()
        self.current_step = 0
        self.action_space = spaces.Box(low=-1, high=1, shape=(1,))  # Position sizing
        self.observation_space = spaces.Box(low=0, high=1, shape=(df.shape[1]-1,))  # Normalized features

    def reset(self):
        self.current_step = 0
        return self.df.iloc[0].drop('spike_label').values

    def step(self, action):
        row = self.df.iloc[self.current_step]
        slippage = abs(action[0]) * row['volume_delta'] * 0.0001  # Simulated friction
        reward = -slippage + (row['close'] - row['open']) * action[0]  # Risk-adjusted
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        return self.df.iloc[self.current_step].drop('spike_label').values, reward, done, {}

def train_rl_agent(df_reduced):
    env = make_vec_env(lambda: VolumeTradingEnv(df_reduced), n_envs=1)
    model = PPO('MlpPolicy', env, learning_rate=1e-4, clip_range=0.2, verbose=1)
    model.learn(total_timesteps=100000)
    return model

# Hyperparameters: timesteps=100000, lr=1e-4.
# Metrics: Cumulative reward >0, Sharpe >1 in sims.
```

### D. Agentic Integration (Volume Analyst Agent)
**Role**: LLM-based agent scans feeds, collaborates (e.g., with Structure Agent).

**Code Snippet** (`src/edges/volume_based/volume_agent.py`):
```python
from anthropic import Anthropic  # Assuming Claude API configured

client = Anthropic()  # API key in env

def volume_analyst_scan(df_reduced, context_from_other_agents=''):
    prompt = f"""
    Analyze volume data: {df_reduced.tail(10).to_json()}
    Detect spikes >150% avg. Predict post-spike momentum.
    Collaborate: {context_from_other_agents}
    Output: Hypothesis (e.g., 'Enter long on spike') and code draft.
    """
    response = client.messages.create(model='claude-3-opus-20240229', max_tokens=500, messages=[{'role': 'user', 'content': prompt}])
    return response.content[0].text

# Integration: Call in Librarian/Strategist flow.
```

## 4. Workflow Integration into Ralph Wiggum Loop

**Detailed Flow** (Update `run_ralph.py`):
1. **Perceive**: Watchers call `load_volume_data()` and `preprocess_data()`; save to Vault.
2. **Reason**: Librarian identifies needs; Volume Analyst Agent scans and generates hypothesis; Strategist drafts code (e.g., integrate RF/CNN predictions).
3. **Validate**: Killer loads draft; runs backtest with `train_volume_classifier()` and `train_cnn()`; applies Monte Carlo (`src/tools/monte_carlo_pro.py`) with slippage injection (e.g., add Gaussian noise to volume); GARCH for vol forecast (`from statsmodels.tsa.api import GARCH; model = GARCH().fit(df['volume_delta'])`); reject if VaR >5% or ruin prob >2%.
4. **Execute**: Approved: Deploy RL agent (`train_rl_agent()`); execute via connectors (e.g., VWAP order on spike); feedback loop retrains quarterly.

**Mermaid Diagram** (for visualization):
```mermaid
graph TD
    Data[Polygon API / Tick Data] -->|Load & Preprocess (PCA)| Watchers
    Watchers --> Vault
    Vault --> Librarian[Volume Analyst Agent (LLM)]
    Librarian --> Plans[Hypothesis: Spike Detection]
    Plans --> Strategist[Draft Code: RF/CNN]
    Strategist --> Drafts
    Drafts --> Killer[Backtest + Monte Carlo (Slippage/GARCH)]
    Killer -->|Approve| RL[Train PPO for VWAP]
    RL --> Execution[Connectors: Trade on Imbalance]
    Execution -->|Feedback| Data
```

**Refinement**:
- Backtesting: Walk-forward on 10+ years (fetch historical via Polygon).
- Optimization: Bayesian for hypers (use `from skopt import BayesSearchCV`).
- Adaptation: Online RL updates; stress-test regimes.
- Robustness: Bias correction in ML (e.g., SMOTE for imbalanced labels).

This script is ready for Coding Agent implementation. Test with sample data: `df = load_volume_data(); model = train_volume_classifier(preprocess_data(df)[0])`.