## Enhanced Technical Specification: The Alpha Research & Execution Factory

This updated specs.md incorporates three new tasks:
- **Task 1**: Add a feature for detailed failure analysis and alpha decay reasoning in the strategy graveyard, presented as professional journal entries. This enhances post-mortems to categorize failure modes (e.g., overfitting, regime shifts) with key metrics, descriptions, and mitigations, drawing from quantitative trading best practices.
- **Task 2**: Embed comprehensive market elements into the execution algorithm (Risk Architect & Manager) and validation (Killer Agent). This includes parametrizable simulations of market types (e.g., order-driven vs. quote-driven), market maker approaches (e.g., bid-ask spreads, delta-neutral), order types (e.g., market, limit, stop), and infrastructure (e.g., latency, clearing). Backtests will vary params to test robustness and uncover hidden edges.
- **Task 3**: Specify implementation locations for agent skills (reusable modular functions), MCP (Monte Carlo Pro simulations), subagents (specialized isolated workers via skills/classes), and agent teams (coordinated groups in loops, e.g., Librarian + Strategist team).

The system remains a 10-year modular architecture treating AI agents as Digital FTEs, with OpenClaw (brain) and NanoClaw (muscle) layers, emphasizing professional edge isolation.

1. System Philosophy
This project implements a 10-year modular architecture where AI agents are treated as Digital FTEs (Full-Time Equivalents). The system is split into two distinct layers:

OpenClaw (The Brain & Business): Proactive reasoning, strategy generation, human-in-the-loop (HITL) coordination, and executive reporting (Gmail/Telegram). Enhanced with professional practices: Agents prioritize hypothesis-driven isolation of edges, focusing on repeatable advantages in isolated market components (e.g., regime-specific setups) to build a diversified portfolio of 5-10 narrow strategies. Now includes failure journaling for alpha decay analysis.

Nano Claw (The Muscle & Senses): High-frequency market sensing (Watchers), Zero-MQL execution, and local process persistence (PM2). Bolstered by data-driven iteration: Emphasizes statistical proof (e.g., e-ratio >1.5, Sharpe >1) and regime tagging for execution in specific conditions only. Extended to simulate diverse market elements (types, makers, orders, infrastructure) in backtests/execution.

2. Functional Requirements: The "Ralph Wiggum" Loop
The loop embeds professional methods for isolating setups/edges, starting with hypothesis generation from observations/anecdotes, rigorous empirical testing, simplification, regime tagging, risk-focused execution, and continuous refinement. This ensures setups are narrow, high-conviction, and stacked across regimes/timeframes/sessions for maximum executions (e.g., 5-10 daily opportunities). Examples of isolated setups (e.g., Pattern Failure Short) serve as templates stored in Neon DB for initial hypothesis seeding. Now parametrizes market simulations in validation/execution to test with varied params (e.g., order types like limit vs. market) and journals failures as structured entries.

A. Ingestion & Perception (Librarian Agent)
Input: Watcher monitors Obsidian_Vault/Needs_Action for research papers (PDFs), news, or data CSVs.

Logic: Extract core Alpha hypotheses using professional hypothesis generation: Start with market observations/anecdotes (e.g., from trader insights or clustering anomalies via K-means in ML). Hypothesize edges based on why they exist (e.g., institutional behavior in specific regimes). Compare against "Institutional Memory" in Neon DB to avoid redundant research, tagging by regime (trending vs. ranging via Hurst exponent), timeframe, session, or asset class.

Output: Structured RESEARCH_PLAN.md with defined parameters for testing, including initial regime filters, e-ratio targets, and potential market simulation params (e.g., test with market maker spreads).

B. Generation & Drafting (Strategist Agent)
Task: Autonomously write Python code for the proposed strategy, embedding model simplification: Reduce parameters to 2-3 high-impact variables (e.g., via feature selection like Boruta). Isolate to specific contexts (e.g., "only if VIX >20" for high-vol regimes).

Target: src/models/drafts/[Strategy_Name].py.

