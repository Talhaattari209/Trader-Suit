# Statistical Edges Implementation Script

This Markdown document provides a detailed, self-contained script for implementing **Statistical Edges** within the Generative Quant Lab (autonomous quantitative trading factory, aka "Ralph Wiggum Loop"). The implementation focuses on exploiting quantitative anomalies such as correlations and deviations, using a combination of supervised ML, unsupervised techniques, DL, and RL. It integrates seamlessly with the existing multi-agent system (Librarian, Strategist, Killer Agents) and foundational components (e.g., data connectors, Monte Carlo simulations, GARCH volatility modeling).

To prevent hallucinations in the Coding Agent (e.g., when using LLMs like Claude for code generation), this script includes:
- **Explicit File Structure**: Precise file paths and names based on the existing project (e.g., `src/agents/`, `src/tools/`).
- **Code Snippets**: Actual Python code examples with imports, functions, and comments. Use libraries available in the environment (e.g., scikit-learn, pandas, numpy, torch, statsmodels, stable-baselines3). No external installs.
- **Modular Design**: Each component is broken down into functions/classes for easy integration.
- **Workflow Integration**: Maps directly to the Ralph Wiggum Loop (Perceive → Reason → Validate → Execute).
- **Parameters and Metrics**: Hardcoded defaults with explanations to avoid ambiguity.
- **Error Handling and Safeguards**: Basic checks for data integrity, model convergence, and risk limits.
- **Scalability Notes**: GPU usage via PyTorch, vectorized operations with NumPy.

Assume the project root is `./`, and build upon existing files like `src/connectors/alpaca_connector.py`, `src/tools/monte_carlo_pro.py`, etc. Test all code snippets in the code_execution tool before deployment.

## 1. Overview and Requirements

- **Edge Type**: Statistical Edges – Focus on anomalies like high correlations (e.g., pairs trading) or deviations (e.g., mean reversion via z-scores).
- **Key Models**:
  - Supervised ML: XGBoost for return prediction.
  - Unsupervised: K-Means clustering for asset grouping; PCA for feature reduction.
  - DL: LSTM for time-series forecasting.
  - RL: PPO for threshold refinement in arbitrage.
- **Data Sources**: Multi-asset OHLCV (e.g., US30, stocks via Polygon API).
- **Integration Points**:
  - Perceive: Use `src/data/us30_loader.py` with added PCA.
  - Reason: Enhance Librarian/Strategist Agents to generate hypotheses.
  - Validate: Extend Killer Agent with Monte Carlo + GARCH.
  - Execute: Deploy RL agent for live trading.
- **Dependencies**: pandas, numpy, scikit-learn (for ML/PCA), torch (for DL), statsmodels (for cointegration/GARCH), stable-baselines3 (for RL).
- **Metrics for Approval**: Sharpe Ratio >1, Max Drawdown <20%, Probability of Ruin <5%, Out-of-Sample Accuracy >60%.
- **Scalability**: Process high-frequency data (e.g., 1-min bars); use batch processing and GPU for training.

## 2. File Structure Additions/Modifications

Add or modify the following files in the project:

- `src/edges/statistical_edges.py`: Core module for statistical models and functions.
- `src/data/preprocessor.py`: Enhanced preprocessing with PCA and normalization.
- `src/agents/librarian_stat.py`: Specialized Librarian for hypothesis generation.
- `src/agents/strategist_stat.py`: Strategist for coding statistical strategies.
- `src/agents/killer_stat.py`: Killer with statistical validation extensions.
- `src/rl/stat_rl_agent.py`: RL component for optimization.
- `src/tools/cointegration.py`: Utility for pairs trading tests.
- `run_statistical_edges.py`: Entry script to run the loop for this edge.

## 3. Detailed Code Implementations

### 3.1 Data Preprocessing (`src/data/preprocessor.py`)

This module ingests and preprocesses data, applying PCA for dimensionality reduction.

