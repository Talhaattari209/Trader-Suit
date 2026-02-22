# Implementation Script for Pattern-Based Edges in Generative Quant Lab

This Markdown script provides a detailed, step-by-step guide for implementing **Pattern-Based Edges** within the autonomous quantitative trading factory ("Ralph Wiggum Loop"). It is designed to prevent hallucinations in coding agents (e.g., LLMs like Claude) by specifying exact libraries, code structures, hyperparameters, file paths, and integration points. All implementations tie into the existing project architecture, including agents (Librarian, Strategist, Killer), financial models (e.g., Monte Carlo, GARCH), AI techniques (ML, DL, RL, PCA), and connectors (e.g., Alpaca, MT5).

Focus: Pattern-based edges identify recurring chart formations (e.g., head-and-shoulders, double tops/bottoms, candlestick patterns like doji or engulfing) to generate trading signals. Enhance with AI for automation: ML for classification, DL for pattern detection, RL for optimization, and agentic workflows for hypothesis/refinement.

**Key Principles**:
- Hypothesis-first: Start with scientific method (e.g., "Hypothesize that head-and-shoulders predicts reversals in trending markets").
- Modularity: Code as separate modules in `src/` for easy integration.
- Scalability: Handle 1,000+ assets/charts; use GPU via PyTorch for DL; parallel processing with NumPy/Pandas.
- Risk Integration: Embed volatility-adjusted stops (GARCH), simulations (Monte Carlo with GBM), and risk metrics (Sharpe >1, drawdown <20%).
- Libraries: Use only available ones (e.g., pandas, numpy, scikit-learn, torch, stable-baselines3). No pip installs.
- Data: Assume US30 or similar OHLCV from `src/data/us30_loader.py`; extend to multi-asset via Polygon API.

## 1. Overview

- **Edge Description**: Detect visual/sequential patterns in price data for entry/exit signals. Examples: Classical (head-and-shoulders, flags), Candlesticks (hammer, shooting star).
- **Automation Enhancements**:
  - ML: Ensemble classifiers (Random Forest) for pattern labeling; Boruta for feature selection.
  - DL: CNNs for image-based detection (treat charts as images); RNNs/LSTMs for sequence-based (e.g., candlestick series).
  - RL: PPO agent trains on historical patterns to learn optimal actions (e.g., position size, stops); rewards based on risk-adjusted returns.
  - Agentic: Multi-agent LLMs (via Claude API) for pattern description, hypothesis generation, and consensus (e.g., Pattern Agent debates with Risk Agent).
- **Integration with Ralph Loop**: Perceive (data ingest), Reason (agent hypothesis/code gen), Validate (backtest/sim), Execute (RL deployment).
- **Scalability Goals**: Process 1,000 charts/hour; low-latency inference (<50ms); quarterly retrain.
- **Ethical/Risk**: Explainability via SHAP; bias checks; circuit breakers if pattern confidence <70%.

## 2. File Structure and Dependencies

Add/update files in `src/`:
- `src/edges/pattern_based/` (new folder): Core implementations.
  - `pattern_detector_ml.py`: ML classifiers and Boruta.
  - `pattern_detector_dl.py`: CNN/RNN models.
  - `pattern_rl_agent.py`: PPO for optimization.
  - `pattern_agent.py`: Agentic LLM workflows.
  - `pattern_workflow.py`: Central orchestration script.
- Dependencies: Import explicitly in code.
  - Data: `pandas`, `numpy`, `sklearn` (for ML/PCA/MinMaxScaler).
  - DL: `torch` (nn, optim, datasets).
  - RL: `stable_baselines3` (PPO, Gym env).
  - Financial: Reuse `src/tools/monte_carlo_pro.py`, `src/tools/volatility_models.py` (GARCH).
  - Agents: Reuse `src/agents/` (Librarian, etc.); assume Claude API wrapper in `src/agents/claude_api.py`.
  - Connectors: `src/connectors/alpaca_connector.py` for data/exec.