Standard: Must follow the BaseStrategy interface to ensure compatibility with the backtester. Incorporate regime tagging (e.g., Hurst exponent checks) and setup templates from examples (e.g., Momentum Breakout Long criteria). Now includes hooks for market param variations (e.g., order type simulations).

C. The Adversarial Moat (Killer Agent)
Validation: Embed rigorous backtesting: Run Monte Carlo Pro simulations (10k+ iterations) on 10+ years of data (e.g., OHLCV via Polygon API). Tag by conditions (e.g., session-specific) and use metrics like Sharpe (>1), max drawdown (<20%), hit rate (>55%), and e-ratio (>1.5). Walk-forward and out-of-sample testing to confirm isolation in regimes.

Stress Test: Inject Synthetic Noise (1-2 pip jitter) and Liquidity Shocks (2-3 pip slippage). Analyze sample size (e.g., 50+ trades) and regime-specific performance (e.g., volatility clustering). Enhanced for Task 2: Parametrize tests with market elements—e.g., simulate order-driven vs. quote-driven markets, market maker behaviors (bid-ask spreads, delta-neutral hedging), order types (market, limit, stop-loss, stop-limit), infrastructure (latency delays, clearing fees via DTCC/OCC models). Vary params like AMM liquidity pools for crypto-like edges or dark pool routing to uncover missed opportunities.

Approval Gate: Strategy must maintain >10% return and <12% Max Drawdown, with proven edge in isolated components (e.g., no overlap with other setups). Approved strategies move to src/models/production/, with "graveyard" post-mortems for failures. For Task 1: Failures trigger detailed journaling—categorize modes (e.g., overfitting: high in-sample Sharpe but out-of-sample drop; alpha decay: crowding via signal homogenization; regime shift: performance drop post-vol spike) as structured entries (e.g., Date, Strategy ID, Failure Mode, Metrics (pre/post decay Sharpe), Description, Limitations, Mitigation Suggestions).

D. Adaptive Optimization (RL/DL Hunter)
Models: Use PPO (Proximal Policy Optimization) for position sizing and Transformers for feature encoding, embedding execution/psychology focus: Adapt for entry timing and risk (e.g., strict stops based on LOD distance). Integrate market param adaptations (e.g., optimize for limit orders in low-liquidity infrastructures).

Gym Env: A custom US30 environment where rewards are Risk-Adjusted (Sharpe * Sortino), refined quarterly for market shifts.

E. Risk & Execution (Risk Architect & Manager)
Sizing: Implementation of Fractional Kelly Criterion and Volatility Targeting, with pro tips: Size based on risk tolerance (e.g., 1% per trade), adaptive via RL.

Execution: Throttled order injection via Alpaca API or MT5 Zero-MQL bridge, mechanical/discretionary based on setup isolation (e.g., trail stops with ATR for momentum breakouts). For Task 2: Embed configurable order types (market: immediate at best price; limit: at specified or better; stop: trigger market at stop price; stop-limit: trigger limit), market maker simulations (e.g., bid-ask profit, volume-based), market types (exchanges like NYSE vs. OTC; order-driven LOB vs. quote-driven), infrastructure (e.g., add latency/jitter for co-location effects, clearing via DTCC models). Test params in backtests to ensure edges hold across scenarios (e.g., iceberg orders for large blocks).

Guardrails: Automatic "Cooldown" triggers after 3 consecutive losses. Track order-level data (e.g., slippage) and psychology (e.g., journal tags for calm execution in ugly markets). Log failures to graveyard with journal entries.

3. Non-Functional Requirements: Stability & Moat
A. Persistence (The Nano Claw Supervisor)
Process Management: All watchers and connectors must run under PM2.

Auto-Restart: If a US30 data stream crashes, PM2 must restart the process immediately.

State Continuity: Agent "thoughts" and current task states must be logged to Neon DB every 60 seconds to survive system reboots, including regime tags, iteration history for continuous refinement, and failure journal entries.

B. Security & Integrity (HITL)
Human-in-the-Loop: High-leverage or live-account trades require a manual file move from /Plans to /Approved. Avoid edge dilution by not copying untested setups.

