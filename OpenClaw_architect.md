This specs.md has been updated to embed professional trading practices for isolating setups and edges. These are integrated into the system's philosophy, functional requirements (especially the Ralph Wiggum Loop), and non-functional aspects to ensure the Alpha Research Factory emphasizes a systematic, data-driven process: hypothesis testing, simplification, risk management, and iteration. Unlike retail approaches chasing "holy grail" strategies, the system focuses on identifying repeatable, quantifiable advantages in specific market conditions—such as regimes (trending vs. ranging), timeframes (e.g., intraday vs. swing), sessions (e.g., London open), or asset classes (e.g., equities vs. forex). The goal is to build a portfolio of narrow, high-conviction setups that can be executed mechanically or discretionarily, maximizing opportunities while minimizing overlap or dilution.

This embedded approach avoids overgeneralization by breaking down the market into isolated components where an edge can be proven statistically (e.g., via backtesting on 10+ years of data) and refined over time. Insights from quantitative trading practices, trader anecdotes, and empirical research are woven in, with key methods mapped to agents and examples used as templates for hypothesis generation and validation.

Technical Specification: The Alpha Research & Execution Factory
1. System Philosophy
This project implements a 10-year modular architecture where AI agents are treated as Digital FTEs (Full-Time Equivalents). The system is split into two distinct layers:

OpenClaw (The Brain & Business): Proactive reasoning, strategy generation, human-in-the-loop (HITL) coordination, and executive reporting (Gmail/Telegram). Enhanced with professional practices: Agents prioritize hypothesis-driven isolation of edges, focusing on repeatable advantages in isolated market components (e.g., regime-specific setups) to build a diversified portfolio of 5-10 narrow strategies.

Nano Claw (The Muscle & Senses): High-frequency market sensing (Watchers), Zero-MQL execution, and local process persistence (PM2). Bolstered by data-driven iteration: Emphasizes statistical proof (e.g., e-ratio >1.5, Sharpe >1) and regime tagging for execution in specific conditions only.

2. Functional Requirements: The "Ralph Wiggum" Loop
The loop embeds professional methods for isolating setups/edges, starting with hypothesis generation from observations/anecdotes, rigorous empirical testing, simplification, regime tagging, risk-focused execution, and continuous refinement. This ensures setups are narrow, high-conviction, and stacked across regimes/timeframes/sessions for maximum executions (e.g., 5-10 daily opportunities). Examples of isolated setups (e.g., Pattern Failure Short) serve as templates stored in Neon DB for initial hypothesis seeding.

A. Ingestion & Perception (Librarian Agent)
Input: Watcher monitors Obsidian_Vault/Needs_Action for research papers (PDFs), news, or data CSVs.

Logic: Extract core Alpha hypotheses using professional hypothesis generation: Start with market observations/anecdotes (e.g., from trader insights or clustering anomalies via K-means in ML). Hypothesize edges based on why they exist (e.g., institutional behavior in specific regimes). Compare against "Institutional Memory" in Neon DB to avoid redundant research, tagging by regime (trending vs. ranging via Hurst exponent), timeframe, session, or asset class.

Output: Structured RESEARCH_PLAN.md with defined parameters for testing, including initial regime filters and e-ratio targets.

B. Generation & Drafting (Strategist Agent)
Task: Autonomously write Python code for the proposed strategy, embedding model simplification: Reduce parameters to 2-3 high-impact variables (e.g., via feature selection like Boruta). Isolate to specific contexts (e.g., "only if VIX >20" for high-vol regimes).

Target: src/models/drafts/[Strategy_Name].py.

Standard: Must follow the BaseStrategy interface to ensure compatibility with the backtester. Incorporate regime tagging (e.g., Hurst exponent checks) and setup templates from examples (e.g., Momentum Breakout Long criteria).

C. The Adversarial Moat (Killer Agent)
Validation: Embed rigorous backtesting: Run Monte Carlo Pro simulations (10k+ iterations) on 10+ years of data (e.g., OHLCV via Polygon API). Tag by conditions (e.g., session-specific) and use metrics like Sharpe (>1), max drawdown (<20%), hit rate (>55%), and e-ratio (>1.5). Walk-forward and out-of-sample testing to confirm isolation in regimes.

Stress Test: Inject Synthetic Noise (1-2 pip jitter) and Liquidity Shocks (2-3 pip slippage). Analyze sample size (e.g., 50+ trades) and regime-specific performance (e.g., volatility clustering).