## 3. Data Preparation (Perceive Phase)

- **Input**: OHLCV data (Open, High, Low, Close, Volume) from CSV/API.
- **Preprocessing**:
  - Normalize with MinMaxScaler.
  - Convert to images for CNN: Use Matplotlib to render candlestick charts as arrays.
  - Apply PCA for feature reduction (e.g., on technical indicators like RSI, MACD).
- **Code Snippet** (in `src/data/pattern_preprocessor.py` - new file):
  ```python
  import pandas as pd
  import numpy as np
  from sklearn.preprocessing import MinMaxScaler
  from sklearn.decomposition import PCA
  import matplotlib.pyplot as plt
  from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
  from io import BytesIO

  def preprocess_ohlcv(df: pd.DataFrame, window_size: int = 60) -> dict:
      # Normalize
      scaler = MinMaxScaler()
      scaled_data = scaler.fit_transform(df[['open', 'high', 'low', 'close', 'volume']])
      
      # PCA reduction (retain 95% variance)
      pca = PCA(n_components=0.95)
      reduced_features = pca.fit_transform(scaled_data)
      
      # Generate image for CNN (e.g., candlestick chart)
      def chart_to_image(ohlcv_window: pd.DataFrame) -> np.ndarray:
          fig, ax = plt.subplots(figsize=(5, 5))
          # Plot candlesticks (simplified; use mplfinance if available, but stick to matplotlib)
          for i, row in ohlcv_window.iterrows():
              color = 'g' if row['close'] > row['open'] else 'r'
              ax.plot([i, i], [row['low'], row['high']], color='black')
              ax.add_patch(plt.Rectangle((i-0.2, min(row['open'], row['close'])), 0.4, abs(row['close']-row['open']), color=color))
          canvas = FigureCanvas(fig)
          buf = BytesIO()
          canvas.print_png(buf)
          buf.seek(0)
          img = np.frombuffer(buf.getvalue(), dtype=np.uint8).reshape((500, 500, -1))  # Adjust size
          plt.close(fig)
          return img
      
      images = []
      for i in range(len(df) - window_size):
          window = df.iloc[i:i+window_size]
          images.append(chart_to_image(window))
      
      return {'scaled': scaled_data, 'reduced': reduced_features, 'images': np.array(images)}
  ```
- **Usage**: Call in Watchers: `preprocessed = preprocess_ohlcv(load_us30_data())`.

## 4. Reasoning Phase (Agentic Hypothesis and Strategy Generation)

- **Agents Involved**:
  - **Pattern Agent**: LLM describes patterns (e.g., "Detect head-and-shoulders: left shoulder high, head higher, right shoulder symmetric").
  - **Strategist Agent**: Generates Python code for detection/integration.
  - **Debate**: Multi-agent consensus (e.g., Pattern Agent proposes, Risk Agent adjusts for vol).
- **Hypothesis Generation**: Use LLM prompts for scientific method.
- **Code Snippet** (in `src/edges/pattern_based/pattern_agent.py`):
  ```python
  from src.agents.claude_api import call_claude  # Assume wrapper: def call_claude(prompt: str) -> str

  def generate_pattern_hypothesis(pattern_type: str = 'head_and_shoulders') -> str:
      prompt = f"""
      Hypothesis: {pattern_type} patterns predict reversals in trending markets.
      Generate a detailed hypothesis including:
      - Definition: e.g., Head higher than shoulders, neckline breakout.
      - Entry: Short on neckline break for bearish.
      - Exit: Target = head height projected down.
      - Risk: Stop above head.
      - Validation: Require volume confirmation > avg.
      Avoid data mining; base on auction theory.
      """
      return call_claude(prompt)

  def agent_debate(hypothesis: str) -> str:
      risk_prompt = f"Refine hypothesis '{hypothesis}' for risk: Integrate GARCH vol for stops. Debate pros/cons."
      refined = call_claude(risk_prompt)
      return refined

  # Integrate with Strategist: Generate code draft
  def generate_strategy_code(refined_hyp: str) -> str:
      code_prompt = f"Write Python function for {refined_hyp} using pandas for detection, return signal (1 buy, -1 sell, 0 hold)."
      return call_claude(code_prompt)
  ```