Zero-MQL: No logic is stored in the MT5 terminal. All execution is handled via Python to maintain a unified code repository.

C. Scalability & Modularity
Serverless Hybrid: Heavy training runs on local GPU; 24/7 sensing/monitoring runs on GCP Cloud Run (Free Tier). Automate quarterly retraining for adaptation, including market param sweeps.

Database: Use PostgreSQL (pgvector) on Neon for "Institutional Memory" of every successful and failed strategy, including tagged setups (e.g., by regime/session), example templates, and enhanced graveyard with journaled failure entries (e.g., fields: failure_mode, alpha_decay_reason, metrics_json).

4. The Business Layer (OpenClaw)
A. Monday Morning CEO Briefing
Logic: Every Monday at 08:00, the Reporter Agent audits Neon DB, embedding performance reviews: Analyze isolated edges (e.g., per setup in portfolio) with drawdown patterns and regime shifts. Include graveyard summaries with journaled failure insights (e.g., "Overfitting detected in 3 strategies: in-sample Sharpe 2.5 → out-of-sample 0.8").

Delivery: Emails a formatted report (via Gmail API) and posts a summary to a private Telegram Channel.

Metrics: P&L, Sharpe Ratio, Signal Decay stats, "Strategy Graveyard" post-mortems, and edge quantification (e.g., e-ratio per regime). Add alpha decay trends (e.g., crowding indicators).

B. Mobile Command Center (Telegram)
Commands: /status (Current P&L), /pause (Emergency Halt), /approve (Execute pending signal), /failure_report (Query graveyard journals).

Alerts: Immediate notification if the Risk Architect triggers a circuit breaker, or if regime shifts dilute an edge, or alpha decay detected.

5. Directory Structure & Standards
Plaintext
/
├── .env                        # API Keys (Neon, Alpaca, MT5, Google)
├── ecosystem.config.js         # PM2 Configuration
├── Obsidian_Vault/             # GUI & Interaction Hub
│   ├── /Needs_Action           # Perception Queue (e.g., for hypothesis seeding with examples)
│   ├── /Approved               # HITL Execution Queue
│   └── /Reports                # CEO Briefings (including regime-tagged metrics, failure journals)
├── src/
│   ├── agents/                 # OpenClaw (Librarian, Killer, Reporter) – enhanced with pro methods; implement agent teams here (e.g., perception_team.py coordinating Librarian + subagents)
│   ├── connectors/             # Nano Claw (Alpaca, MT5 Zero-MQL); add market infrastructure sims
│   ├── models/                 # RL/DL Model definitions, with setup templates and param hooks
│   └── tools/                  # Monte Carlo, DB Handlers (e.g., for regime clustering, failure journaling)
└── tests/                      # Unit tests for 10-year reliability, including backtesting examples with market params

Implementation Instructions for Coding Agent
Initialize Infrastructure: Build the BaseAgent and BaseConnector classes first to ensure modularity. Embed regime tagging in BaseStrategy. For Task 3: Implement agent skills as .md-defined Python functions in src/skills/[agent]/ (e.g., extract_hypothesis.py); MCP as Monte Carlo Pro in src/tools/monte_carlo.py; subagents as isolated classes (e.g., FailureAnalyzer subagent in Killer for journaling); agent teams in src/agents/teams/ (e.g., ValidationTeam coordinating Killer + Risk subagents in loop).

Setup Memory: Implement the Neon DB schema for alphas and strategy_graveyard, adding fields for regime/timeframe/session tags, e-ratio, example-based templates, failure journals (structured as JSON: {mode: "overfitting", reason: "High in-sample fit but regime shift failure", metrics: {...}, limitations: "Ignores market changes", mitigation: "Add regime filters"}).

Boot Senses: Implement the US30 Data Watcher under PM2 supervision, with anomaly scanning for hypothesis generation.

Activate Loop: Use the Ralph Wiggum Loop to iterate from raw research to a Monte-Carlo-validated production model, starting with pro methods (e.g., backtest one example setup via code_execution if needed) and refining quarterly. Integrate market param testing and failure journaling in Killer/Reporter.