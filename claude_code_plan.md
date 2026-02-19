# Autonomous Trading System – Digital FTE / Personal AI Employee

This plan outlines the development of an **autonomous trading system** functioning as a "Digital FTE" or "Personal AI Employee" for financial research and alpha generation.  

It integrates:
- Core trading system requirements from `specs.md`
- Robust architectural & operational principles from *"The CRM Digital FTE Factory Final Hackathon 5.md"* and `hackathon_0.md`  
  (Claude Code as reasoning, Obsidian for memory, Watchers, MCP, HITL, error handling, Kubernetes deployment)

**Primary goal**: Create a modular, secure, and resilient system capable of autonomously identifying, validating, and managing trading strategies — with **critical human oversight**.

## I. Foundational Setup  
(Leveraging `hackathon_0.md` and `specs.md`)

### 1. Initialize Obsidian Vault Structure

Create the following folders inside `AI_Employee_Vault`:

- `/Needs_Action` – new research, data, manual inputs
- `/Plans` – generated research plans and strategy drafts
- `/Done` – completed tasks / research
- `/Logs` – audit logs of all AI actions
- `/Pending_Approval` – actions requiring human review (e.g. trade execution)
- `/Approved` – approved actions
- `/Rejected` – rejected actions
- `/Accounting` – financial transactions and reports
- `/Research_Data` – raw market data, research papers
- `/Alphas` – validated strategy parameters
- `/Strategy_Graveyard` – failed hypotheses
- `/Market_Regimes` – metadata on historical market periods

**Initial markdown files** (refer `hackathon_0.md`):

- `Dashboard.md`
- `Company_Handbook.md` (trading rules / risk limits)
- `Business_Goals.md` (trading objectives)

### 2. Database Setup

- **Database**: PostgreSQL (Neon DB recommended)
- **Schema**:
  - Tables from `specs.md`: `alphas`, `strategy_graveyard`, `market_regimes`
  - Adapt logging/metrics tables from Hackathon 5 (e.g. `agent_metrics`, `conversations`, `messages`) for auditability of AI reasoning & decisions
- Implement `db_handler.py` (using **asyncpg**)

### 3. Watcher Implementation

Implement `BaseWatcher` + specific watchers:

- **Research Watcher**  
  Monitors `/Needs_Action` for: PDFs, URLs, news articles, manual inputs  
  → feeds Librarian agent

- **Data Ingestion Watcher**  
  Monitors folder or API for new market data (CSV/JSON)

Watchers create structured markdown files in `/Needs_Action` for Claude Code to process.

## II. Core Trading System Logic  
(Leveraging `specs.md` + FTE principles)

### 1. Agentic Workflow (Claude Code as Reasoning Engine)

- **Librarian Agent**  
  Input: markdown in `/Needs_Action`  
  → Extracts **Core Alpha Hypothesis**  
  → Compares against Market Theory Knowledge Base (Neon DB)  
  Output: `RESEARCH_PLAN.md` → `/Plans`

- **Strategist Agent**  
  Input: `RESEARCH_PLAN.md`  
  → Translates qualitative plan → quantitative Python code (entry/exit logic, ideal regime)  
  Output: Python test script → `src/models/drafts/`

- **Monte Carlo Engine Agent**  
  Input: draft Python script  
  → Runs 10,000+ Monte Carlo iterations + "Killer Agent" (synthetic slippage/noise)  
  Output: simulation results, statistical significance → updates `RESEARCH_PLAN.md` or new validation file

- **Regime Analyst Agent**  
  Input: Monte Carlo performance data  
  → Tests across timeframes (1m, 5m, 1h, 1D) + regimes (High Vol, Bear, Trending)  
  → Tests on correlated assets  
  Output: robustness analysis + "Characteristic Drift" findings

- **Risk Architect Agent**  
  Input: validated strategy + market analysis  
  → Runs RL agents (PPO/DQN) for optimal sizing (Kelly), SL/TP ratios  
  → Integrates behavioral patches (Disposition Effect, FOMO)  
  Output: finalized parameters, risk profile → proposal in `/Pending_Approval`

### 2. Model Context Protocol (MCP) Servers

Custom MCP servers:

- `data-mcp` – real-time / historical market data (external APIs)
- `trading-mcp` – brokerage API interaction (**strictly HITL**)
- `reporting-mcp` – specialized reports (e.g. "Monday Morning CEO Briefing")

Expose `@function_tool` decorated functions (OpenAI Agents SDK style).  
Use **Pydantic** `BaseModel` for strict input schemas + robust error handling.

### 3. Human-in-the-Loop (HITL)

File-based approval workflow:

- Critical actions (e.g. live trade proposals) → file created in `/Pending_Approval`
- Claude Code **waits** until human moves file to `/Approved`
- Define clear permission boundaries per action category

### 4. Persistence and Autonomy – Ralph Wiggum Loop

- Use Ralph Wiggum Loop pattern for continuous multi-step iteration
- Completion condition: e.g. file moved to `/Done`
- Managed by adapted `Orchestrator.py` + watchers

## III. Operational Excellence & Deployment

### 1. Security & Privacy Architecture

- **Credentials**: `.env` (local) + Kubernetes Secrets (prod) — `.gitignore` all `.env`
- **Sandboxing**: `DEV_MODE`, `--dry-run` flags, separate dev/test accounts
- **Rate limiting** on external APIs
- **Audit logging**: structured JSON logs → `/Vault/Logs/YYYY-MM-DD.json`
- Strict permission boundaries (auto vs manual approval)

### 2. Error States & Recovery

- Retry with exponential backoff (transient errors)
- Graceful degradation (fallback to cache / pause)
- **Watchdog.py**: monitors & restarts components + alerts on failure

### 3. Deployment

- **Docker** containerization
- **Kubernetes** manifests:
  - Namespace, ConfigMap, Secrets
  - Deployments (API + Workers)
  - Service, Ingress, HPA
  - FastAPI external API (dashboard, triggers)
  - Worker pods for agents (queue consumers)
  - PostgreSQL (+ pgvector)
  - Kafka (market events, task queues)
- Health checks + auto-scaling

## IV. Verification

- **Unit tests** — pytest (watchers, db_handler, MCP tools, agent logic)
- **Integration tests** — agent → agent flows (Librarian → Strategist → Monte Carlo)
- **End-to-End tests**:
  - New research input → `RESEARCH_PLAN.md` generated
  - Validated strategy → approval request in `/Pending_Approval`
  - HITL simulation (move to `/Approved` → dry-run log)
  - Audit log correctness
  - Load testing (simulated feeds + analysis)
  - Chaos testing (random pod kills → resilience & recovery)