- **Flow**: Librarian triggers: hyp = generate_pattern_hypothesis(); refined = agent_debate(hyp); code = generate_strategy_code(refined); save to `src/models/drafts/pattern_strategy.py`.

## 5. Validation Phase (ML/DL Detection and Backtesting)

- **ML Detection**: Random Forest ensemble; Boruta for features.
- **DL Detection**: CNN for images; LSTM for sequences.
- **Backtesting**: Integrate with Killer; use Monte Carlo/GARCH.
- **Code Snippet** (in `src/edges/pattern_based/pattern_detector_ml.py`):
  ```python
  from sklearn.ensemble import RandomForestClassifier
  from sklearn.feature_selection import BorutaPy
  from sklearn.metrics import accuracy_score
  import numpy as np

  def ml_pattern_classifier(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:  # y: labels (0 no pattern, 1 pattern)
      # Boruta feature selection
      rf = RandomForestClassifier(n_estimators=100, max_depth=10)
      boruta = BorutaPy(rf, n_estimators='auto', verbose=0)
      boruta.fit(X, y)
      selected_features = X[:, boruta.support_]
      
      # Train ensemble
      rf.fit(selected_features, y)
      return rf

  def detect_pattern_ml(model: RandomForestClassifier, new_data: np.ndarray) -> int:
      pred = model.predict(new_data)
      return pred[0]  # Signal
  ```
- **DL Snippet** (in `src/edges/pattern_based/pattern_detector_dl.py`):
  ```python
  import torch
  import torch.nn as nn
  import torch.optim as optim

  class PatternCNN(nn.Module):
      def __init__(self):
          super().__init__()
          self.conv1 = nn.Conv2d(3, 32, kernel_size=3)  # Assume RGB images
          self.pool = nn.MaxPool2d(2, 2)
          self.fc1 = nn.Linear(32 * 248 * 248, 128)  # Adjust based on image size
          self.fc2 = nn.Linear(128, 3)  # Classes: buy, sell, hold

      def forward(self, x):
          x = self.pool(torch.relu(self.conv1(x)))
          x = x.view(-1, 32 * 248 * 248)
          x = torch.relu(self.fc1(x))
          return self.fc2(x)

  def train_cnn(data_loader, epochs=10):
      model = PatternCNN()
      criterion = nn.CrossEntropyLoss()
      optimizer = optim.Adam(model.parameters(), lr=0.001)
      for epoch in range(epochs):
          for images, labels in data_loader:
              optimizer.zero_grad()
              outputs = model(images)
              loss = criterion(outputs, labels)
              loss.backward()
              optimizer.step()
      return model

  class PatternLSTM(nn.Module):
      def __init__(self, input_size=5, hidden_size=50):
          super().__init__()
          self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
          self.fc = nn.Linear(hidden_size, 3)

      def forward(self, x):
          _, (hn, _) = self.lstm(x)
          return self.fc(hn.squeeze(0))
  ```
- **Validation Flow**: Killer loads draft; runs backtest on pandas df; applies Monte Carlo (10,000 paths with GBM: dS = μ dt + σ dW); GARCH for vol stops (e.g., stop = close + 2*σ from EGARCH); reject if accuracy <70% or Sharpe <1.

## 6. Execution Phase (RL Optimization and Deployment)

