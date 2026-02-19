This `specs.md` is designed to be a "living" blueprint. It follows the **Digital FTE** architecture—utilizing **Claude Code** for reasoning, **Obsidian** for memory, and **Neon DB** for long-term institutional knowledge.

You can copy and paste the content below into a file named `specs.md` in your project root and then run: `claude "Implement the system defined in specs.md"`.

---

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

### Contextual Action Suggestion

If you're ready, I can generate the **PostgreSQL initialization script** for your Neon DB so Claude can begin building the "Institutional Memory" tables immediately. Do you want me to do that?