# Project Models & Architecture Flow

This document outlines the **Financial, AI, Reinforcement Learning (RL), and Deep Learning (DL)** models used in this project, explaining their specific roles and the data flow connecting them.

## 1. Overview: The Generative Quant Lab

The project implements an **autonomous quantitative trading factory** ("Ralph Wiggum Loop"). It uses a multi-agent system to:
1.  **Perceive** market data (Financials).
2.  **Reason** and generate strategies (AI/LLMs).
3.  **Validate** strategies through stress-testing and simulation (Financial Models & RL).
4.  **Manage Risk** through position sizing and guardrails (Risk Architect).
5.  **Execute** trades with throttling and failover (Execution Manager).
6.  **Report** performance and audit decisions (Reporter).

---

## 2. Models by Domain

### 📊 A. Financial Models
*Used for Market Interaction, Simulation, and Risk Management.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **Monte Carlo Simulation** | `src/tools/monte_carlo_pro.py` | **Validation Flow:** Used by `KillerAgent` to run 10,000+ probabilistic simulations of a strategy's equity curve. Calculates **Probability of Ruin** and **Value at Risk (VaR)** to reject fragile strategies. |
| **Slippage & Friction Models** | `src/tools/monte_carlo_pro.py` | **Validation Flow:** Injects synthetic noise (slippage, latency shocks) into backtests to simulate real-world execution conditions. Ensures strategies aren't just "lucky" on paper. |
| **Execution Manager** | `src/connectors/execution_manager.py` | **Action Flow:** Implements a **Token-Bucket Throttler** and **Multi-Account Failover**. Manages order queuing, batching, and rate-limiting (e.g., Alpaca's 200 orders/min limit). |
| **Market Connectors** | `src/connectors/alpaca_connector.py`<br>`src/connectors/mt5_connector.py` | **Execution Flow:** Standardized interfaces for **Alpaca** and **MetaTrader 5**. Fetches OHLCV data and executes orders. |
| **Data Preprocessing** | `src/data/us30_loader.py` | **Data Flow:** Uses `pandas` and `numpy` to clean CSV/API data and `sklearn.MinMaxScaler` to normalize features for RL/DL model consumption. |

### 🧠 B. AI Models (Artificial Intelligence)
*Used for Reasoning, Strategy Generation, and Orchestration.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **LLM Agents (Claude/Anthropic)** | `src/agents/` | **Core Brain:** The system relies on Large Language Models to "think" and orchestrate the loop. |
| **Librarian Agent** | `src/agents/librarian_agent.py` | **Reasoning:** Analyzes needs (`Needs_Action`) and creating structured plans for the factory. |
| **Strategist Agent** | `src/agents/strategist_agent.py` | **Generation:** Writing Python code (`Drafts`) for new trading strategies based on plans. |
| **Killer Agent** | `src/agents/killer_agent.py` | **Validation:** Adversarial agent that stress-tests drafts. **Approval Criteria:** Must hit >10% return and <12% max drawdown in simulated paths. |
| **Risk Architect Agent** | `src/agents/risk_architect.py` | **Guardrails:** Computes **Fractional Kelly** sizing, **Volatility Targeting**, and enforces **Consecutive Loss Cooldowns**. |
| **Reporter Agent** | `src/agents/reporter.py` | **Audit:** Scans logs and accounting data to generate "Monday Morning Briefings" with P&L and audit stats. |
| **Discovery Lab** | `src/tools/discovery_lab.py` | **Interaction:** Streamlit-based lab for "What-If" backtests, regime scanning, and **SHAP** feature importance analysis. |

### 🤖 C. Reinforcement Learning (RL) Models
*Used for Adaptive Strategy Optimization.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **PPO (Proximal Policy Optimization)** | `requirements.txt` (`stable-baselines3`) | **Actor Flow:** Designed for continuous action spaces (position sizing -1 to +1). |
| **The "Gym" Environment** | `Actor_critic_models.md` | **Training Flow:** Custom environment where rewards are **Risk-Adjusted** (Sharpe * Sortino), punishing high-volatility gambling. |
| **Actor-Critic Architecture** | `Actor_critic_models.md` | **System Design:**<br>- **Actor**: Proposes trades.<br>- **Critic**: Adversarial agent (Killer Agent) that tries to "break" the strategy using noise. |

### 🕸️ D. Deep Learning (DL) Models
*Used for Pattern Recognition and Time-Series Encoding.*

| Model / Concept | Implementation File(s) | Role & Flow |
| :--- | :--- | :--- |
| **Transformers** | `Actor_critic_models.md` | **Feature Extraction:** Used for handling long-range dependencies in price data. |
| **CNN (Convolutional Neural Networks)** | `Actor_critic_models.md` | **Feature Extraction:** Used to recognize local visual patterns (e.g., candlestick formations). |
| **MinMax Scaler** | `src/data/us30_loader.py` | **Preprocessing:** Prepares data for Neural Networks by scaling inputs to a 0-1 range. |

---

## 3. The Central Execution Flow ("Ralph Wiggum Loop")

The models interact in a continuous loop defined in `run_ralph.py` and supported by orchestration layers:

```mermaid
graph TD
    Data[World Data / US30] -->|Ingest| Watchers[Watchers (Research/Data)]
    Watchers -->|Save Context| Vault[Needs_Action (Vault)]
    
    Vault -->|Read Context| Librarian[🤖 Librarian Agent (AI)]
    Librarian -->|Create Plan| Plans[Plans Folder]
    
    Plans -->|Read Plan| Strategist[🧠 Strategist Agent (AI)]
    Strategist -->|Write Python Code| Drafts[src/models/drafts/*.py]
    
    Drafts -->|Load Strategy| Killer[🔪 Killer Agent (AI/Financials)]
    Killer -->|Run Stress Tests| MonteCarlo[Monte Carlo Engine]
    
    MonteCarlo -->|Criteria: 10% Ret / 12% DD| Killer
    Killer -->|APPROVE| Production[src/models/production/]
    
    Production -->|Active Strategy| Risk[🛡️ Risk Architect (AI)]
    Risk -->|Size/Guardrails| Execution[⚡ Execution Manager]
    Execution -->|Throttled Orders| Market[Market (MT5/Alpaca)]
    
    Market -->|Trade Logs| Accounting[Vault/Accounting]
    Accounting -->|Performance| Reporter[📝 Reporter Agent (AI)]
    Reporter -->|Weekly Briefing| Reports[Vault/Reports]
```

### Detailed Step-by-Step Flow:

1.  **Perception (Financials + Data):**
    *   **Watchers** ingest raw data. **US30Loader** normalizes it using `sklearn`.

2.  **Reasoning (AI/LLM):**
    *   **Librarian Agent** creates plans.
    *   **Strategist Agent** writes Python strategies into `src/models/drafts/`.

3.  **Validation (The Critic):**
    *   **Killer Agent** stress-tests drafts using **MonteCarloPro**.
    *   **Approval Gate:** Strategy must maintain >10% profitability and <12% drawdown across 10k simulations with injected slippage.

4.  **Risk & Action (Production):**
    *   Approved strategies are picked up for live/paper execution.
    *   **Risk Architect Agent** calculates Kelly-fractional position sizes and monitors for "Cooldown" conditions (e.g., 3 consecutive losses).
    *   **Execution Manager** handles the actual API calls, ensuring rate limits aren't hit and using backup accounts if necessary.

5.  **Reporting (Feedback Loop):**
    *   **Reporter Agent** aggregates "Risk Audit" logs and "Accounting" P&L to produce a weekly summary, closing the loop with performance visibility.
