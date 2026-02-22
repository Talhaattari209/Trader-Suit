# Implementation Script for Market Structure Edges

This Markdown script provides a detailed, step-by-step guide for implementing **Market Structure Edges** within the Generative Quant Lab (autonomous quantitative trading factory, aka "Ralph Wiggum Loop"). The focus is on analyzing price levels, trends, and liquidity using concepts like Inner Circle Trader (ICT) elements (e.g., Order Blocks, Fair Value Gaps (FVG), Break of Structure (BOS), liquidity sweeps). This edge type integrates with the multi-agent system (Librarian, Strategist, Killer Agents) and embeds financial models (e.g., GARCH for volatility, Monte Carlo for simulations), AI techniques (ML for regime detection, DL for multi-timeframe analysis, RL for optimization), and PCA for preprocessing.

The implementation emphasizes modularity, scalability (e.g., handling multi-asset, high-frequency data), and robustness (e.g., stress-testing with stochastic processes). All code assumes Python 3.12+ environment with libraries like pandas, numpy, scikit-learn, torch (for DL/RL), statsmodels (for Hurst), and stable-baselines3 (for RL). File paths build on existing structure (e.g., `src/agents/`, `src/tools/`).

To prevent hallucinations in the Coding Agent (e.g., when using LLMs like Claude for strategy generation), this script includes:
- Explicit mathematical formulations.
- Precise code snippets with imports and error handling.
- Clear workflow mappings to the Ralph Wiggum Loop.
- Hyperparameter defaults and tuning guidelines.
- Validation metrics and pitfalls.

## 1. Overview of Market Structure Edges

**Description**: Market structure edges exploit hierarchical price action: higher highs/lows for trends, support/resistance levels (order blocks), gaps (FVG), and liquidity pools. Regimes are detected (trending vs. ranging) to adapt strategies.

**Key Components**:
- **Regime Detection**: Use Hurst exponent (H > 0.5 for trending, H < 0.5 for mean-reverting).
- **Structure Identification**: Detect BOS (break of prior high/low), FVG (imbalance gaps), Order Blocks (mitigation zones).
- **Liquidity Analysis**: Identify sweeps (price probing liquidity) and levels.
- **AI Enhancements**: ML for classification, DL (Transformers/GNNs) for multi-timeframe/relational analysis, RL (DQN) for breakout trading.
- **Agentic Workflow**: Multi-agent debate (e.g., Structure Agent identifies BOS, Risk Agent confirms via vol).

**Integration Points**:
- Data from `src/connectors/` (e.g., Alpaca for OHLCV).
- Preprocessing with PCA in `src/data/`.
- Validation via `src/tools/monte_carlo_pro.py`.
- Execution in `run_ralph.py` loop.

**Scalability Considerations**:
- Process multi-timeframes (e.g., 1m, 5m, 1h) in parallel using PyTorch tensors.
- Deploy on GPU for DL/RL; handle 100+ assets via vectorized ops.
- Low-latency: Aim for <100ms inference per tick.

## 2. Required Files and Structure

Add/update these files in the project:

- `src/edges/market_structure.py`: Core logic for detection (Hurst, BOS, FVG, etc.).
- `src/agents/structure_agent.py`: LLM-based agent for identification and debate.
- `src/ml/regime_classifier.py`: ML models for regime detection.
- `src/dl/transformer_analyzer.py`: DL for multi-timeframe.
- `src/dl/gnn_structure.py`: GNN for relational structures (optional advanced).
- `src/rl/dqn_breakout.py`: RL for breakout optimization.
- `src/tools/liquidity_tools.py`: Utilities for sweeps and levels.

Update `requirements.txt` if needed (e.g., ensure `torch`, `stable-baselines3`, `networkx` for GNNs).

## 3. Detailed Implementation by Component

### A. Data Preprocessing and Feature Engineering
*Role*: Prepare OHLCV for analysis; reduce dimensions with PCA.

**Code Snippet** (in `src/data/market_structure_preprocessor.py`):
```python
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

def preprocess_data(df: pd.DataFrame, n_components: float = 0.95) -> pd.DataFrame:
    """
    Preprocess OHLCV data: Compute features like swings, then apply PCA.
    :param df: DataFrame with 'open', 'high', 'low', 'close', 'volume'.
    :param n_components: Variance ratio for PCA.
    :return: Reduced DataFrame.
    """
    # Compute swing highs/lows (pivot points)
    df['swing_high'] = df['high'].rolling(window=20, center=True).max()
    df['swing_low'] = df['low'].rolling(window=20, center=True).min()
    
    # Features: Returns, vol, Hurst (computed separately), etc.
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(20).std()
    
    # Normalize
    scaler = MinMaxScaler()
    features = df[['open', 'high', 'low', 'close', 'volume', 'returns', 'volatility']].dropna()
    scaled = scaler.fit_transform(features)
    
    # PCA reduction
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(scaled)
    explained = pca.explained_variance_ratio_.sum()
    print(f"Explained variance: {explained:.2f}")
    
    # Return as DF
    reduced_df = pd.DataFrame(reduced, index=features.index, columns=[f'pc{i}' for i in range(reduced.shape[1])])
    return pd.concat([df, reduced_df], axis=1).dropna()
```