Approval Gate: Strategy must maintain >10% return and <12% Max Drawdown, with proven edge in isolated components (e.g., no overlap with other setups). Approved strategies move to src/models/production/, with "graveyard" post-mortems for failures.

D. Adaptive Optimization (RL/DL Hunter)
Models: Use PPO (Proximal Policy Optimization) for position sizing and Transformers for feature encoding, embedding execution/psychology focus: Adapt for entry timing and risk (e.g., strict stops based on LOD distance).

Gym Env: A custom US30 environment where rewards are Risk-Adjusted (Sharpe * Sortino), refined quarterly for market shifts.

E. Risk & Execution (Risk Architect & Manager)
Sizing: Implementation of Fractional Kelly Criterion and Volatility Targeting, with pro tips: Size based on risk tolerance (e.g., 1% per trade), adaptive via RL.

Execution: Throttled order injection via Alpaca API or MT5 Zero-MQL bridge, mechanical/discretionary based on setup isolation (e.g., trail stops with ATR for momentum breakouts).

Guardrails: Automatic "Cooldown" triggers after 3 consecutive losses. Track order-level data (e.g., slippage) and psychology (e.g., journal tags for calm execution in ugly markets).

3. Non-Functional Requirements: Stability & Moat
A. Persistence (The Nano Claw Supervisor)
Process Management: All watchers and connectors must run under PM2.

Auto-Restart: If a US30 data stream crashes, PM2 must restart the process immediately.

State Continuity: Agent "thoughts" and current task states must be logged to Neon DB every 60 seconds to survive system reboots, including regime tags and iteration history for continuous refinement.

B. Security & Integrity (HITL)
Human-in-the-Loop: High-leverage or live-account trades require a manual file move from /Plans to /Approved. Avoid edge dilution by not copying untested setups.

Zero-MQL: No logic is stored in the MT5 terminal. All execution is handled via Python to maintain a unified code repository.

C. Scalability & Modularity
Serverless Hybrid: Heavy training runs on local GPU; 24/7 sensing/monitoring runs on GCP Cloud Run (Free Tier). Automate quarterly retraining for adaptation.

Database: Use PostgreSQL (pgvector) on Neon for "Institutional Memory" of every successful and failed strategy, including tagged setups (e.g., by regime/session) and example templates.

4. The Business Layer (OpenClaw)
A. Monday Morning CEO Briefing
Logic: Every Monday at 08:00, the Reporter Agent audits Neon DB, embedding performance reviews: Analyze isolated edges (e.g., per setup in portfolio) with drawdown patterns and regime shifts.

Delivery: Emails a formatted report (via Gmail API) and posts a summary to a private Telegram Channel.

Metrics: P&L, Sharpe Ratio, Signal Decay stats, "Strategy Graveyard" post-mortems, and edge quantification (e.g., e-ratio per regime).

B. Mobile Command Center (Telegram)
Commands: /status (Current P&L), /pause (Emergency Halt), /approve (Execute pending signal).

Alerts: Immediate notification if the Risk Architect triggers a circuit breaker, or if regime shifts dilute an edge.

5. Directory Structure & Standards
Plaintext
/
├── .env                        # API Keys (Neon, Alpaca, MT5, Google)
├── ecosystem.config.js         # PM2 Configuration
├── Obsidian_Vault/             # GUI & Interaction Hub
│   ├── /Needs_Action           # Perception Queue (e.g., for hypothesis seeding with examples)
│   ├── /Approved               # HITL Execution Queue
│   └── /Reports                # CEO Briefings (including regime-tagged metrics)
├── src/
│   ├── agents/                 # OpenClaw (Librarian, Killer, Reporter) – enhanced with pro methods
│   ├── connectors/             # Nano Claw (Alpaca, MT5 Zero-MQL)
│   ├── models/                 # RL/DL Model definitions, with setup templates
│   └── tools/                  # Monte Carlo, DB Handlers (e.g., for regime clustering)
└── tests/                      # Unit tests for 10-year reliability, including backtesting examples

Implementation Instructions for Coding Agent
Initialize Infrastructure: Build the BaseAgent and BaseConnector classes first to ensure modularity. Embed regime tagging in BaseStrategy.

Setup Memory: Implement the Neon DB schema for alphas and strategy_graveyard, adding fields for regime/timeframe/session tags, e-ratio, and example-based templates.

Boot Senses: Implement the US30 Data Watcher under PM2 supervision, with anomaly scanning for hypothesis generation.

Activate Loop: Use the Ralph Wiggum Loop to iterate from raw research to a Monte-Carlo-validated production model, starting with pro methods (e.g., backtest one example setup via code_execution if needed) and refining quarterly.