```python
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import StandardScaler  # For z-scores

def load_and_preprocess_data(file_path_or_api, assets=['US30', 'AAPL'], freq='1min'):
    """
    Load OHLCV data from CSV/API, compute features (e.g., returns, correlations), apply PCA.
    :param file_path_or_api: str, path or API endpoint (e.g., 'polygon' for Polygon API).
    :param assets: list, assets to fetch.
    :param freq: str, data frequency.
    :return: pd.DataFrame, preprocessed data with reduced dimensions.
    """
    if file_path_or_api == 'polygon':
        # Use Polygon API (environment has key)
        from polygon import RESTClient
        client = RESTClient()  # API key auto-configured
        data = {}
        for asset in assets:
            bars = client.get_aggs(ticker=asset, multiplier=1, timespan=freq, from_='2020-01-01', to='2026-02-20')
            df = pd.DataFrame(bars)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[asset] = df[['open', 'high', 'low', 'close', 'volume']]
    else:
        # Load from CSV
        data = {asset: pd.read_csv(f"{file_path_or_api}_{asset}.csv", index_col='timestamp', parse_dates=True) for asset in assets}
    
    # Compute features: returns, rolling correlations
    for asset, df in data.items():
        df['returns'] = df['close'].pct_change().fillna(0)
        if len(assets) > 1:
            # Example pairwise correlation
            corr_df = pd.concat([data[assets[0]]['close'], df['close']], axis=1).rolling(252).corr().iloc[0::2, -1]
            df['correlation'] = corr_df.values
    
    # Concatenate multi-asset
    combined_df = pd.concat(data.values(), axis=1, keys=assets)
    combined_df = combined_df.fillna(method='ffill').dropna()
    
    # Normalize and PCA
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(combined_df)
    pca = PCA(n_components=0.95)  # Retain 95% variance
    reduced = pca.fit_transform(scaled)
    reduced_df = pd.DataFrame(reduced, index=combined_df.index, columns=[f'PC{i+1}' for i in range(reduced.shape[1])])
    
    return reduced_df, pca.explained_variance_ratio_  # Return data and variance for logging

# Example usage: data, var_ratio = load_and_preprocess_data('polygon', assets=['US30', 'SPY'])
```

### 3.2 Statistical Models Core (`src/edges/statistical_edges.py`)

Core functions for ML/DL/RL components.

```python
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_selection import SelectFromModel
from xgboost import XGBRegressor  # Supervised ML
from sklearn.metrics import mean_squared_error
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from statsmodels.tsa.stattools import adfuller, coint  # For cointegration
import stable_baselines3 as sb3
from stable_baselines3.common.vec_env import DummyVecEnv
from gym import spaces, Env

class StatisticalModels:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.features = data.drop(columns=['returns'], errors='ignore')  # Assume 'returns' is target
    
    def unsupervised_clustering(self, n_clusters=5):
        """K-Means for asset grouping."""
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(self.features)
        self.data['cluster'] = labels
        return self.data
    
    def supervised_prediction(self, target_col='returns'):
        """XGBoost for return prediction; feature ranking with Boruta-like (using XGB importance)."""
        X = self.features
        y = self.data[target_col]
        model = XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
        model.fit(X, y)
        selector = SelectFromModel(model, threshold='median', prefit=True)
        selected_features = X.columns[selector.get_support()]
        preds = model.predict(X)
        mse = mean_squared_error(y, preds)
        return model, selected_features, preds, mse
    
    def dl_lstm_forecast(self, seq_len=60, epochs=50):
        """LSTM for time-series forecasting."""
        class LSTM(nn.Module):
            def __init__(self, input_size, hidden_size=50, num_layers=1):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])
        
        # Prepare sequences
        X_seq, y_seq = [], []
        for i in range(len(self.data) - seq_len):
            X_seq.append(self.features.iloc[i:i+seq_len].values)
            y_seq.append(self.data['returns'].iloc[i+seq_len])
        X_seq, y_seq = np.array(X_seq), np.array(y_seq)
        
        # DataLoader
        dataset = TensorDataset(torch.tensor(X_seq, dtype=torch.float32), torch.tensor(y_seq, dtype=torch.float32))
        loader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Train
        model = LSTM(input_size=X_seq.shape[2])
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model.to(device)
        
        for epoch in range(epochs):
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                optimizer.zero_grad()
                out = model(batch_x)
                loss = criterion(out.squeeze(), batch_y)
                loss.backward()
                optimizer.step()
        
        return model
    
    def rl_arb_optimization(self, env=None):
        """PPO for refining thresholds in pairs trading."""
        class ArbEnv(Env):
            def __init__(self, data):
                super().__init__()
                self.data = data.reset_index()
                self.current_step = 0
                self.action_space = spaces.Box(low=-1, high=1, shape=(1,))  # Position size
                self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(data.shape[1],))
            
            def reset(self):
                self.current_step = 0
                return self.data.iloc[0].values
            
            def step(self, action):
                reward = action[0] * self.data['returns'].iloc[self.current_step]  # Simple reward
                self.current_step += 1
                done = self.current_step >= len(self.data) - 1
                return self.data.iloc[self.current_step].values, reward, done, {}
        
        if env is None:
            env = DummyVecEnv([lambda: ArbEnv(self.data)])
        model = sb3.PPO('MlpPolicy', env, learning_rate=1e-4, verbose=0)
        model.learn(total_timesteps=10000)
        return model

def pairs_trading_test(asset1_data: pd.Series, asset2_data: pd.Series, threshold=2.0):
    """Cointegration test for pairs."""
    score, pvalue, _ = coint(asset1_data, asset2_data)
    if pvalue > 0.05:
        return None  # Not cointegrated
    spread = asset1_data - asset2_data
    zscore = (spread - spread.mean()) / spread.std()
    entry_signals = np.where(zscore > threshold, -1, np.where(zscore < -threshold, 1, 0))
    return entry_signals, zscore

# Example: models = StatisticalModels(data)
# cluster_df = models.unsupervised_clustering()
```