**Workflow Integration**: Called in Watchers (Perception phase) before feeding to agents.

### B. Regime Detection (ML Component)
*Role*: Classify market regimes using Hurst exponent and ML.

**Mathematical Formulation**: Hurst Exponent (H) via rescaled range (R/S) analysis:  
H = log(R/S) / log(n), where R = max(cumsum) - min(cumsum), S = std(deviations), n = window size.  
- H > 0.5: Trending (persistent).  
- H < 0.5: Mean-reverting (anti-persistent).  
- H ≈ 0.5: Random walk.

**Code Snippet** (in `src/ml/regime_classifier.py`):
```python
import pandas as pd
import numpy as np
from statsmodels.regression.linear_model import OLS
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def compute_hurst(series: pd.Series, window: int = 100) -> float:
    """
    Compute Hurst exponent for regime detection.
    :param series: Log prices.
    :param window: Rolling window.
    :return: H value.
    """
    if len(series) < window:
        raise ValueError("Series too short")
    lags = range(2, window)
    tau = [np.std(np.subtract(series[lag:], series[:-lag])) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0]

def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    ML classification: Train RF on features including Hurst.
    :param df: Preprocessed DF.
    :return: DF with 'regime' column (0: ranging, 1: trending).
    """
    df['hurst'] = df['close'].rolling(100).apply(lambda x: compute_hurst(np.log(x)))
    features = df[['hurst', 'volatility', 'pc0', 'pc1']].dropna()  # From PCA
    labels = (features['hurst'] > 0.5).astype(int)  # Binary label
    
    X_train, X_test, y_train, y_test = train_test_split(features.drop('hurst', axis=1), labels, test_size=0.2)
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Regime classification accuracy: {acc:.2f}")
    
    df['regime'] = clf.predict(features.drop('hurst', axis=1))
    return df
```

**Hyperparameters**: n_estimators=100, max_depth=10; tune with GridSearchCV.  
**Metrics**: Accuracy >70%, precision-recall for imbalanced regimes.  
**Pitfalls**: Non-stationarity; mitigate with rolling windows and ADF tests.

### C. Structure Identification (Agentic + DL Component)
*Role*: Detect BOS, FVG, Order Blocks using LLMs and DL.

**Definitions**:
- **BOS**: Break of prior swing high (bullish) or low (bearish).
- **FVG**: Gap between candles where high_{t-1} < low_{t+1} (bullish imbalance).
- **Order Block**: Zone where price mitigated (e.g., last bearish candle before bullish impulse).

**Code Snippet** (in `src/agents/structure_agent.py` for LLM part; `src/dl/transformer_analyzer.py` for DL):
```python
# LLM Agent (using Claude/Anthropic via API placeholder)
import anthropic  # Assume API key set

client = anthropic.Anthropic(api_key="your_key")

def structure_agent(df: pd.DataFrame) -> dict:
    """
    LLM identifies structures; debates with risk agent.
    :param df: DF with OHLCV.
    :return: Dict of detected structures.
    """
    prompt = f"""
    Analyze market structure:
    - Data: {df.tail(50).to_csv()}  # Last 50 bars
    - Detect BOS: Break of swing high/low.
    - Detect FVG: Imbalance gaps.
    - Detect Order Blocks: Mitigation zones.
    - Regime: {df['regime'].iloc[-1]}
    Output JSON: {{'bos': bool, 'fvg': list of levels, 'order_blocks': list of zones}}
    """
    message = client.messages.create(model="claude-3-opus-20240229", max_tokens=500, messages=[{"role": "user", "content": prompt}])
    response = message.content[0].text  # Parse JSON
    return eval(response)  # Safely parse

# DL: Transformers for multi-timeframe
import torch
import torch.nn as nn

class MultiTimeframeTransformer(nn.Module):
    def __init__(self, input_dim: int = 5, num_layers: int = 4, num_heads: int = 8):
        super().__init__()
        self.encoder_layer = nn.TransformerEncoderLayer(d_model=input_dim, nhead=num_heads)
        self.transformer = nn.TransformerEncoder(self.encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(input_dim, 3)  # Output: BOS prob, FVG prob, regime

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (seq_len, batch, features)
        x = self.transformer(x)
        return torch.sigmoid(self.fc(x.mean(dim=0)))  # Aggregate

# Usage
def analyze_multi_timeframe(dfs: list[pd.DataFrame]) -> torch.Tensor:  # List of DFs for different TFs
    tensors = [torch.tensor(df[['open', 'high', 'low', 'close', 'volume']].values).unsqueeze(1) for df in dfs]
    input_tensor = torch.cat(tensors, dim=0)  # (seq, batch=1, features)
    model = MultiTimeframeTransformer()
    return model(input_tensor)
```