- **RL**: PPO agent learns from patterns; rewards = Sharpe * (1 - drawdown).
- **Code Snippet** (in `src/edges/pattern_based/pattern_rl_agent.py`):
  ```python
  from stable_baselines3 import PPO
  from stable_baselines3.common.env_util import make_vec_env
  from gym import spaces
  import gym

  class PatternEnv(gym.Env):
      def __init__(self, data: pd.DataFrame):
          self.observation_space = spaces.Box(low=0, high=1, shape=(60, 5))  # Normalized window
          self.action_space = spaces.Box(low=-1, high=1, shape=(1,))  # Position size
          self.data = data
          self.current_step = 0

      def reset(self):
          self.current_step = 0
          return self.data.iloc[self.current_step:self.current_step+60].values.flatten()

      def step(self, action):
          # Simulate trade based on pattern signal
          reward = action * (self.data['close'].pct_change().iloc[self.current_step+1])  # Simplified
          self.current_step += 1
          done = self.current_step >= len(self.data) - 60
          return self.data.iloc[self.current_step:self.current_step+60].values.flatten(), reward, done, {}

  def train_rl_pattern(data: pd.DataFrame):
      env = make_vec_env(lambda: PatternEnv(data), n_envs=1)
      model = PPO("MlpPolicy", env, learning_rate=1e-4, verbose=0)
      model.learn(total_timesteps=10000)
      return model

  def execute_pattern_rl(model: PPO, state: np.ndarray) -> float:
      action, _ = model.predict(state)
      return action[0]  # Position
  ```
- **Deployment**: In `run_ralph.py`, if approved: Load RL model; fetch real-time data; detect pattern; adjust with RL; execute via Alpaca (e.g., `alpaca.submit_order(symbol='US30', qty=abs(action), side='buy' if action>0 else 'sell')`).

## 7. Full Workflow Orchestration

- **Script** (in `src/edges/pattern_based/pattern_workflow.py`):
  ```python
  from src.data.us30_loader import load_us30_data
  from .pattern_preprocessor import preprocess_ohlcv
  from .pattern_agent import generate_pattern_hypothesis, agent_debate, generate_strategy_code
  from .pattern_detector_dl import train_cnn  # Or ML
  from .pattern_rl_agent import train_rl_pattern, execute_pattern_rl
  from src.tools.monte_carlo_pro import run_monte_carlo  # Assume function
  from src.agents.killer import killer_decision  # Assume

  def run_pattern_edge():
      df = load_us30_data()
      preprocessed = preprocess_ohlcv(df)
      
      hyp = generate_pattern_hypothesis()
      refined = agent_debate(hyp)
      strategy_code = generate_strategy_code(refined)  # Save to drafts
      
      # Train models (example DL)
      data_loader = torch.utils.data.DataLoader(preprocessed['images'], batch_size=32)  # Assume labels prepared
      cnn_model = train_cnn(data_loader)
      
      # Validate
      sim_results = run_monte_carlo(strategy_code, df)  # Inject GARCH vol
      decision = killer_decision(sim_results)  # APPROVE/REJECT
      
      if decision == 'APPROVE':
          rl_model = train_rl_pattern(df)
          # Live loop
          while True:
              live_state = get_live_data()  # From connectors
              signal = detect_pattern_ml(...)  # Or DL
              action = execute_pattern_rl(rl_model, live_state)
              execute_trade(action)
  ```
- **Monitoring**: Log to `risk_audit_logs.txt`; retrain if Sharpe drops <1.

## 8. Testing and Refinement

- **Unit Tests**: Add in `tests/test_pattern_edge.py` (use pytest if available, else manual).
  - Test detection accuracy on synthetic data (e.g., generate head-and-shoulders with NumPy).
- **Optimization**: Bayesian via scipy.optimize; RL online learning.
- **Adaptation**: Retrain DL/RL quarterly; agent reflection: LLM prompt "Reflect on performance: Sharpe=1.2, improve?".
- **Robustness**: Stress with 2.5x vol; bias correction in Boruta.

This script is self-contained; implement sequentially to avoid errors. If issues, debug with code_execution tool.