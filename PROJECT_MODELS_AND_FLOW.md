# Project Models & Architecture Flow

This document outlines the **Financial, AI, Reinforcement Learning (RL), and Deep Learning (DL)** models used in this project, explaining their specific roles and the data flow connecting them.

## 1. Overview: The Generative Quant Lab

The project implements an **autonomous quantitative trading factory** ("Ralph Wiggum Loop"). It uses a multi-agent system to:
1.  **Perceive** market data (Financials).
2.  **Reason** and generate strategies (AI/LLMs).
3.  **Validate** strategies through stress-testing and simulation (Financial Models & RL).
4.  **execute** trades (Financials).

---

## 2. Models by Domain

### 📊 A. Financial Models
*Used for Market Interaction, Simulation, and Risk Management.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **Monte Carlo Simulation** | `src/tools/monte_carlo_pro.py` | **Validation Flow:** Used by `KillerAgent` to run 10,000+ probabilistic simulations of a strategy's equity curve. Calculates **Probability of Ruin** and **Value at Risk (VaR)** to reject fragile strategies. |
| **Slippage & Friction Models** | `src/tools/monte_carlo_pro.py` | **Validation Flow:** Injects synthetic noise (slippage, latency shocks) into backtests to simulate real-world execution conditions. Ensures strategies aren't just "lucky" on paper. |
| **Regime Stress Testing** | `src/tools/monte_carlo_pro.py` | **Validation Flow:** Multiplies volatility by factors (e.g., 2.5x for "2020 Crash") to test how strategies behave during black swan events. |
| **Market Connectors** | `src/connectors/alpaca_connector.py`<br>`src/connectors/mt5_connector.py` | **Execution Flow:** Standardized interfaces for **Alpaca** and **MetaTrader 5**. Fetches OHLCV data and executes orders. |
| **Data Preprocessing** | `src/data/us30_loader.py` | **Data Flow:** Uses `pandas` and `numpy` to clean CSV/API data and `sklearn.MinMaxScaler` to normalize features for RL/DL model consumption. |

### 🧠 B. AI Models (Artificial Intelligence)
*Used for Reasoning, Strategy Generation, and Orchestration.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **LLM Agents (Claude/Anthropic)** | `src/agents/` <br> (`Librarian`, `Strategist`, `Killer`) | **Core Brain:** The system relies on Large Language Models to "think". <br>- **Librarian**: Analyzing needs (`Needs_Action`) and creating plans.<br>- **Strategist**: Writing Python code (`Drafts`) for new trading strategies based on plans.<br>- **Killer**: Analyzing backtest results and deciding whether to `APPROVE` or `REJECT`. |
| **Random Forest** | *Conceptual (Critic Role)* | **Critic Flow:** Mentioned in `Actor_critic_models.md` as a model for feature importance—identifying *why* a specific trade failed during analysis. |

### 🤖 C. Reinforcement Learning (RL) Models
*Used for Adaptive Strategy Optimization.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **PPO (Proximal Policy Optimization)** | `requirements.txt` (`stable-baselines3`)<br>*Conceptual in `Actor_critic_models.md`* | **Actor Flow:** The "Alpha Hunter". Designed to execute continuous actions (position sizing -1 to +1) based on market state. Preferred over DQN for its stability in non-stationary markets. |
| **The "Gym" Environment** | `Actor_critic_models.md` | **Training Flow:** A custom environment where the Actor receives **Risk-Adjusted Rewards** (Sharpe * Sortino) rather than simple P&L, punishing high-volatility gambling. |
| **Actor-Critic Architecture** | `Actor_critic_models.md` | **System Design:**<br>- **Actor**: Proposes trades.<br>- **Critic**: Adversarial agent that tries to "break" the strategy using noise injection. |

### 🕸️ D. Deep Learning (DL) Models
*Used for Pattern Recognition and Time-Series Encoding.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **Transformers** | `Actor_critic_models.md` | **Feature Extraction:** Used in the Actor's neural network to handle long-range dependencies in price data (checking past market cycles). |
| **CNN (Convolutional Neural Networks)** | `Actor_critic_models.md` | **Feature Extraction:** Used as the input layer for the Actor to recognize local visual patterns (e.g., candlestick formations) in the OHLCV data. |
| **LSTM** | `Actor_critic_models.md` | **Perception Layer:** Alternative to Transformers for simple time-series forecasting (predicting next hour's close). |
| **MinMax Scaler** | `src/data/us30_loader.py` | **Preprocessing:** Prepares data for these Neural Networks by scaling inputs to a 0-1 range. |

---

## 3. The Central Execution Flow ("Ralph Wiggum Loop")

The models interact in a continuous loop defined in `run_ralph.py`:

```mermaid
graph TD
    Data[World Data / US30] -->|Ingest| Watchers[Watchers (Research/Data)]
    Watchers -->|Save Context| Vault[Needs_Action (Vault)]
    
    Vault -->|Read Context| Librarian[🤖 Librarian Agent (AI)]
    Librarian -->|Create Plan| Plans[Plans Folder]
    
    Plans -->|Read Plan| Strategist[🧠 Strategist Agent (AI)]
    Strategist -->|Write Python Code| Drafts[src/models/drafts/*.py]
    
    Drafts -->|Load Strategy| Killer[🔪 Killer Agent (AI/Financials)]
    USD[US30 CSV Data] -->|Preprocess (sklearn)| Killer
    
    Killer -->|Run Backtest| Simulation[Financial Simulation]
    Simulation -->|Inject Noise/Slippage| Friction[Friction Models]
    Friction -->|10,000 Iterations| MonteCarlo[Monte Carlo Engine]
    
    MonteCarlo -->|Risk Metrics (VaR, Ruin)| Killer
    Killer -->|Decision (APPROVE/REJECT)| Logs[Risk Audit Logs]
```

### Detailed Step-by-Step Flow:

1.  **Perception (Financials + Data):**
    *   **Watchers** ingest raw data from the world.
    *   **US30Loader** (`src/data/us30_loader.py`) loads market data (CSV or API) and uses `sklearn` to normalize it for model consumption.

2.  **Reasoning (AI/LLM):**
    *   **Librarian Agent** identifies what needs to be done.
    *   **Strategist Agent** writes a new Python strategy file (e.g., `strategy_sma_cross.py`) into `src/models/drafts/`.

3.  **Validation (Financials + RL Concepts):**
    *   **Killer Agent** picks up the drafted strategy.
    *   It runs a base backtest using `pandas`.
    *   **MonteCarloPro** (`src/tools/monte_carlo_pro.py`) takes over:
        *   **Bootstraps** the returns (shuffles them) to test robustness.
        *   **Injects Friction** (Slippage models) to simulate real execution.
        *   **Stresses Regimes** (Simulates crashes).
    *   This implements the **"Critic"** role from RL theory—actively trying to fail the strategy.

4.  **Action (Decision):**
    *   Based on "Probability of Ruin" and "Sharpe Ratio", the Killer Agent makes a decision.
    *   **Approved** strategies are moved to production (conceptual).
    *   **Rejected** strategies move to the "Graveyard".