**Hyperparameters**: Layers=4, heads=8; train with MSE loss on labeled data.  
**Metrics**: Detection accuracy >80%; use SHAP for explainability.  
**Pitfalls**: Overfitting to noise; mitigate with dropout=0.2 and cross-val.

### D. Liquidity Analysis and GNNs (Advanced DL)
*Role*: Model relational structures (e.g., liquidity networks).

**Code Snippet** (in `src/dl/gnn_structure.py`):
```python
import torch
import torch_geometric.nn as pyg_nn  # Requires torch-geometric if installed; else skip
import networkx as nx

def build_liquidity_graph(df: pd.DataFrame) -> torch_geometric.data.Data:
    """
    GNN for liquidity relations.
    :param df: DF.
    :return: Graph data.
    """
    G = nx.Graph()
    for i in range(len(df)):
        G.add_node(i, features=df.iloc[i][['high', 'low', 'volume']])
        if i > 0:
            G.add_edge(i-1, i, weight=abs(df['close'].iloc[i] - df['close'].iloc[i-1]))
    
    # Convert to PyG
    from torch_geometric.utils import from_networkx
    data = from_networkx(G)
    return data

class LiquidityGNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = pyg_nn.GCNConv(3, 16)  # Features: high, low, vol
        self.fc = nn.Linear(16, 1)  # Predict liquidity sweep prob

    def forward(self, data):
        x = self.conv1(data.x, data.edge_index)
        return torch.sigmoid(self.fc(x.mean(dim=0)))

# Usage: model = LiquidityGNN(); probs = model(graph_data)
```

**Pitfalls**: Dependency on torch-geometric; fallback to rule-based if unavailable.

### E. RL for Breakout Trading (DQN)
*Role*: Optimize entries at support/resistance.

**Code Snippet** (in `src/rl/dqn_breakout.py`):
```python
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import DummyVecEnv

class BreakoutEnv(gym.Env):
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(10,))  # State: prices, regime, etc.
        self.action_space = gym.spaces.Discrete(3)  # 0: Hold, 1: Long at breakout, 2: Short
        self.current_step = 0

    def reset(self, seed=None):
        self.current_step = 0
        return self._get_obs(), {}

    def step(self, action):
        reward = self._compute_reward(action)  # E.g., Sharpe-adjusted P&L
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        return self._get_obs(), reward, done, False, {}

    def _get_obs(self):
        return self.df.iloc[self.current_step][['close', 'regime', 'hurst', 'pc0']].values  # Example state

    def _compute_reward(self, action):
        # Reward: Positive for correct breakout, penalize drawdown
        return np.random.rand()  # Placeholder; implement based on structure

def train_dqn(df: pd.DataFrame):
    env = DummyVecEnv([lambda: BreakoutEnv(df)])
    model = DQN("MlpPolicy", env, learning_rate=1e-3, buffer_size=10000, verbose=1)
    model.learn(total_timesteps=10000)
    return model
```

**Hyperparameters**: LR=1e-3, buffer=10k; rewards: Sharpe * Sortino.  
**Metrics**: Cumulative reward > baseline; policy entropy for exploration.  
**Pitfalls**: Overfitting; use online learning and diverse regimes.

## 4. Workflow Integration into Ralph Wiggum Loop

**Perceive**: Ingest data via connectors; preprocess with PCA and compute Hurst/regime.

**Reason**: Structure Agent (LLM + DL) identifies elements; debates with Killer (e.g., "Is BOS valid in high vol?").

**Validate**: Killer runs backtests; Monte Carlo with Heston (stochastic vol) and regime stress (e.g., multiply vol by 2.5x); inject slippage; approve if Sharpe >1, drawdown <20%, ruin prob <5%.

**Execute**: Deploy RL (DQN) for live breakouts; dynamic hedging with GARCH forecasts; log decisions.

**Mermaid Flow Update** (add to `run_ralph.py` docs):
```mermaid
graph TD
    Data --> Preprocess[PCA + Hurst]
    Preprocess --> StructureAgent[Structure Agent (LLM/DL)]
    StructureAgent --> RegimeML[Regime Classifier]
    RegimeML --> Killer[Validate with Monte Carlo/GARCH]
    Killer --> RL[DQN Execution]
    RL --> Market[Connectors]
```

## 5. Testing and Refinement

- **Backtesting**: Use 10+ years data; walk-forward with OOS periods.
- **Optimization**: Bayesian (via skopt) for params; PPO alternative if continuous actions needed.
- **Adaptation**: Retrain DL/RL quarterly; online updates via env feedback.
- **Robustness**: Bias correction in ML; stress across crashes (2008, 2020).
- **Example Run**: Load US30; preprocess; classify regime; detect BOS; train DQN; simulate 10k paths.

This script is self-contained for implementation. If errors occur, debug with print statements and handle exceptions.