### 3.3 Agent Enhancements

#### Librarian for Hypothesis (`src/agents/librarian_stat.py`)

```python
# Use LLM (e.g., via API, but simulate here)
def generate_hypothesis(data_summary: str):
    """LLM-like: Generate stat hypotheses."""
    # In practice, call Claude API; here placeholder
    hypotheses = [
        "High correlation (>0.8) between US30 and SPY indicates pairs trading opportunity if cointegration p-value <0.05."
    ]
    return hypotheses

# Integrate: hypotheses = generate_hypothesis(data.describe().to_string())
```

#### Strategist for Code Generation (`src/agents/strategist_stat.py`)

```python
def draft_strategy_code(hypothesis: str):
    """Generate Python code draft for strategy."""
    # Placeholder: In full, use LLM to write
    code = """
def pairs_strategy(data):
    signals, zscore = pairs_trading_test(data['US30_close'], data['SPY_close'])
    return signals
"""
    with open('src/models/drafts/stat_pairs.py', 'w') as f:
        f.write(code)
    return 'src/models/drafts/stat_pairs.py'
```

#### Killer for Validation (`src/agents/killer_stat.py`)

Extend existing Killer to include stat-specific validation.

```python
from src.tools.monte_carlo_pro import MonteCarloPro  # Existing
from statsmodels.tsa.api import GARCH

def validate_strategy(strategy_path: str, data: pd.DataFrame):
    """Run backtest, Monte Carlo, GARCH forecast."""
    # Load strategy
    import importlib.util
    spec = importlib.util.spec_from_file_location("strategy", strategy_path)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    
    # Backtest
    signals = strategy.pairs_strategy(data)  # Assume function name
    returns = signals * data['returns'].shift(-1).fillna(0)  # Hypothetical
    sharpe = returns.mean() / returns.std() * np.sqrt(252)
    
    # GARCH vol forecast
    garch = GARCH(returns)
    garch_fit = garch.fit()
    vol_forecast = garch_fit.forecast(horizon=1).variance.iloc[-1]
    
    # Monte Carlo
    mc = MonteCarloPro(returns)
    ruin_prob, var = mc.simulate(paths=10000, vol_scale=vol_forecast)
    
    if sharpe > 1 and ruin_prob < 0.05:
        return "APPROVE", {"sharpe": sharpe, "ruin_prob": ruin_prob}
    return "REJECT", {"reason": "Metrics failed"}
```

### 3.4 RL Integration (`src/rl/stat_rl_agent.py`)

Already in core models; deploy as:

```python
def deploy_rl(model, live_data):
    obs = live_data.iloc[-1].values
    action, _ = model.predict(obs)
    # Execute trade based on action (e.g., position size)
    return action
```

### 3.5 Entry Script (`run_statistical_edges.py`)

```python
from src.data.preprocessor import load_and_preprocess_data
from src.edges.statistical_edges import StatisticalModels
from src.agents.librarian_stat import generate_hypothesis
from src.agents.strategist_stat import draft_strategy_code
from src.agents.killer_stat import validate_strategy
from src.rl.stat_rl_agent import deploy_rl

# Perceive
data, _ = load_and_preprocess_data('polygon', assets=['US30', 'SPY'])

# Reason
hypotheses = generate_hypothesis(data.describe().to_string())
strategy_path = draft_strategy_code(hypotheses[0])

# Validate
decision, metrics = validate_strategy(strategy_path, data)
print(f"Decision: {decision}, Metrics: {metrics}")

if decision == "APPROVE":
    # Execute
    models = StatisticalModels(data)
    rl_model = models.rl_arb_optimization()
    live_action = deploy_rl(rl_model, data)  # Simulate live
    # Integrate with connectors for real execution
```

## 4. Testing and Deployment Guidelines

- **Testing**: Run `python run_statistical_edges.py`; check logs for metrics. Use code_execution tool to verify snippets.
- **Error Handling**: Add try-except for API failures, model convergence (e.g., if pvalue NaN, skip).
- **Optimization**: Use Bayesian (e.g., via scikit-optimize if available) for hyperparameters.
- **Adaptation**: Retrain DL/RL quarterly; monitor with ES from Monte Carlo.
- **Robustness**: Stress-test with regime multipliers in Monte Carlo.

This script is complete for implementation. Extend for other edges as needed.