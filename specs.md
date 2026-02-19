
# Technical Specification: Autonomous Alpha Research & Execution FTE

## 1. System Vision & Objective

To build a multi-agent "Digital Employee" that functions as a Senior Quant Researcher. The system must autonomously transform raw information (papers, news) into validated, risk-managed trading alphas for US30 and other financial markets. The architecture is modular to ensure a **10 year lifecycle**, allowing for the replacement of individual LLMs or models without breaking the core workflow.

## 2. Infrastructure & Tech Stack

* **Reasoning Engine**: Claude Code (via CCR) / Agentic Workflows.
* **Memory (Dashboard/GUI)**: Obsidian Vault (Local-first).
* **Long-term Memory**: Neon DB (PostgreSQL + pgvector).
* **Compute**: GCP (Cloud Run/Functions for 24/7 watchers).
* **Environment**: Docker on WSL2.
* **Languages/Libs**: Python (Pandas, Numpy, Stable-Baselines3, Scikit-Learn, Asyncpg).

## 3. Core Agentic Workflow (The Factory Line)

### A. The Librarian (Ingestion & Comparison)

* **Input**: Watcher monitors `Obsidian_Vault/Needs_Action` for PDFs, URLs, or text snippets.
* **Logic**: Use LLM to extract "Core Alpha Hypothesis" from text.
* **Fundamental Filter**: Compare hypothesis against a "Market Theory Knowledge Base" (EMH, Mean Reversion, Momentum, etc.) stored in Neon DB.
* **Output**: A structured `RESEARCH_PLAN.md` in the `/Plans` folder.

### B. The Strategist (Scenario Generation)

* **Logic**: Transform the qualitative research plan into quantitative Python code.
* **Task**: Define the entry/exit logic and the "Ideal Market Regime" for the strategy.
* **Output**: A Python test script stored in `src/models/drafts/`.

### C. The Monte Carlo Engine (Edge Validation)

* **Function**: Run **Monte Carlo Simulations** (10,000+ iterations) to determine the probability of the edge being "real" rather than random noise.
* **Moat**: Stress-test the edge by shuffling the OHLCV data to ensure the strategy doesn't survive on luck.

### D. The Regime Analyst (Cross-Market Robustness)

* **Timeframe Analysis**: Test across 1m, 5m, 1h, and 1D timeframes.
* **Regime Testing**: Force the strategy through "High Volatility" (2020), "Bear Market" (2022), and "Trending" regimes.
* **Variations**: Test US30 strategy logic on correlated assets (e.g., GER40, NAS100) to find "Characteristic Drift."

### E. The Risk Architect (Execution & Sizing)

* **Optimization**: Run RL agents (PPO/DQN) to find optimal **Position Sizing** (Kelly Criterion) and Stop-Loss/Take-Profit ratios.
* **Behavioral Patch**: Integrate "Guardrail" checks for the **Disposition Effect** (closing winners too early) and **FOMO** (entering late).

## 4. Database Schema (Neon DB)

* `alphas`: Stores validated strategy parameters and historical Sharpe ratios.
* `strategy_graveyard`: Stores failed hypotheses with a "Reason for Failure" (e.g., "Inconsistent in low-volatility regimes").
* `market_regimes`: Metadata on US30 historical periods for cross-regime testing.

## 5. Development Milestones (The "Baby Steps")

### Phase 1: The Skeleton

1. Initialize the **Obsidian Vault** folder structure.
2. Setup `db_handler.py` to connect to Neon.
3. Implement the `BaseWatcher` in Python to detect new files in `/Needs_Action`.

### Phase 2: The Logic Engine

1. Implement the **Monte Carlo** tool as a Python skill for Claude.
2. Build the **US30 Data Loader** that pulls from your CSV/dataset.
3. Configure the **Ralph Wiggum Loop** to iterate from `Plan` -> `Monte Carlo` -> `Done`.

### Phase 3: The Adversarial Moat

1. Implement the **"Killer Agent"** logic that injects synthetic slippage and noise into every backtest.
2. Build the **Monday Morning CEO Briefing** generator in Obsidian.

## 6. Security & Human-in-the-Loop (HITL)

* **Safety**: No trade can be "Live" without a manual file move to the `/Approved` folder.
* **Isolation**: Docker containers must have limited access to the local filesystem outside of the Vault and `src` folders.

---

## 7. Specialized Actor-Critic Implementation (Alpha Hunter + Adversarial Critic)

The system uses an **Actor-Critic** workflow: the **Actor** ("Alpha Hunter") generates hypotheses and entry/exit logic; the **Critic** ("Adversarial Risk Manager") stress-tests strategies and blocks curve-fitting.

### A. Environment (The Gym)

- **Reward Function**: Risk-adjusted reward (e.g. Sharpe × Sortino) to punish high-volatility gambling, not raw P&L.
- **State Space**: OHLCV, RSI, ATR (volatility), and Time-of-Day (US30 session logic).

### B. Actor Neural Network

- **Primary Model**: PPO (Proximal Policy Optimization) for stable, non-stationary markets.
- **Input**: 1D CNN for local pattern recognition (e.g. candlestick patterns).
- **Hidden**: Transformer Encoder for long-range dependencies (e.g. session opens, volatility spikes).
- **Output**: Tanh activation for continuous position sizing (**conviction level** -1 to +1).

### C. Critic Neural Network

- **Architecture**: Multi-headed value network (Expected Return, MDD, VaR).
- **Input**: Shared CNN/Transformer representation with the Actor.
- **Evaluation**: TD (Temporal Difference) error vs. Buy & Hold / Random Walk baseline.
- **Validation**: Synthetic noise injection (pip jitter, volume shuffle); 10,000+ Monte Carlo permutations for Probability of Ruin.

### D. Validation Moat Pipeline

1. **Actor** proposes a strategy signal.
2. **Critic** runs a **Noise Stress Test** (random pip jitter).
3. **Critic** runs a **Liquidity Stress Test** (simulated 2–3 pip slippage).
4. **Final gate**: Strategy moves to `Obsidian_Vault/Done` only if **Probability of Profit** remains > 60% across 5,000 Monte Carlo iterations.

### E. Model Roles in the FTE

| Model Type      | Best For                 | Role in FTE                          |
|-----------------|--------------------------|--------------------------------------|
| **PPO (RL)**    | Continuous decisions     | **Actor** (strategic execution)      |
| **LSTM (DL)**   | Time-series forecasting  | **Perception layer** (e.g. next hour)|
| **Random Forest** | Feature importance     | **Critic** (why a trade failed)      |
| **Transformer** | Complex pattern recognition | **Brain** (e.g. 10y US30 data)   |

See **docs/ACTOR_CRITIC_SPECS.md** and **database/schema_actor_critic.sql** for full Actor-Critic DB schema (pgvector, backtest_logs) and implementation details.

---

