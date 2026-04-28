# Project Architecture — Trader-Suit / OpenClaw Alpha Research System

> **As-built reference.** This document reflects the current state of the codebase.
> Historical planning documents (`IMPLEMENTATION_PLAN.md`, `TECHNICAL_SPECS_ANALYSIS_AND_PLAN.md`) describe earlier phases.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Layer-by-Layer Breakdown](#3-layer-by-layer-breakdown)
   - 3.1 [Vault — Input & Output Filesystem](#31-vault--input--output-filesystem)
   - 3.2 [Orchestration Layer](#32-orchestration-layer)
   - 3.3 [Agent Pipeline (Ralph Wiggum Loop)](#33-agent-pipeline-ralph-wiggum-loop)
   - 3.4 [Validation — Killer Agent & Monte Carlo Pro](#34-validation--killer-agent--monte-carlo-pro)
   - 3.5 [Risk Architecture](#35-risk-architecture)
   - 3.6 [HITL Gateway & Approval](#36-hitl-gateway--approval)
   - 3.7 [Execution Connectors](#37-execution-connectors)
   - 3.8 [Edges & Strategy Library](#38-edges--strategy-library)
   - 3.9 [ML / DL / RL Models](#39-ml--dl--rl-models)
   - 3.10 [Data Layer](#310-data-layer)
   - 3.11 [Memory & Bootstrap](#311-memory--bootstrap)
   - 3.12 [Skills System](#312-skills-system)
   - 3.13 [Database (Neon / asyncpg)](#313-database-neon--asyncpg)
   - 3.14 [FastAPI Backend](#314-fastapi-backend)
   - 3.15 [Streamlit Dashboard (Trader-Suit UI)](#315-streamlit-dashboard-trader-suit-ui)
   - 3.16 [Colab Research Pipeline](#316-colab-research-pipeline)
   - 3.17 [Tools & Utilities](#317-tools--utilities)
4. [End-to-End Workflow Walkthrough](#4-end-to-end-workflow-walkthrough)
5. [Directory Structure](#5-directory-structure)
6. [Environment & Configuration](#6-environment--configuration)
7. [Testing](#7-testing)
8. [Technology Stack](#8-technology-stack)
9. [Deployment](#9-deployment)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. System Overview

**Trader-Suit** is an AI-native algorithmic trading research and execution platform built around two complementary systems:

| System | Role |
|--------|------|
| **OpenClaw** | Brain — orchestrates agents, conducts research, validates hypotheses, manages risk |
| **Nano Claw** | Muscle — handles live execution via broker connectors (Alpaca, MT5) |

The system follows the **Ralph Wiggum Loop**: a sequential multi-agent pipeline that takes raw research ideas from a filesystem vault, transforms them into statistically validated trading strategies, and — after mandatory human approval — can execute them live.

All agent logic is in Python. There is **zero MQL** (no MetaTrader scripts); MT5 is accessed only through the Python connector.

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRADER-SUIT (OpenClaw)                           │
│                                                                         │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│   │  Streamlit   │    │   FastAPI    │    │  Colab SSH   │             │
│   │  Dashboard   │◄───│   Backend   │    │  (T4 GPU)    │             │
│   │  (port 8501) │    │  (port 8000) │    │  Research    │             │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘             │
│          │                   │                   │                     │
│          └───────────────────┼───────────────────┘                     │
│                              │                                         │
│   ┌──────────────────────────▼──────────────────────────────────────┐  │
│   │                    ORCHESTRATOR                                  │  │
│   │          src/orchestration/orchestrator.py                       │  │
│   │   Bootstrap → Skills → Agent Chain → HITL Gate → Reporter       │  │
│   └────┬─────────┬──────────┬──────────┬──────────────┬─────────────┘  │
│        │         │          │          │              │                 │
│   ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼──────┐ ┌───▼──────┐         │
│   │Library-│ │Strate- │ │Killer  │ │  Risk    │ │Reporter  │         │
│   │an Agent│ │gist    │ │Agent   │ │Architect │ │          │         │
│   └────┬───┘ └───┬────┘ └───┬────┘ └───┬──────┘ └───┬──────┘         │
│        │         │          │          │              │                 │
│   ┌────▼─────────▼──────────▼──────────▼──────────────▼─────────────┐  │
│   │                       VAULT FILESYSTEM                           │  │
│   │   Needs_Action/ → Plans/ → models/drafts/ → Approved/ → Logs/   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                              │                                         │
│   ┌──────────────────────────▼──────────────────────────────────────┐  │
│   │              EXECUTION LAYER (Nano Claw)                         │  │
│   │   HITL Gateway → Connectors (Alpaca / MT5) → Broker APIs        │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                              │                                         │
│   ┌──────────────────────────▼──────────────────────────────────────┐  │
│   │               PERSISTENCE LAYER                                  │  │
│   │          Neon (asyncpg) · Vault .md files · CSV data            │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Breakdown

### 3.1 Vault — Input & Output Filesystem

The vault (`AI_Employee_Vault/`) is the system's communication bus. Every agent reads from and writes to specific sub-folders. This file-based design allows human operators to drop in new research, inspect any intermediate artifact, and intervene at any stage.

```
AI_Employee_Vault/
├── Needs_Action/       ← operator drops raw research ideas / signals here
├── Plans/              ← Librarian writes structured RESEARCH_PLAN .md files here
├── models/drafts/      ← Strategist writes BaseStrategy Python code here
├── Approved/           ← operator places a file here to authorize live execution
├── Logs/               ← all agents log Risk_Audit, Risk_Config, run metadata
├── Accounting/         ← P&L records consumed by Reporter
├── Reports/            ← Monday briefings and graveyard summaries written here
└── Graveyard/          ← failed strategies archived with post-mortem .md
```

Watchers (`src/watchers/`) poll these folders and trigger the appropriate agent when new files appear.

---

### 3.2 Orchestration Layer

**`src/orchestration/orchestrator.py`**

The orchestrator is the central control loop. On startup it:

1. Loads **bootstrap context** (`AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`) via `src/memory/bootstrap_loader.py`.
2. Resolves and injects per-agent **skills** via `src/skills/loader.py`.
3. Chains agents in the **Ralph Wiggum Loop** order.
4. Passes the **HITL gate** before any execution is attempted.
5. Invokes the **Reporter** after each cycle.

The orchestrator can be run standalone:

```bash
python -m src.orchestration.orchestrator
```

---

### 3.3 Agent Pipeline (Ralph Wiggum Loop)

Each agent is a subclass of `BaseAgent` (`src/agents/base_agent.py`), which defines the abstract contract:

```
perceive()  →  reason()  →  act()  →  log_action()
```

| Step | Agent | Module | Input | Output |
|------|-------|--------|-------|--------|
| 1 | **Librarian** | `src/agents/librarian_agent.py` | `Needs_Action/` files | `Plans/RESEARCH_PLAN_*.md` |
| 2 | **Strategist** | `src/agents/strategist_agent.py` | `Plans/` | `models/drafts/strategy_*.py` |
| 3 | **Killer** | `src/agents/killer_agent.py` | Draft strategy file | Monte Carlo audit → pass/fail |
| 4 | **Risk Architect** | `src/agents/risk_architect.py` | Validated strategy | Sized position params |
| 5 | **Execution Manager** | `src/connectors/execution_manager.py` | `Approved/` file | Live / paper orders |
| 6 | **Reporter** | `src/agents/reporter.py` | `Logs/` + `Accounting/` | `Reports/` briefings |

**Librarian Agent**
- Senior quant persona, powered by Anthropic Claude or Gemini (via `src/tools/llm_client.py`).
- Extracts alpha hypotheses from research documents.
- Tags hypotheses by market regime (trend, range, volatile).
- Checks institutional memory (DB / vault) to avoid redundant strategies.
- Produces a structured `RESEARCH_PLAN.md` with sections: hypothesis, edge type, instruments, regime context, risk parameters.

**Strategist Agent**
- Receives the research plan; loads `US30Loader` for data context and `EDGE_REGISTRY_SUMMARY` for available edges.
- Emits only valid `BaseStrategy` subclass code — no execution logic.
- Embeds regime filter hooks and market parameter references.

**Killer Agent**
- Loads the draft strategy and the US30 price series.
- Runs `MonteCarloPro` with bootstrap path simulation, VaR, friction, and stress regime scenarios.
- Pass → strategy file moves toward `models/production/`; Fail → strategy goes to `Graveyard/` with a post-mortem journal entry (`src/tools/failure_journal.py`).
- Logs Risk Audit to `Logs/` and optionally to Neon DB.

**Risk Architect**
- Applies fractional Kelly sizing.
- Adds volatility targeting guardrails.
- Inserts circuit breakers (cooldown after N consecutive losses).
- Outputs a risk parameter block attached to the strategy.

**Reporter**
- Scans `Logs/` and `Accounting/`.
- Pulls graveyard context from Neon when `DATABASE_URL` is set.
- Writes Monday briefings to `Reports/`.
- Optionally pushes to Telegram or Gmail (via `src/tools/notifier.py`).

---

### 3.4 Validation — Killer Agent & Monte Carlo Pro

**`src/tools/monte_carlo_pro.py`** is the core statistical moat of the system.

```
MonteCarloPro
├── simulate_paths()          — bootstrap-resampled equity curves
├── compute_var()             — parametric + historical VaR at configurable alpha
├── apply_friction()          — commission, slippage, spread simulation
├── stress_regime_scenarios() — crisis, trending, ranging overlays
└── generate_audit_report()   — structured Risk_Audit_*.md output
```

Typical pass criteria (configurable via env/config):
- Median Sharpe ≥ threshold across bootstrap iterations
- Maximum drawdown below limit
- Positive expectancy under worst-case friction scenario

---

### 3.5 Risk Architecture

**`src/agents/risk_architect.py`** and **`src/agents/risk_architect_sizing.py`**

- **Kelly Criterion** (fractional, typically 0.25× full Kelly) for position sizing.
- **Volatility targeting**: position size scales inversely with realized volatility.
- **Circuit breaker**: disables execution after N consecutive losses; requires manual reset.
- **Max drawdown guardrail**: system-wide soft ceiling; hard stop when breached.

---

### 3.6 HITL Gateway & Approval

**`src/gateway/approval.py`**

The Human-In-The-Loop (HITL) gate is a hard requirement before any live execution:

```python
can_approve_strategy(strategy_path) → bool   # checks Approved/ folder
can_execute_order(order)            → bool   # validates approval file exists
```

The operator approves a strategy by placing a file in `AI_Employee_Vault/Approved/`. The system will **not** execute without this file, regardless of Monte Carlo outcome.

High-leverage or size-threshold orders also require manual approval (configurable threshold in `.env`).

---

### 3.7 Execution Connectors

**`src/connectors/`**

| Module | Purpose |
|--------|---------|
| `alpaca_connector.py` | Alpaca Markets REST + WebSocket (paper and live) |
| `mt5_connector.py` | MetaTrader 5 Python API (Windows-only) |
| `execution_manager.py` | Throttled order routing; chooses connector based on `BROKER_TYPE` |
| `market_stream.py` | Real-time quote / bar streaming |
| `connector_cache.py` | Price cache layer to reduce API calls |
| `connector_factory.py` | Creates the correct connector from `BROKER_TYPE` env var |
| `broker_adapter.py` | Unified adapter interface across broker types |

The `execution_manager` enforces rate limits and routes to the approved broker. Zero MQL — all MetaTrader communication goes through the Python MT5 connector.

---

### 3.8 Edges & Strategy Library

**`src/edges/`** contains pre-built alpha edges organized by type:

```
edges/
├── edge_registry.py           ← EdgeInfo dataclass catalogue (edge_type → modules)
├── volume_based/
│   ├── volume_rl_agent.py     ← RL agent trained on volume features
│   └── volume_workflow.py
├── pattern_based/
│   ├── pattern_detector_dl.py ← DL pattern classifier
│   ├── pattern_detector_ml.py ← ML baseline
│   └── pattern_rl_agent.py
├── statistical/               ← cointegration, mean-reversion edges
└── session_based/             ← US session time-of-day overlays
```

The **Strategist Agent** queries `EDGE_REGISTRY_SUMMARY` to select and compose edges when drafting a new strategy. New edges can be registered by adding an `EdgeInfo` entry in `edge_registry.py`.

**`src/models/base_strategy.py`** defines the contract every strategy must satisfy:

```python
class BaseStrategy:
    def entry(self, data) -> Signal: ...
    def exit(self, data, position) -> Signal: ...
    def risk(self, data) -> RiskParams: ...
```

Draft strategies live in `src/models/drafts/`; validated production strategies in `src/models/production/`.

---

### 3.9 ML / DL / RL Models

| Model | Module | Algorithm |
|-------|--------|-----------|
| Regime Classifier | `src/ml/regime_classifier.py` | scikit-learn (Random Forest / XGBoost) |
| Pattern Detector ML | `src/edges/pattern_based/pattern_detector_ml.py` | sklearn pipeline |
| Pattern Detector DL | `src/edges/pattern_based/pattern_detector_dl.py` | PyTorch / TensorFlow CNN |
| Volume RL Agent | `src/edges/volume_based/volume_rl_agent.py` | stable-baselines3 PPO/SAC |
| Pattern RL Agent | `src/edges/pattern_based/pattern_rl_agent.py` | stable-baselines3 |

Heavy training runs are performed on **Google Colab T4 GPU** via Remote-SSH (see §3.16). Local dev machine is used for code editing only.

---

### 3.10 Data Layer

**`src/data/`**

| Module | Role |
|--------|------|
| `us30_loader.py` | Primary OHLCV loader for US30 (Dow Jones); reads CSV or live connector; MinMax normalization for RL feature vectors |
| `preprocessor.py` | General feature engineering (returns, rolling stats, etc.) |
| `pattern_preprocessor.py` | Candlestick encoding and windowing for DL/RL |
| `volume_loader.py` | Volume profile aggregation |

Data sources:
- **CSV files** (path set via `US30_CSV_PATH` env var) — primary for backtesting and Colab research.
- **Live connector** (Alpaca or MT5) — injected when `BROKER_TYPE` is set.
- **yfinance** — used in Colab notebooks for broader market data.

---

### 3.11 Memory & Bootstrap

**`src/memory/`**

| Module | Role |
|--------|------|
| `bootstrap_loader.py` | Concatenates `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `Paradigms.md` into a single context string injected into every LLM agent call |
| `session_store.py` | In-process session key/value store (per-run state) |
| `state_sync.py` | Optional sync of session state to Neon DB |

The bootstrap ensures every agent shares the same **persona**, **operating principles**, and **operator-defined constraints** without relying on agent-to-agent message passing.

---

### 3.12 Skills System

**`src/skills/`** implements a three-tier skill resolution:

```
1. ./skills/<agent>/SKILL.md          (workspace-local, highest priority)
2. ~/.alpha-factory/skills/           (user-global)
3. src/skills/<agent>/SKILL.md        (package default)
```

Skills are markdown files injected into an agent's context to specialize its behavior (e.g. the Killer agent's skill defines the exact Monte Carlo pass/fail criteria to apply). New skills can be dropped in at any tier without modifying Python code.

---

### 3.13 Database (Neon / asyncpg)

**`src/db/db_handler.py`** — async PostgreSQL via **asyncpg** connected to **Neon** (serverless Postgres).

Core tables (see `database/schema.sql`):

| Table | Contents |
|-------|----------|
| `alphas` | Validated alpha hypotheses with metadata |
| `graveyard` | Failed strategies with post-mortem text |
| `regimes` | Detected market regime labels + timestamps |
| `audit_log` | Risk audit entries from Killer Agent |

Actor-critic extensions (`database/schema_actor_critic.sql`) add tables for RL episode logging (see `docs/ACTOR_CRITIC_SPECS.md`).

The database is **optional** — the system degrades gracefully to vault-only filesystem mode when `DATABASE_URL` is not set.

---

### 3.14 FastAPI Backend

**`src/api/main.py`** — served via **uvicorn** on port `8000`.

```bash
python main.py          # starts uvicorn on :8000
```

Endpoints provide:
- Market data (bars, quotes) — backed by Alpaca when keys are present; mock data otherwise.
- Strategy list and status.
- Agent run triggers (can kick off orchestrator from the dashboard).
- Approval / HITL status checks.

CORS is configured to allow the Streamlit dashboard (`localhost:8501`) to call the API.

---

### 3.15 Streamlit Dashboard (Trader-Suit UI)

**`src/dashboard/app.py`** — served on port `8501`.

```bash
streamlit run src/dashboard/app.py
```

Dashboard pages (`src/dashboard/pages/`):

| Page | Purpose |
|------|---------|
| **Home** | System status, active strategies, quick metrics |
| **Alpha Idea Lab** | Drop research notes; trigger Librarian; view RESEARCH_PLANs |
| **Vault Explorer** | Browse all vault folders and file contents |
| **No-Code Builder** | `builder_agent.py` — conversational strategy builder |
| **Strategy Library** | View and compare all drafts and production strategies |
| **Backtester / Killer** | Run Monte Carlo pro on demand; view Risk Audit reports |
| **Optimization Lab** | Parameter sweep and walk-forward optimization tools |
| **Execution & Reports** | Live/paper order management; Monday briefings |
| **Technical Analysis** | Charts, indicators, regime overlays |

**`src/dashboard/cockpit.py`** provides the real-time trading cockpit view (P&L, open positions, live equity curve).

---

### 3.16 Colab Research Pipeline

The Colab environment is accessed via **Remote-SSH** directly inside Cursor. When the status bar shows `SSH: [Colab host]`, the integrated terminal executes on the Colab instance.

```
Local Cursor IDE  ──SSH tunnel──►  Google Colab T4 GPU
  (code editing)                   (training, backtesting,
                                    Monte Carlo at scale)
                                   /content/drive/MyDrive/
                                   Alpha_FTE_Project/
                                   (Google Drive = persistence)
```

**Colab notebooks** (`colab/`):

| Notebook | Purpose |
|----------|---------|
| `setup_colab.ipynb` | One-time GPU setup: clone repo, pip install, `sys.path` |
| `run_rl_dl_ml_colab.ipynb` | Full RL/DL/ML training loop + Monte Carlo validation |
| `us30_model_research.ipynb` | US30 pipeline: yfinance → feature engineering → walk-forward CV → ML/DL/RL |
| `us30_dxy_equity_vs_fx.ipynb` | Research: US30 / DXY / equity vs FX forward alpha |

**`colab/requirements-colab.txt`** is a lean subset (no Streamlit / FastAPI / asyncpg) optimized for GPU compute:

```
numpy, pandas, scikit-learn, torch, yfinance, pandas-ta,
tensorflow, stable-baselines3, gym
```

---

### 3.17 Tools & Utilities

**`src/tools/`**

| Module | Role |
|--------|------|
| `monte_carlo_pro.py` | Core statistical validation engine |
| `llm_client.py` | Unified LLM wrapper (Anthropic Claude + Google Gemini) |
| `vault_watcher.py` | Filesystem polling for vault `Needs_Action/` folder |
| `failure_journal.py` | Writes graveyard post-mortem entries |
| `journal.py` | General trade/research journal logging |
| `notifier.py` | Telegram / Gmail push notifications |
| `discovery_lab.py` | Alpha screening utilities |
| `cointegration.py` | Engle-Granger / Johansen cointegration tests |
| `db_handlers.py` | Higher-level DB helpers over `db_handler.py` |

**`src/mcp/alpaca_server.py`** — MCP (Model Context Protocol) server exposing Alpaca data to LLM agent tool calls.

**`src/prompt/instruction_router.py`** — routes operator instructions to the correct agent based on intent classification.

**`src/backtest/us_session_backtest.py`** — US equity session backtest engine.

---

## 4. End-to-End Workflow Walkthrough

Below is the full lifecycle of a strategy from idea to execution.

```
STEP 1  ─── Operator drops a research note into AI_Employee_Vault/Needs_Action/
                e.g. "US30 opens strong on low DXY + declining yields → momentum edge"

STEP 2  ─── vault_watcher.py detects the new file
            → triggers orchestrator.py

STEP 3  ─── BOOTSTRAP
            bootstrap_loader.py injects AGENTS.md + SOUL.md + IDENTITY.md + USER.md
            skills/loader.py injects per-agent SKILL.md files

STEP 4  ─── LIBRARIAN AGENT  (src/agents/librarian_agent.py)
            · Reads Needs_Action/ file
            · Queries DB for similar past alphas (deduplication)
            · Calls LLM (Claude / Gemini) with structured quant persona
            · Tags hypothesis by regime (trending / ranging / volatile)
            · Writes Plans/RESEARCH_PLAN_<timestamp>.md

STEP 5  ─── STRATEGIST AGENT  (src/agents/strategist_agent.py)
            · Reads Plans/ file
            · Loads US30Loader for data context
            · Queries EDGE_REGISTRY for relevant edges (volume, pattern, session)
            · Calls LLM to generate BaseStrategy subclass code
            · Writes src/models/drafts/strategy_<name>.py

STEP 6  ─── KILLER AGENT  (src/agents/killer_agent.py)
            · Loads draft strategy + US30 price history
            · Runs MonteCarloPro:
                - N bootstrap iterations of equity curve simulation
                - VaR at configured alpha
                - Friction adjustment (spread + commission + slippage)
                - Stress regime overlay (crisis, trending, ranging)
            · PASS → strategy moves toward models/production/
              FAIL → strategy archived to Graveyard/ + failure_journal.py
            · Writes Logs/Risk_Audit_<timestamp>.md
            · Optionally logs to Neon DB (audit_log table)

STEP 7  ─── RISK ARCHITECT  (src/agents/risk_architect.py)
            · Applies fractional Kelly sizing (default 0.25×)
            · Attaches volatility targeting multiplier
            · Adds circuit breaker parameters
            · Writes final risk-parameterized strategy file

STEP 8  ─── HITL GATE  (src/gateway/approval.py)
            · System HALTS here
            · Operator reviews Risk_Audit .md and strategy code
            · Operator places approval file in AI_Employee_Vault/Approved/
            · can_approve_strategy() → True

STEP 9  ─── EXECUTION MANAGER  (src/connectors/execution_manager.py)
            · connector_factory creates Alpaca or MT5 connector
            · Throttled order routing
            · Orders logged to Accounting/

STEP 10 ─── REPORTER  (src/agents/reporter.py)
            · Scans Logs/ and Accounting/
            · Pulls graveyard context from Neon
            · Writes Reports/Monday_Briefing_<date>.md
            · Sends Telegram / Gmail notification (if configured)
```

---

## 5. Directory Structure

```
claude/                               ← repo root
├── main.py                           ← FastAPI entry (uvicorn :8000)
├── pyproject.toml                    ← project metadata + deps
├── requirements.txt                  ← pip deps
├── .env.example                      ← env var template (commit this, NOT .env)
│
├── src/
│   ├── agents/                       ← Ralph Wiggum agent implementations
│   │   ├── base_agent.py
│   │   ├── librarian_agent.py
│   │   ├── strategist_agent.py
│   │   ├── killer_agent.py
│   │   ├── risk_architect.py
│   │   ├── risk_architect_sizing.py
│   │   ├── reporter.py
│   │   └── teams/
│   ├── orchestration/
│   │   └── orchestrator.py
│   ├── gateway/
│   │   └── approval.py               ← HITL enforcement
│   ├── memory/
│   │   ├── bootstrap_loader.py
│   │   ├── session_store.py
│   │   └── state_sync.py
│   ├── skills/
│   │   ├── loader.py                 ← 3-tier skill resolution
│   │   └── <agent>/SKILL.md
│   ├── tools/
│   │   ├── monte_carlo_pro.py        ← statistical validation core
│   │   ├── llm_client.py
│   │   ├── vault_watcher.py
│   │   ├── failure_journal.py
│   │   ├── notifier.py
│   │   └── ...
│   ├── db/
│   │   └── db_handler.py             ← asyncpg / Neon
│   ├── data/
│   │   ├── us30_loader.py
│   │   ├── preprocessor.py
│   │   └── ...
│   ├── models/
│   │   ├── base_strategy.py
│   │   ├── drafts/                   ← unvalidated strategies
│   │   └── production/               ← validated + approved strategies
│   ├── edges/
│   │   ├── edge_registry.py
│   │   ├── volume_based/
│   │   ├── pattern_based/
│   │   ├── statistical/
│   │   └── session_based/
│   ├── ml/
│   │   └── regime_classifier.py
│   ├── connectors/
│   │   ├── alpaca_connector.py
│   │   ├── mt5_connector.py
│   │   ├── execution_manager.py
│   │   ├── market_stream.py
│   │   ├── connector_cache.py
│   │   └── connector_factory.py
│   ├── api/
│   │   ├── main.py                   ← FastAPI app
│   │   └── alpaca_service.py
│   ├── dashboard/
│   │   ├── app.py                    ← Streamlit entry
│   │   ├── cockpit.py
│   │   ├── builder_agent.py
│   │   └── pages/
│   ├── watchers/
│   │   ├── base_watcher.py
│   │   ├── research_watcher.py
│   │   └── data_ingestion_watcher.py
│   ├── backtest/
│   │   └── us_session_backtest.py
│   ├── mcp/
│   │   └── alpaca_server.py
│   └── prompt/
│       └── instruction_router.py
│
├── AI_Employee_Vault/                ← agent I/O filesystem bus
│   ├── Needs_Action/
│   ├── Plans/
│   ├── Approved/
│   ├── Logs/
│   ├── Accounting/
│   ├── Reports/
│   └── Graveyard/
│
├── database/
│   ├── schema.sql
│   └── schema_actor_critic.sql
│
├── docs/
│   ├── UI_Design_Best_Practices.md
│   ├── ACTOR_CRITIC_SPECS.md
│   └── DEPLOYMENT.md
│
├── colab/
│   ├── README.md
│   ├── CONNECT_COLAB_SSH.md
│   ├── requirements-colab.txt
│   ├── setup_colab.ipynb
│   ├── run_rl_dl_ml_colab.ipynb
│   ├── us30_model_research.ipynb
│   └── us30_dxy_equity_vs_fx.ipynb
│
├── tests/
│   ├── test_monte_carlo_pro.py
│   ├── test_connectors.py
│   ├── test_advanced_connector.py
│   └── test_us_session_backtest.py
│
└── skills/                           ← workspace-level skill overrides
```

---

## 6. Environment & Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in values. **Never commit `.env`.**

| Variable | Description |
|----------|-------------|
| `VAULT_PATH` | Absolute path to `AI_Employee_Vault/` |
| `US30_CSV_PATH` | Path to US30 OHLCV CSV for backtesting |
| `BROKER_TYPE` | `alpaca` or `mt5` |
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_SECRET_KEY` | Alpaca secret key |
| `ALPACA_ENDPOINT` | `https://paper-api.alpaca.markets` or live URL |
| `GEMINI_API_KEY` | Google Gemini API key (LLM fallback) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (primary LLM) |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `RESEARCH_INPUT_PATH` | Optional override for research input folder |
| `DATA_SOURCE_PATH` | Optional override for data CSV folder |

---

## 7. Testing

```bash
pytest tests/
```

| Test file | Covers |
|-----------|--------|
| `test_monte_carlo_pro.py` | Bootstrap simulation, VaR, audit report generation |
| `test_connectors.py` | Alpaca + MT5 connector interface conformance |
| `test_advanced_connector.py` | Edge cases: rate limits, reconnect, partial fills |
| `test_us_session_backtest.py` | Session backtest engine correctness |

`test_mcp_server.py` (root) validates the MCP Alpaca server tool contracts.

---

## 8. Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python ≥ 3.10 |
| LLM | Anthropic Claude (primary) · Google Gemini (fallback) |
| ML/RL | scikit-learn · PyTorch · TensorFlow · stable-baselines3 |
| Data | pandas · numpy · yfinance · pandas-ta | 
| Database | PostgreSQL via Neon (serverless) · asyncpg |
| API backend | FastAPI · uvicorn | 
| Dashboard | Streamlit · Plotly | 
| Brokers | Alpaca (`alpaca-py`) · MetaTrader 5 (`MetaTrader5`) | 
| Compute | Google Colab T4 GPU (Remote-SSH) | 
| Notifications | Telegram Bot API · Gmail SMTP | 
| Process management | PM2 (planned, see `docs/DEPLOYMENT.md`) | 
| Protocol | MCP (Model Context Protocol) for LLM tool calls | 

---

## 9. Deployment

**Development (local editing + Colab compute):**

```bash
# API backend
python main.py                           # uvicorn on :8000

# Streamlit dashboard
streamlit run src/dashboard/app.py       # on :8501

# Agent loop (manual trigger)
python -m src.orchestration.orchestrator
```

**Colab (training / backtesting):**

1. Connect via Remote-SSH (see `colab/CONNECT_COLAB_SSH.md`).
2. Mount Drive: `from google.colab import drive; drive.mount('/content/drive')`.
3. Install deps: `pip install -r colab/requirements-colab.txt`.
4. Run notebooks or: `python -m src.edges.volume_based.volume_workflow`.
5. Monitor GPU: `nvidia-smi`.

All checkpoints and trained models must be saved under `/content/drive/MyDrive/Alpha_FTE_Project/` for persistence across Colab disconnects.

**Production (planned):**
- PM2 for process supervision (see `docs/DEPLOYMENT.md`).
- `DATABASE_URL` pointing to Neon production instance.
- `ALPACA_ENDPOINT` switched to live URL after operator approval.

---

## 10. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **File-based vault as message bus** | Enables full human transparency; operator can inspect and intervene at every step with a text editor; no broker-in-the-middle needed |
| **Mandatory HITL before execution** | Prevents automated systems from going live without human review; approval is a physical file drop, not a flag |
| **Zero MQL** | All broker logic in Python; MT5 accessed via Python connector; keeps codebase unified and testable |
| **Monte Carlo moat** | Bootstrap resampling + friction + stress regimes provides a much higher bar than simple backtesting; guards against curve-fitting |
| **Fractional Kelly sizing** | Full Kelly has high ruin probability; 0.25× Kelly balances growth and drawdown |
| **LLM persona via bootstrap** | Injecting SOUL.md / IDENTITY.md / USER.md on every call ensures consistent agent behavior without storing state between calls |
| **3-tier skill resolution** | Allows workspace overrides without forking the package; operators can customize agent behavior by dropping a SKILL.md file |
| **Colab via Remote-SSH** | Keeps the dev workflow inside Cursor; no context switching to browser; Drive-mounted paths provide persistence |
| **Graceful DB degradation** | System operates in vault-only mode when DATABASE_URL is absent; useful for local dev without a Neon connection |
| **asyncpg over SQLAlchemy** | Lower overhead for async FastAPI; sufficient for the current schema; actor-critic logging needs high write throughput |

---

## 11. Implementation Status — Backend & Agents

### Legend
- **Done** — code exists and is wired end-to-end
- **Partial** — code exists but is not fully connected / has placeholder logic
- **Planned** — defined in spec/plan but not yet coded

---

### 11.1 Core Agent Pipeline

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| BaseAgent (perceive / reason / act) | `src/agents/base_agent.py` | **Done** | Abstract contract implemented |
| Orchestrator (one-cycle loop) | `src/orchestration/orchestrator.py` | **Done** | Chains all agents; optional bootstrap + skills |
| Librarian Agent | `src/agents/librarian_agent.py` | **Done** | Needs_Action → RESEARCH_PLAN; LLM via Anthropic/Gemini |
| Strategist Agent | `src/agents/strategist_agent.py` | **Done** | Plans → BaseStrategy draft; edge registry context |
| Killer Agent | `src/agents/killer_agent.py` | **Done** | Monte Carlo Pro + graveyard; optional DB logging |
| Risk Architect | `src/agents/risk_architect.py` | **Done** | Fractional Kelly, vol targeting, circuit breakers |
| Risk Architect (sizing module) | `src/agents/risk_architect_sizing.py` | **Done** | Position sizing helpers |
| Reporter | `src/agents/reporter.py` | **Done** | Briefings from Logs + Accounting; Neon-aware graveyard |
| Perception Team | `src/agents/teams/perception_team.py` | **Done** | Watcher-level coordination |
| Validation Team | `src/agents/teams/validation_team.py` | **Done** | Killer-level coordination |

---

### 11.2 Memory, Bootstrap & Skills

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| Bootstrap loader | `src/memory/bootstrap_loader.py` | **Done** | Concatenates AGENTS.md, SOUL.md, IDENTITY.md, USER.md, Paradigms.md |
| Session store | `src/memory/session_store.py` | **Done** | In-process key/value per run |
| State sync to Neon | `src/memory/state_sync.py` | **Done** | 60s flush interval |
| Skills loader (3-tier) | `src/skills/loader.py` | **Done** | workspace > ~/.alpha-factory > src/skills |
| Per-agent SKILL.md files | `src/skills/<agent>/SKILL.md` | **Done** | Librarian, Strategist, Killer, Risk Architect, Watchers |
| Subagent skill implementations (e.g. `extract_hypothesis.py`) | `src/skills/<agent>/` | **Planned** | Paradigms Task 3; pin concrete skill modules |

---

### 11.3 Validation & Monte Carlo

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| Monte Carlo Pro engine | `src/tools/monte_carlo_pro.py` | **Done** | Bootstrap paths, VaR, friction, stress regimes, audit report |
| Failure journal | `src/tools/failure_journal.py` | **Done** | Graveyard post-mortem entries |
| Full failure schema in Neon | `database/schema.sql` | **Partial** | Basic schema present; `failure_mode`, `alpha_decay_reason`, `metrics_json` columns need migration (Paradigms Task 1) |
| FailureAnalyzer subagent | — | **Planned** | Dedicated subagent to classify and route failure modes |
| Market parameter simulations | — | **Planned** | `market_infrastructure_sims.py`; order types, market-maker sims (Paradigms Task 2) | 
| Walk-forward / out-of-sample toggle | `src/tools/monte_carlo_pro.py` | **Partial** | Framework exists; not exposed as UI/API parameter yet | 

---

### 11.4 HITL Gateway & Execution

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| HITL approval gate | `src/gateway/approval.py` | **Done** | File-based; `can_approve_strategy`, `can_execute_order` |
| Alpaca connector | `src/connectors/alpaca_connector.py` | **Done** | Paper + live; REST + WebSocket |
| MT5 connector (Zero-MQL) | `src/connectors/mt5_connector.py` | **Done** | Python MT5 API; no MQL scripts |
| Execution manager (throttled routing) | `src/connectors/execution_manager.py` | **Done** | Rate-limited; broker chosen via `BROKER_TYPE` |
| Market stream (real-time quotes) | `src/connectors/market_stream.py` | **Done** | WebSocket quote streaming |
| Connector cache | `src/connectors/connector_cache.py` | **Done** | Reduces redundant API calls |
| Connector factory | `src/connectors/connector_factory.py` | **Done** | Instantiates correct connector from env |
| Broker adapter (unified interface) | `src/execution/broker_adapter.py` | **Done** | Normalizes across Alpaca / MT5 |
| PM2 process supervision | `ecosystem.config.js` | **Planned** | Referenced in README; file not present; needed for production daemon mode |

---

### 11.5 

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| BaseStrategy contract | `src/models/base_strategy.py` | **Done** | entry / exit / risk interface |
| Edge registry | `src/edges/edge_registry.py` | **Done** | EdgeInfo catalogue with all edge types |
| Volume RL agent | `src/edges/volume_based/volume_rl_agent.py` | **Done** | stable-baselines3 PPO/SAC on volume features |
| Pattern RL agent | `src/edges/pattern_based/pattern_rl_agent.py` | **Done** | RL on candlestick patterns |
| Pattern detector (DL) | `src/edges/pattern_based/pattern_detector_dl.py` | **Done** | PyTorch/TensorFlow CNN |
| Pattern detector (ML) | `src/edges/pattern_based/pattern_detector_ml.py` | **Done** | sklearn pipeline baseline |
| Statistical / cointegration edges | `src/edges/statistical/`, `src/tools/cointegration.py` | **Done** | Engle-Granger / Johansen |
| Session-based edges | `src/edges/session_based/` | **Done** | US session time-of-day overlays |
| Regime classifier | `src/ml/regime_classifier.py` | **Done** | Trending / Ranging / Volatile labels |
| Draft strategies | `src/models/drafts/` | **Partial** | `strategy_manual_sma.py` present; more generated per cycle |
| Production strategies | `src/models/production/` | **Partial** | Populated by Killer on pass; currently empty until first validated cycle |

---

### 11.6 Data & Database

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| US30 loader (CSV + connector) | `src/data/us30_loader.py` | **Done** | CSV fallback + live connector path; MinMax for RL |
| General preprocessor | `src/data/preprocessor.py` | **Done** | Returns, rolling stats, feature engineering |
| Pattern preprocessor | `src/data/pattern_preprocessor.py` | **Done** | Candlestick windowing for DL/RL |
| Volume loader | `src/data/volume_loader.py` | **Done** | Volume profile aggregation |
| DB handler (asyncpg) | `src/db/db_handler.py` | **Done** | alphas, graveyard, regimes, audit_log tables |
| Higher-level DB helpers | `src/tools/db_handlers.py` | **Done** | Wraps db_handler for agent use |
| Neon connection (live wiring in API) | `src/api/main.py` | **Planned** | API currently returns mock data; Neon not wired to endpoints |
| Actor-critic schema | `database/schema_actor_critic.sql` | **Partial** | SQL written; not yet applied to production Neon |

---

### 11.7 Watchers & Vault

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| Base watcher | `src/watchers/base_watcher.py` | **Done** | Needs_Action polling abstraction |
| Research watcher | `src/watchers/research_watcher.py` | **Done** | Triggers Librarian on new file |
| Data ingestion watcher | `src/watchers/data_ingestion_watcher.py` | **Done** | Monitors data source path |
| Vault watcher (`monitor_vault`) | `src/tools/vault_watcher.py` | **Done** | Filesystem event loop |
| PM2 watcher daemon | `ecosystem.config.js` | **Planned** | Needs PM2 config to run watchers as persistent processes |

---

### 11.8 FastAPI Backend

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` — health check | **Done** | Returns system status |
| `GET /status` — agent health | **Done** | Mock data; not wired to real agent state |
| `GET /signals` — active signals | **Done** | Mock data; not wired to vault / Approved/ |
| `GET /risk` — risk metrics | **Done** | Mock data; not wired to Risk Architect output |
| `GET /alpaca/status` — broker connection | **Done** | Checks Alpaca credentials |
| `GET /alpaca/account` — account info | **Done** | Live when credentials are set |
| `GET /alpaca/positions` — open positions | **Done** | Live when credentials are set |
| `GET /alpaca/bars` — price history | **Done** | Proxies Alpaca bars API |
| Performance metrics endpoint | **Planned** | P&L, Sharpe, Sortino, DD from Neon or computed |
| Activity log endpoint | **Planned** | `GET /activity` — events from agents/watchers |
| Vault file list / read / upload | **Planned** | Needed for Vault Explorer page |
| Strategy list (drafts/production/graveyard) | **Planned** | Scan models dirs + failure journal |
| Monte Carlo Pro job endpoint | **Planned** | Async run; return metrics + pass/fail |
| Instruction router endpoint | **Planned** | `POST /instruct` → `instruction_router` → Librarian |
| Alpha decay / redundancy check | **Planned** | From Librarian/Neon; expose to Alpha Idea Lab |
| MT5 live price / candlestick | **Planned** | From `market_stream`; expose as SSE or polling endpoint |

---

### 11.9 Notifications & Reporting

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| Reporter agent (briefings) | `src/agents/reporter.py` | **Done** | Writes Reports/; Neon-aware graveyard context |
| Notifier (Telegram/Gmail) | `src/tools/notifier.py` | **Partial** | Code exists; integration with Reporter not fully wired |
| Telegram `/failure_report` command | — | **Planned** | Paradigms Task 1; query failure journals from Telegram bot |
| PDF export | — | **Planned** | Spec calls for downloadable report PDF from Execution & Reports page |

---

### 11.10 MCP & Advanced Tools

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| MCP Alpaca server | `src/mcp/alpaca_server.py` | **Done** | Exposes Alpaca data to LLM tool calls |
| Instruction router | `src/prompt/instruction_router.py` | **Done** | Routes operator prompts to agents |
| Discovery lab | `src/tools/discovery_lab.py` | **Partial** | What-If engine, Regime Scanner, SHAP; standalone — not integrated into dashboard |
| Journal (trade logging) | `src/tools/journal.py` | **Partial** | Code exists; automated trade logger not fully wired |
| SHAP feature importance | — | **Planned** | Discovery Lab spec calls for SHAP analysis on strategies |
| Colab session manager | — | **Planned** | `Manage_colab.md` describes resource management; no code yet |

---

## 12. Implementation Status — UI (Streamlit Dashboard)

> The dashboard is built as a **9-page Streamlit multi-page app** (`src/dashboard/app.py` + `pages/`).
> Page files exist for all 9 sections, but most contain **scaffold / placeholder UI** rather than live data connections.
> The source of truth for detailed gap analysis is `UI_Implementation_Gap.md`.

---

### 12.1 Global / App Shell

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-page Streamlit app (9 pages) | **Done** | All page files exist under `src/dashboard/pages/` |
| Wide layout (`layout="wide"`) | **Done** | Set in every page |
| Dark theme (custom CSS) | **Done** | `apply_theme()` in `src/dashboard/components.py` |
| Session state init | **Done** | `init_session_state()` in `src/dashboard/session_state.py` |
| Sidebar layout ratios (1:3 / 1:4 / 1:5 per page) | **Partial** | Config constants exist; not uniformly applied |
| Cross-page session state (selected strategy, date range, regime) | **Partial** | `st.session_state` keys defined; not all pages consume them |
| Plotly charts everywhere spec mandates | **Partial** | Home + Backtester use Plotly; others use placeholder text |
| Metrics color-coding (green >threshold / red <threshold) | **Partial** | `metric_card_simple` helper exists; thresholds not wired everywhere |
| Live data from Neon / MT5 / US30 CSV wired to UI | **Planned** | All pages currently use mock data or static DataFrames |

---

### 12.2 Page-by-Page Status

#### Home / Dashboard (`app.py`)

| Element | Spec | Status |
|---------|------|--------|
| Date range selector (default last 30 days) | 1 component | **Done** |
| 4 metric cards: P&L, Sharpe, Max DD, Active Strategies | 4 components | **Partial** — cards render; values are mock |
| "New Alpha Idea" button linking to Alpha Idea Lab | 1 button | **Done** |
| "View Live MT5 Feed" button | 1 button | **Partial** — button exists; no live feed wired |
| Regime / session multiselect filter | 1 component | **Done** |
| System Status expander (PM2, Neon, MT5 indicators) | 1 expander | **Partial** — Agent Status panel exists; PM2 + Neon + MT5 health not wired |
| Recent Activity Log table (5 rows) | 1 table | **Planned** — placeholder row shown; no real event log |
| Alpha decay alert (`st.info`) | 2 alerts | **Planned** |
| Cumulative P&L line chart (Plotly, full width) | 1 chart | **Partial** — chart renders with mock data |
| Regime Performance bar chart | 1 chart | **Partial** — chart renders with mock data |
| Signal Decay heatmap (strategies × months) | 1 chart | **Planned** |

**Overall: Partial — layout and scaffolding done; all data sources are mock**

---

#### Alpha Idea Lab (`pages/1_Alpha_Idea_Lab.py`)

| Element | Spec | Status |
|---------|------|--------|
| Natural language text area prompt | 1 component | **Done** |
| Template selectbox (5 options) | 1 component | **Done** |
| File uploader (DOCX/PDF, 10 MB) | 1 component | **Done** |
| Conversational chat display (up to 10 iterations) | chat UI | **Done** |
| "Generate Hypothesis" → Librarian Agent | 1 button | **Planned** — button structure exists; not wired to LibrarianAgent |
| RESEARCH_PLAN.md preview (markdown) | 1 markdown display | **Planned** |
| "Proceed to Builder" button + session state nav | 1 button | **Planned** |
| Progress bar for agent processing | 1 component | **Planned** |
| Redundancy warning (Neon check) | 1 alert | **Planned** |
| Advanced hypothesis tweaks expander (Hurst, regime tags) | 1 expander | **Planned** |
| US30 price vs volume scatter plot | 1 chart | **Planned** |
| Initial e-ratio / regime metrics display | metrics | **Planned** |

**Overall: Partial — UI scaffold and chat interface done; agent wiring and data entirely planned**

---

#### Vault Explorer (`pages/2_Vault_Explorer.py`)

| Element | Spec | Status |
|---------|------|--------|
| Folder tree / expander (Needs_Action, Plans, Approved, Reports, Logs) | 1 navigator | **Done** — expander-based folder selector |
| File search bar | 1 component | **Done** |
| File list table (Name, Date, Type, Status) | 1 table | **Partial** — renders; reads from vault filesystem |
| "Upload File" button | 1 button | **Done** |
| "Trigger Watcher" button | 1 button | **Partial** — button exists; not wired to `vault_watcher` |
| "Edit File" (inline markdown editor) | 1 button | **Planned** |
| Markdown file preview | 1 viewer | **Done** — selected file content rendered |
| Download button | 1 button | **Done** |
| File metadata expander (regime tags, linked strategies) | 1 expander | **Planned** |
| Bulk actions multiselect (move to Approved, delete) | 1 multiselect | **Planned** |
| Upload/scan success alert | 1 alert | **Planned** |

**Overall: Partial — file browsing and preview work; write operations and metadata are planned**

---

#### No-Code Strategy Builder (`pages/3_No_Code_Builder.py`)

| Element | Spec | Status |
|---------|------|--------|
| 8-step stepper (`st.progress` + Next buttons) | 1 stepper | **Partial** — tabs structure exists |
| 8 tabs (one per step) | 8 tabs | **Partial** — basic tabs present |
| Selectboxes per step (model type, edge type, etc.) | ~5/step | **Partial** — a few controls stubbed |
| Sliders (Layers, Dropout, Epochs, Batch Size) | 4 sliders | **Partial** — some present as scaffolding |
| Preprocessing multiselect | 1 component | **Planned** |
| "Generate Code" button → Strategist Agent | 1 button | **Planned** — button visible; not wired to StrategistAgent |
| Advanced Code View expander (editable Python) | 1 expander | **Planned** |
| Feature Impact table (Boruta scores) | 1 table | **Planned** |
| Agent suggestion alert (`st.info`) | 1 alert | **Planned** |
| Sample training curve line chart | 1 chart | **Planned** |
| Feature importance bar chart | 1 chart | **Planned** |

**Overall: Partial — UI scaffold exists; no agent integration or live model interaction**

---

#### Strategy Library (`pages/4_Strategy_Library.py`)

| Element | Spec | Status |
|---------|------|--------|
| Strategy search bar | 1 component | **Done** |
| Strategy list table (ID, Name, Status, Metrics) | 1 table | **Partial** — table renders with static sample rows |
| Status filters multiselect (drafts / production / graveyard) | 1 component | **Done** |
| "View Details" button + expanded detail | 1 button | **Partial** — expander structure exists |
| "Export to Pine Script" button | 1 button | **Planned** |
| Graveyard journal full expander | 1 expander | **Planned** |
| Code / report download button | 1 button | **Planned** |
| "Retrigger Validation" button | 1 button | **Planned** |
| Alpha decay alert (`st.error`) | 1 alert | **Planned** |
| Per-strategy metric cards (Sharpe, DD, Hit Rate, e-ratio) | 4 cards | **Partial** — cards rendered with mock values |
| Equity curve line chart | 1 chart | **Partial** — Plotly chart renders with mock data |
| Portfolio breakdown pie chart | 1 chart | **Planned** |

**Overall: Partial — browsing scaffold done; real data from models/ and failure_journal not wired**

---

#### Backtester & Killer (`pages/5_Backtester_Killer.py`)

| Element | Spec | Status |
|---------|------|--------|
| Strategy selectbox | 1 component | **Done** |
| Iterations slider (1k–10k) | 1 slider | **Done** |
| Stress tests multiselect | 1 component | **Done** |
| Walk-Forward / Out-of-Sample checkboxes | 2 checkboxes | **Done** |
| "Run Monte Carlo Pro" button | 1 button | **Partial** — button exists; shows placeholder info instead of calling `MonteCarloPro` |
| Progress bar for long runs | 1 component | **Planned** |
| Results table (metrics per run) | 1 table | **Partial** — static sample DataFrame shown |
| Market param sims expander | 1 expander | **Planned** |
| "Approve to Production" button | 1 button | **Planned** |
| "Journal Failure" button | 1 button | **Planned** — needs `failure_journal` wiring |
| Gate pass/fail alert | 1 alert | **Planned** |
| Returns distribution histogram | 1 chart | **Partial** — Plotly histogram renders with mock data |
| Regime-specific heatmap | 1 chart | **Partial** — heatmap renders with mock data |
| Drawdown box plot | 1 chart | **Planned** |
| MC Profiles tab | additional tab | **Partial** — tab exists; placeholder content |
| "Trigger Colab MC" button | 1 button | **Done** — links to Colab notebook URL |

**Overall: Partial — controls and chart scaffolding done; no real MonteCarloPro execution or Killer integration**

---

#### Optimization Lab (`pages/6_Optimization_Lab.py`)

| Element | Spec | Status |
|---------|------|--------|
| PPO / Genetic / Ensemble tab set | 3 tabs | **Done** |
| Hyperparameter sliders (LR, reward, epochs) | 4 sliders | **Done** |
| "Train Model" button | 1 button | **Partial** — button exists; shows info message (no training triggered) |
| US30 Gym env selectbox | 1 component | **Done** |
| Features multiselect (Transformers) | 1 component | **Planned** |
| Code hooks expander (editable) | 1 expander | **Planned** |
| Training progress bar | 1 component | **Planned** |
| Optimization results table | 1 table | **Planned** |
| "Save to Strategy" button | 1 button | **Planned** |
| Overfitting warning alert | 1 alert | **Partial** — Sharpe gap / overfitting section stubbed |
| "Run on Colab" button | 1 button | **Done** — links to Colab notebook |
| Learning curve (rewards vs episodes) | 1 chart | **Partial** — Plotly chart renders with mock data |
| Param sensitivity scatter | 1 chart | **Partial** — chart stubbed |
| Ensemble voting weights bar | 1 chart | **Planned** |

**Overall: Partial — controls and Colab links done; no actual training integration**

---

#### Execution & Reports (`pages/7_Execution_Reports.py`)

| Element | Spec | Status |
|---------|------|--------|
| Execution Monitor / Reports tab set | 2 tabs | **Done** |
| Auto-refresh toggle + slider | 2 controls | **Done** |
| Alpaca connection status indicator | 1 indicator | **Done** — live when Alpaca credentials set |
| Open positions table (Entry, Size, P&L) | 1 table | **Done** — live from Alpaca API when connected; mock fallback |
| Account summary metrics | metric cards | **Done** — live from Alpaca when connected |
| Cockpit (Signal Monitor, Risk Visualizer, Agent Status) | 3 panels | **Done** — renders via `render_cockpit()`; data is mock |
| "Approve Trade" button (HITL file move) | 1 button | **Planned** — not wired to `approval.py` |
| Real-time US30/MT5 ticker (every 10s) | 1 ticker | **Planned** |
| Cooldown / circuit breaker alert | 1 alert | **Planned** |
| Monday Briefing markdown preview | 1 display | **Planned** |
| "Send Report" button (Gmail/Telegram) | 1 button | **Planned** |
| Graveyard summaries expander | 1 expander | **Planned** |
| `/failure_report` button | 1 button | **Planned** |
| Full report PDF download | 1 download | **Planned** |
| Live US30 candlestick chart | 1 chart | **Planned** |
| Intraday P&L line chart | 1 chart | **Partial** — P&L curve renders with Alpaca data if connected |

**Overall: Partial — Alpaca account/positions live; cockpit renders with mock data; reporting and HITL actions planned**

---

#### Situational Analysis (`pages/8_Situational_Analysis.py`)

| Element | Status | Notes |
|---------|--------|-------|
| Page scaffold | **Partial** | File exists; content depends on current discovery_lab integration |
| What-If backtest engine | **Planned** | Wire `src/tools/discovery_lab.py` what-if engine |
| Regime scanner | **Planned** | Wire `regime_classifier.py` to display current regime per symbol |
| SHAP feature importance | **Planned** | Requires SHAP library install and model wiring |

---

#### Technical Analysis (`pages/9_Technical_Analysis.py`)

| Element | Status | Notes |
|---------|--------|-------|
| Page scaffold | **Partial** | File exists |
| Indicator overlay charts | **Planned** | pandas-ta indicators on US30 data via Plotly |
| Pattern annotation | **Planned** | Pattern detector output overlaid on price chart |

---

### 12.3 UI vs Backend Wiring Summary

| Page | UI Scaffold | Live Data | Agent Wiring |
|------|-------------|-----------|--------------|
| Home / Dashboard | Partial | Mock | None |
| Alpha Idea Lab | Partial | Mock | None (Librarian not wired) |
| Vault Explorer | Partial | Filesystem (read) | None (watcher not triggered) |
| No-Code Builder | Partial | Mock | None (Strategist not wired) |
| Strategy Library | Partial | Mock | None (models/ not scanned) |
| Backtester & Killer | Partial | Mock | None (MonteCarloPro not called) |
| Optimization Lab | Partial | Mock | None (training on Colab only) |
| Execution & Reports | Partial | **Alpaca live** (positions, account) | Partial (cockpit mock; HITL not wired) |
| Situational Analysis | Scaffold only | None | None |
| Technical Analysis | Scaffold only | None | None |

---

### 12.4 Priority Implementation Queue

Based on `UI_Implementation_Gap.md` and current backend readiness, the recommended order for closing the gaps:

1. **Backend data APIs** — wire Neon, vault filesystem, and strategy scanner to FastAPI endpoints so all pages have real data to consume.
2. **Home / Dashboard** — replace mock metrics and charts with live API calls; add decay heatmap and activity log.
3. **Alpha Idea Lab** — wire "Generate Hypothesis" to `LibrarianAgent` via `instruction_router`; display RESEARCH_PLAN.md output live.
4. **Vault Explorer** — connect "Trigger Watcher" to `vault_watcher`; add inline markdown editor and bulk-action support.
5. **Strategy Library** — scan `models/drafts/`, `models/production/`, and `Graveyard/`; pull journals from `failure_journal`.
6. **Backtester & Killer** — call `MonteCarloPro` + `KillerAgent` from the UI; show live results and wire Approve/Journal buttons.
7. **No-Code Strategy Builder** — complete 8-step wizard and wire "Generate Code" to `StrategistAgent`.
8. **Optimization Lab** — wire results API for completed Colab training runs; add param sensitivity scatter.
9. **Execution & Reports** — wire HITL Approve button to `approval.py`; add MT5 ticker; wire Reporter to Reports tab.
10. **Situational Analysis / Technical Analysis** — integrate `discovery_lab.py`, `regime_classifier`, and `pattern_detector`.

---

## 13. Deep-Dive Concepts & How They Actually Work

This section explains the core technical mechanisms in plain terms, tied directly to the code that implements them.

---

### 13.1 Bootstrap Loader — What It Is and What It Does

**File:** `src/memory/bootstrap_loader.py`

#### The Problem It Solves

Every LLM agent call starts with a blank context. Without shared grounding, the Librarian and Strategist would answer with generic advice instead of operating inside this system's specific rules, persona, and constraints.

#### What It Does

The bootstrap loader reads five markdown files from the workspace root and concatenates them into one context string that is injected at the top of every agent's LLM prompt:

```
AGENTS.md      → operating instructions (Ralph Wiggum loop, vault conventions, Zero-MQL rule)
SOUL.md        → values and epistemic stance (what the system believes about markets)
TOOLS.md       → list of tools and APIs available to agents
IDENTITY.md    → persona description (senior quant researcher persona)
USER.md        → operator profile, preferences, and constraints
```

#### How It Works (Step by Step)

```
1. load_bootstrap(workspace_root="c:/Users/User/Downloads/claude") is called
2. _resolve_root() picks the first existing path: workspace_root → vault_path → cwd
3. For each file in ("AGENTS.md", "SOUL.md", "TOOLS.md", "IDENTITY.md", "USER.md"):
   - If the file exists and is non-empty → read text
   - If missing → silently skip (no crash)
4. Surviving files are joined as:
   "## AGENTS.md\n\n<content>\n\n---\n\n## SOUL.md\n\n<content>\n\n---\n\n..."
5. The resulting string is prepended to every agent's LLM system prompt
```

#### Concrete Effect

When the Librarian Agent calls Claude or Gemini, the prompt starts with the full bootstrap context. This means Claude "knows" it is acting as a senior quant, must follow Zero-MQL conventions, must tag hypotheses by regime, must write plans to `Plans/`, and must check the institutional memory for redundancy — without any of those rules being re-stated per call.

**`as_dict=True` mode** returns `{"AGENTS.md": "<text>", "SOUL.md": "<text>", ...}` which the orchestrator uses to inject files selectively into different agents (e.g. only SOUL.md into Reporter, full set into Librarian).

---

### 13.2 Discovery Lab — What It Is Actually Doing

**File:** `src/tools/discovery_lab.py`

#### Purpose

Discovery Lab is a lightweight Streamlit research tool for **ad-hoc, interactive exploration** — it lets the operator test an idea quickly without running the full Ralph Wiggum loop. Think of it as a "scratchpad" between having a vague idea and formalising it into a `Needs_Action/` research note.

#### Three Tools It Contains

**1. What-If Engine**

Answers "what would have happened if I traded rule X?"

```python
run_what_if_backtest(params: dict) → DataFrame
```

The operator selects a strategy type (e.g. RSI Crossover, Moving Average Crossover), a lookback period, and a threshold via Streamlit sliders. The engine runs the rule against historical price data and returns an equity curve. The result is shown as a line chart in the UI.

*Current state:* The function returns dummy random data as a placeholder. The intent is to wire it to `us30_loader` + the backtest engine so real OHLCV is used.

**2. Regime Scanner**

Answers "what regime is each instrument currently in?"

```python
classify_regime(data) → "Trending" | "Ranging" | "Volatile"
detect_regime_shift(current, previous) → bool
```

The scanner loops over a watchlist (e.g. US30, DXY, equity indices), classifies each asset's current regime, compares it to the previous classification, and flags any transitions. Transitions trigger a `st.warning` alert in the UI.

*Current state:* Classification is random placeholder. The production wiring is to `src/ml/regime_classifier.py` which uses a trained Random Forest on rolling volatility, Hurst exponent, and autocorrelation features.

**3. Feature Importance Analyzer**

Answers "why did this strategy take that trade?"

```python
analyze_feature_importance(strategy_data, trade_data) → pd.Series  # feature → score
```

This is where **SHAP** is intended to plug in. The function takes strategy data (the feature matrix the model saw at trade time) and trade outcomes, then computes a ranked importance bar chart. The operator can see that, for example, "ATR" and "Volume Spike" drove 70% of the decision weight.

*Current state:* Returns random `np.random.rand()` scores. Production wiring requires `shap` library + the trained ML/DL model (see §13.3).

---

### 13.3 SHAP Analysis — What It Is and Why It Matters

#### What SHAP Is

**SHAP** (SHapley Additive exPlanations) is a game-theory method that answers the question: *"How much did each input feature contribute to this specific prediction?"*

For a single trade, SHAP decomposes the model's output into additive contributions from each feature:

```
prediction = base_value + SHAP(RSI) + SHAP(ATR) + SHAP(Volume) + SHAP(Hour) + ...
```

Each SHAP value has a sign (positive = pushed toward buy; negative = pushed toward hold/sell) and a magnitude (how much it moved the decision).

#### Why It Matters for This System

Standard backtesting tells you *whether* a strategy worked. SHAP tells you *why* it worked — and whether those reasons are still valid. Key uses:

| Use Case | Question Answered |
|----------|------------------|
| Trade attribution | Why did the model buy US30 at 09:35? |
| Regime robustness | Does ATR matter more in volatile regimes? |
| Feature pruning | Which inputs are noise vs signal? |
| Overfitting detection | Is the model relying on look-ahead features? |

#### How It Would Work in This Codebase

```python
import shap

# 1. Train the model (Random Forest or LSTM)
rf_model = ml_pattern_classifier(X_train, y_train)

# 2. Create SHAP explainer
explainer = shap.TreeExplainer(rf_model)   # for RandomForest
# or: shap.DeepExplainer(lstm_model, X_train_tensor)  # for PyTorch LSTM

# 3. Compute SHAP values for a trade
shap_values = explainer.shap_values(X_trade)  # shape: (n_features,) per class

# 4. Rank features by |SHAP|
importance = pd.Series(np.abs(shap_values[1]), index=feature_names).sort_values(ascending=False)

# 5. Display in Discovery Lab
st.bar_chart(importance)
```

The result is a bar chart where the tallest bar is the feature that most strongly pushed the model toward its decision on that specific trade. This is what `analyze_feature_importance()` in `discovery_lab.py` is designed to produce once wired to real models.

**Current status:** Planned. The `shap` library is not yet in `requirements.txt`. The `analyze_feature_importance()` function returns random placeholder values.

---

### 13.4 Pattern Detection — How It Actually Works

Pattern detection in this system uses **three layers**: a classical ML classifier (Random Forest), a deep learning model (LSTM), and an RL agent (PPO). Each layer operates on the same preprocessed OHLCV data and produces a signal: **buy (1), sell (2), or hold (0)**.

---

#### Step 1 — Data Preprocessing (`src/data/pattern_preprocessor.py`)

Raw OHLCV bars go through two transformations before any model sees them:

```python
preprocess_ohlcv(df, window_size=60) → {"scaled": ndarray, "reduced": ndarray, "df": df}
```

**MinMax scaling:** All five columns (Open, High, Low, Close, Volume) are scaled to [0, 1] so price level differences across time don't dominate the model.

```
scaled = MinMaxScaler().fit_transform(df[["Open","High","Low","Close","Volume"]])
```

**PCA dimensionality reduction:** The five scaled features are compressed via PCA, retaining 95% of variance. This removes collinear noise (Open/Close are often highly correlated) and speeds up LSTM training.

```
reduced = PCA(n_components=0.95).fit_transform(scaled)
```

The `window_size=60` parameter means the models see the last 60 bars as a sequence — one OHLCV snapshot per bar, 60 time steps total.

---

#### Step 2 — ML Layer: Random Forest Classifier (`src/edges/pattern_based/pattern_detector_ml.py`)

The Random Forest treats each 60-bar window as a flat feature vector and classifies it into one of three labels.

```python
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
rf.fit(X, y)   # X: (n_windows, n_features), y: (n_windows,) — 0=hold,1=buy,2=sell
```

**Prediction at runtime:**

```python
detect_pattern_ml(model, new_data) → int   # 0, 1, or 2
```

It reshapes the incoming feature vector to `(1, n_features)` and calls `model.predict()`. The integer output maps to hold/buy/sell.

**Why Random Forest first?**
- Fast to train, no GPU needed, runs locally.
- Feature importances are directly readable (no SHAP needed).
- Provides a baseline to beat with the DL layer.

---

#### Step 3 — DL Layer: LSTM (`src/edges/pattern_based/pattern_detector_dl.py`)

The LSTM (Long Short-Term Memory) sees the full 60-step sequence as a 3D tensor — capturing temporal dependencies that the flat RF cannot.

```
Architecture:
  Input:  (batch, 60 timesteps, 5 features)   ← OHLCV per bar
  LSTM:   hidden_size=50
  FC:     50 → 3                              ← logits for hold/buy/sell
```

```python
class PatternLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=50):
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc   = nn.Linear(hidden_size, 3)

    def forward(self, x):
        _, (hn, _) = self.lstm(x)   # hn = final hidden state
        return self.fc(hn.squeeze(0))
```

**Training:**

```python
train_pattern_lstm(X_seq, y_labels, epochs=10)
# X_seq shape: (n_samples, 60, 5)
# y_labels:    (n_samples,)  — 0/1/2
# Loss: CrossEntropyLoss; Optimizer: Adam(lr=0.001)
```

The model runs in a plain training loop (no validation split in the current stub). Production use on Colab adds early stopping, a validation set, and checkpoint saving to Google Drive.

**Why LSTM over simple RNN?**
LSTM has gated memory (forget gate, input gate, output gate) so it can remember relevant events from 60 bars ago without the gradient vanishing. This matters for patterns like head-and-shoulders where the first shoulder may be 30–40 bars before the signal.

---

#### Step 4 — RL Layer: PPO Pattern Agent (`src/edges/pattern_based/pattern_rl_agent.py`)

The RL agent wraps the preprocessed data in an OpenAI Gym environment and trains a PPO (Proximal Policy Optimization) policy that learns *when to act* based on the signal from the ML/DL layers.

The RL agent's reward function incorporates:
- Returns from the price data at that bar
- Slippage cost proportional to position size
- The goal: maximize cumulative reward (risk-adjusted returns) rather than raw accuracy

This is fundamentally different from the ML/DL layers — those classify *what the pattern is*; the RL agent learns *whether it is worth trading right now* given current market conditions.

---

#### Full Pattern Detection Pipeline

```
OHLCV bars (raw)
      │
      ▼
preprocess_ohlcv()                 ← MinMax scale + PCA reduce
      │
      ├─► ML layer (Random Forest)  ← flat feature vector → buy/sell/hold
      │
      ├─► DL layer (LSTM)           ← 60-bar sequence → buy/sell/hold
      │
      └─► RL layer (PPO)            ← gym env: reward = returns - slippage
                                       learns when to act on ML/DL signal
      │
      ▼
Signal vote (ensemble or priority)
      │
      ▼
BaseStrategy.entry() / .exit()    ← consumed by Strategist-generated strategy
```

---

### 13.5 Monte Carlo Pro — How It Actually Works

**File:** `src/tools/monte_carlo_pro.py`

The `MonteCarloPro` class is the statistical gatekeeper of the entire system. Every draft strategy must pass through it before it can be approved. It runs up to 10,000 simulated "what could have happened" scenarios to stress-test whether a strategy's historical results are robust or lucky.

#### The Core Question It Answers

> "If the trade order had been slightly different, or market conditions slightly worse, would this strategy have survived?"

Standard backtesting gives one equity curve — the one that actually happened. Monte Carlo gives a *distribution* of 10,000 equity curves so we can measure the tail risk.

---

#### Phase 1 — Trade Sequence Randomization (`simulate_paths`)

```python
mc = MonteCarloPro(iterations=10000, confidence_level=0.95)
results = mc.simulate_paths(returns=strategy_returns, initial_capital=100_000)
```

**What happens inside each of the 10,000 iterations:**

```python
for _ in range(10_000):
    # 1. Bootstrap: randomly resample the trade returns WITH replacement
    #    (same returns, different order — tests path dependency)
    shuffled = np.random.choice(returns_arr, size=len(returns_arr), replace=True)

    # 2. Build the equity curve from this shuffled sequence
    equity_path = 100_000 * np.cumprod(1 + shuffled)

    # 3. Measure maximum drawdown for this path
    peak     = np.maximum.accumulate(equity_path)
    drawdown = (equity_path - peak) / peak
    max_dd   = np.min(drawdown)

    results.append(equity_path[-1])   # final portfolio value
    max_dds.append(max_dd)
```

**Why bootstrap resampling?** A strategy might look great because its best trades happened early when capital was low. Bootstrap resampling shuffles the order and asks: what if those big winners had come later? This surfaces path dependency — strategies that only work if lucky trade order is preserved.

**Output metrics:**

| Metric | How Computed | What It Measures |
|--------|-------------|-----------------|
| `var_95` | 5th percentile of 10,000 final values | Worst-case ending portfolio (95% confidence) |
| `expected_shortfall` | Mean of bottom 5% of ending values | Average loss in the tail (CVaR) |
| `prob_of_ruin` | Fraction of paths ending below 50% of starting capital | Probability of catastrophic loss |
| `max_dd_dist` | Distribution of max drawdowns across all paths | Full range of drawdown risk |

---

#### Phase 2 — Friction Injection (`inject_execution_friction`)

Before paths are simulated, real-world execution costs are added to the returns:

```python
adjusted_returns = mc.inject_execution_friction(
    returns,
    slippage_pct=0.0002,   # 2 basis points average slippage
    latency_shocks=0.1     # 10% of trades hit a "latency shock"
)
```

**What this models:**

```python
noise  = np.random.normal(0, slippage_pct, size=n)     # random fill imprecision
shocks = np.where(random < latency_shocks, -slippage*2, 0)  # 10% of fills are worse
adjusted = returns + noise + shocks
```

Every trade gets random fill noise. 10% of trades get an extra 4-basis-point penalty simulating a delayed fill (latency shock). This means a strategy that barely passes on clean returns often fails when friction is included — exactly the kind of curve-fitting the Killer Agent is designed to catch.

---

#### Phase 3 — Named Regime Stress Tests (`regime_stress_tests`)

```python
regime_results = mc.regime_stress_tests(returns, initial_capital=100_000)
```

Three named regimes are tested, each defined by a volatility multiplier:

| Regime | Multiplier | Represents |
|--------|-----------|------------|
| `2020_crash` | ×2.5 | COVID crash volatility surge |
| `2022_bear` | ×1.8 | Fed rate-hike bear market |
| `2023_chop` | ×1.2 | Low-conviction choppy market |

For each regime, all returns are scaled by the multiplier and `simulate_paths()` is run again. The output is a dict of `{regime_name: {prob_of_ruin, var_95, expected_shortfall}}`. A strategy that survives normal conditions but has `prob_of_ruin > 0.3` in a 2020-crash scenario fails the Killer's gate.

---

#### Phase 4 — Parameter Stability / Overfitting Cliff (`parameter_stability_tests`)

```python
stability = mc.parameter_stability_tests(returns, n_nudges=20, nudge_pct=0.10)
```

This test nudges the strategy's returns by ±10% randomly, 20 times, and checks whether `prob_of_ruin` stays stable:

```python
for _ in range(20):
    scale  = 1 + np.random.uniform(-0.10, +0.10, size=n)   # ±10% nudge
    nudged = returns * scale
    prob_ruins.append(simulate_paths(nudged)["prob_of_ruin"])
```

**Output:**

```python
{
  "prob_of_ruin_mean": 0.04,
  "prob_of_ruin_std":  0.12,   # high std = fragile / overfit
  "overfit_cliff_flag": True   # triggered if std > 0.05 OR (max-min) > 0.10
}
```

A well-generalised strategy should have nearly the same ruin probability whether returns are 10% higher or lower. If `overfit_cliff_flag=True`, the strategy lives on a knife-edge — it only worked for its exact historical parameters and will likely fail live.

---

#### Phase 5 — Decision Output (`get_decision_metrics`)

```python
report = mc.get_decision_metrics(sim_results, initial_capital=100_000)
```

Produces a human-readable summary:

```
Alpha Probability Profile:
- Win Probability:            78.30%
- 95% Value at Risk:          $91,240.00
- Worst Case Drawdown (99th): -34.2%
```

This text is written to `Logs/Risk_Audit_<timestamp>.md` and optionally stored in the Neon `audit_log` table.

---

#### Full Monte Carlo Decision Flow (Killer Agent)

```
Draft strategy file (strategy_X.py)
          │
          ▼
    Load trade returns from US30Loader
          │
          ▼
┌─────────────────────────────────────┐
│   inject_execution_friction()       │ ← add slippage + latency shocks
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       simulate_paths() ×10,000      │ ← bootstrap resample; measure VaR, DD, ruin
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│     regime_stress_tests()           │ ← 2020 crash, 2022 bear, 2023 chop
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│  parameter_stability_tests()        │ ← ±10% nudge × 20; overfit cliff flag
└─────────────────┬───────────────────┘
                  │
          PASS criteria met?
         /                  \
        YES                  NO
         │                   │
   models/production/    Graveyard/
   Risk_Audit_*.md       + failure_journal.py post-mortem
   (Neon audit_log)
```

---

### 13.6 Edges & Strategy Models — How It All Works

**Files:** `src/edges/`, `src/edges/edge_registry.py`, `src/models/base_strategy.py`

#### What an "Edge" Is

In trading, an **edge** is a systematic, repeatable reason why a trade has positive expected value. It is not a hunch — it is a statistically measurable property of price behaviour. The system defines 8 edge types:

| Edge Type | What It Exploits | Keywords |
|-----------|-----------------|---------|
| `statistical` | Price pairs that move together and revert when they diverge | cointegration, z-score, pairs |
| `pattern_based` | Recurring candlestick/chart formations that precede directional moves | head-and-shoulders, candlestick, chart pattern |
| `volume_based` | Institutional order-flow signatures in volume data | VWAP, TWAP, volume spike, institutional |
| `market_structure` | ICT-style price mechanics: order blocks, fair value gaps, liquidity sweeps | order block, FVG, BOS, liquidity |
| `tokenized_assets` | Cross-chain arbitrage and RWA mispricing | tokenized RWA, BUIDL, gas |
| `geopolitical` | Macro regime shifts driven by geopolitical events | EM, multipolar, USD weak, conflict |
| `prediction_event` | Information embedded in prediction market prices before events | Polymarket, Kalshi, earnings |
| `ai_enhanced` | Sentiment, factor mining, momentum extracted from news and text | sentiment, BERT, microstructure |

---

#### The Edge Registry (`src/edges/edge_registry.py`)

The registry is the central lookup table that connects a natural-language instruction to the code that implements the edge.

```python
@dataclass
class EdgeInfo:
    edge_type:       str          # "volume_based"
    keywords:        List[str]    # ["VWAP", "volume spike", ...]
    core_modules:    List[str]    # ["src.edges.volume_based.volume_analyzer", ...]
    models_used:     List[str]    # ["RandomForest", "CNN", "PPO"]
    data_sources:    List[str]    # ["Polygon tick/agg"]
    workflow_module: Optional[str]# "src.edges.volume_based.volume_workflow"
```

When the operator writes "US30 opens strong on low DXY + institutional volume spike", the Instruction Router calls:

```python
match_instruction_to_edges(instruction) → [EdgeInfo(edge_type="volume_based"), ...]
```

It scans `instruction.lower()` for keywords from each EdgeInfo. If "volume spike" appears, the volume_based edge is selected. The matched EdgeInfo is passed to the Strategist Agent so it knows which modules and models to reference when writing the strategy code.

The Librarian and Strategist also receive a compact summary via:

```python
registry_summary_for_llm() →
  "Edge registry (use these when generating code):
   - statistical: modules src.edges.statistical_edges; workflow src.edges.statistical_workflow
   - pattern_based: modules src.edges.pattern_based.pattern_workflow; ...
   ..."
```

This string is injected into the LLM prompt so the agent knows exactly which importable modules exist.

---

#### The BaseStrategy Contract (`src/models/base_strategy.py`)

Every strategy generated by the Strategist Agent must be a subclass of `BaseStrategy`. This is a hard constraint enforced by the Killer Agent when it imports the strategy file.

```python
class BaseStrategy(ABC):

    @abstractmethod
    def entry(self, state: Dict[str, Any]) -> bool:
        """True → open a position now."""
        # state contains: Open, High, Low, Close, Volume, any indicators

    @abstractmethod
    def exit(self, state: Dict[str, Any]) -> bool:
        """True → close position now."""

    @abstractmethod
    def risk(self, state: Dict[str, Any]) -> float:
        """Return fraction of capital to risk (0 = skip this bar)."""
```

**Why this contract matters:**
- The Killer Agent can backtest *any* `BaseStrategy` subclass with the same loop — it does not need to know what the strategy does internally.
- The Risk Architect can call `strategy.risk()` to get position size before sizing decisions.
- The Execution Manager calls `strategy.entry()` / `strategy.exit()` for live trading without knowing strategy internals.

---

#### Volume-Based Edge — Full Workflow Example

The volume-based edge is the most fully implemented workflow and shows how all layers connect.

**`VolumeWorkflow` (`src/edges/volume_based/volume_workflow.py`):**

```
Step 1: get_data()
   load_volume_data(csv_path)       ← reads US30 CSV or connector
   preprocess_volume_data(df)       ← computes VWAP deviation, volume z-score, spike_label
   add returns column               ← pct_change on Close for RL reward

Step 2: run_models(data)
   train_volume_classifier(df)      ← Random Forest on spike_label
   train_rl_volume(df)              ← PPO agent in VolumeEnv
   returns {"rf": rf, "rl_model": ..., "accuracy": acc, "returns": returns}

Step 3: validate(signals, data)     ← inherited from BaseEdgeWorkflow
   runs MonteCarloPro on returns
   returns (pass: bool, audit: dict)
```

**Random Forest in volume_analyzer.py:**

```python
X = df.drop("spike_label", axis=1)   # VWAP deviation, volume z-score, etc.
y = df["spike_label"]                 # 1 = institutional volume spike, 0 = normal
rf.fit(X_train, y_train)
accuracy, precision, feature_importances = evaluate(rf, X_test, y_test)
```

**PPO RL Agent in volume_rl_agent.py:**

The `VolumeEnv` gym environment works like this:

```
observation: current bar features (VWAP deviation, z-score, etc.)  — continuous vector
action:      continuous value in [-1, 1]
             +1 = full long, -1 = full short, 0 = flat
reward:      returns[t] × action  (profit)
             − |action| × 0.0001  (slippage cost)
done:        True when all bars consumed
```

The PPO agent learns a policy: given the observation vector, what action maximises cumulative reward? After `total_timesteps` of interaction with the environment, the policy can generate trading signals on new data via `model.predict(obs)`.

---

#### How the Strategist Assembles a Strategy from Edges

When the Strategist Agent generates a strategy file, it follows this pattern:

```python
# 1. Import the relevant edge module (from EdgeInfo.core_modules)
from src.edges.volume_based.volume_analyzer import train_volume_classifier

# 2. Subclass BaseStrategy (mandatory)
class VolumeBreakoutStrategy(BaseStrategy):

    def entry(self, state):
        # Use the RF model's spike_label prediction
        vol_z_score = state.get("volume_z_score", 0)
        return vol_z_score > 2.0      # 2 standard deviations above mean volume

    def exit(self, state):
        return state.get("volume_z_score", 0) < 0.5   # volume normalised

    def risk(self, state):
        # Risk Architect will override this with Kelly sizing
        return 0.01   # 1% of capital per trade (default)
```

The Killer Agent imports this file, instantiates the class, runs a historical backtest using `entry()` / `exit()` / `risk()`, collects the resulting returns series, and passes it to `MonteCarloPro`.

---

#### Edge Selection → Strategy Generation → Validation Flow

```
Operator input: "volume spike on US30 at session open"
         │
         ▼
match_instruction_to_edges()
  → EdgeInfo(edge_type="volume_based",
             modules=["volume_analyzer", "volume_rl_agent"],
             models=["RandomForest", "PPO"])
         │
         ▼
Librarian writes RESEARCH_PLAN_volume_spike.md
  (hypothesis, regime tags, instruments, risk params)
         │
         ▼
Strategist reads plan + EdgeInfo + registry_summary_for_llm()
  → generates VolumeBreakoutStrategy(BaseStrategy) in models/drafts/
         │
         ▼
Killer Agent:
  1. Imports strategy
  2. Runs historical backtest → returns series
  3. inject_execution_friction()
  4. simulate_paths() × 10,000
  5. regime_stress_tests()
  6. parameter_stability_tests()
  7. get_decision_metrics()
         │
         ▼
  PASS → models/production/ + Risk_Audit_*.md
  FAIL → Graveyard/ + failure_journal post-mortem
         │
         ▼
Risk Architect adds Kelly sizing + circuit breakers
         │
         ▼
Operator places file in Approved/ (HITL)
         │
         ▼
Execution Manager routes orders via Alpaca / MT5
```

---

## 14. API Reference — External APIs & Internal Endpoints

This section documents every external API the system calls, plus the internal FastAPI backend, covering **how** each is used, **when** it is called, and **why** it was chosen.

---

### 14.1 Anthropic Claude API

| Attribute | Value |
|-----------|-------|
| **Library** | `anthropic` (Python SDK) |
| **Module** | `src/tools/llm_client.py` → `AnthropicLLMClient` |
| **Env var** | `ANTHROPIC_API_KEY` |
| **Model** | `claude-3-5-sonnet-20241022` (default) |
| **Max tokens** | 4096 |

**How it is called:**

```python
client = AnthropicLLMClient(model="claude-3-5-sonnet-20241022", max_tokens=4096)
response = await client.complete(prompt=user_prompt, system=bootstrap_context)
# Internally calls: await anthropic.AsyncAnthropic.messages.create(...)
```

The call is always **async** (`AsyncAnthropic`). The `system` parameter receives the full bootstrap context (AGENTS.md + SOUL.md + IDENTITY.md + USER.md concatenated). The `messages` list always contains a single `{"role": "user", "content": prompt}` entry.

**When it is called:**
- `LibrarianAgent.reason()` — to extract alpha hypotheses and write a structured RESEARCH_PLAN
- `StrategistAgent.reason()` — to generate `BaseStrategy` subclass Python code
- `PatternAgent.generate_pattern_hypothesis()` — optionally, to generate a pattern-specific hypothesis

**Why Anthropic Claude:**
- Strong structured output adherence (produces valid Python code and markdown reliably)
- Long context window to absorb full bootstrap (AGENTS.md + vault files) in one call
- Async SDK matches FastAPI's async request model
- Primary LLM; Gemini is the fallback when `ANTHROPIC_API_KEY` is absent

**Fallback behaviour:** If `ANTHROPIC_API_KEY` is not set, `_get_client()` raises `RuntimeError` and the orchestrator falls back to `GeminiLLMClient`.

---

### 14.2 Google Gemini API

| Attribute | Value |
|-----------|-------|
| **Library** | `google-generativeai` |
| **Module** | `src/tools/llm_client.py` → `GeminiLLMClient` |
| **Env var** | `GEMINI_API_KEY` |
| **Model** | `gemini-1.5-flash` (default) |

**How it is called:**

```python
client = GeminiLLMClient(model_name="gemini-1.5-flash")
response = await client.complete(prompt=user_prompt, system=bootstrap_context)
# Internally: genai.configure(api_key=...) then model.generate_content_async(full_prompt)
```

Because Gemini does not have a separate `system` parameter in all SDK versions, the system context is prepended inline:

```python
full_prompt = f"System: {system}\n\nUser: {prompt}"
```

If `generate_content_async` fails (version incompatibility), it falls back to the synchronous `model.generate_content()`.

**When it is called:**
- Same agents as Claude (Librarian, Strategist) — used when `ANTHROPIC_API_KEY` is not set
- Both clients share the `BaseLLMClient` abstract interface so agents do not need to change

**Why Gemini as fallback:**
- Free tier with generous quota for development
- `gemini-1.5-flash` is fast for iteration during local dev
- Easy switch: same `complete(prompt, system)` interface as Claude

---

### 14.3 Alpaca Markets API

| Attribute | Value |
|-----------|-------|
| **Library** | `alpaca-py` |
| **Module** | `src/connectors/alpaca_connector.py`, `src/api/alpaca_service.py` |
| **Env vars** | `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER` (`true`/`false`), `ALPACA_TICKER_SYMBOL` |
| **Base URL (paper)** | `https://paper-api.alpaca.markets` |
| **Base URL (live)** | `https://api.alpaca.markets` |

Alpaca provides two client types used differently:

#### Trading Client (`alpaca.trading.client.TradingClient`)

Handles account management and order execution.

```python
from alpaca.trading.client import TradingClient
tc = TradingClient(api_key=key, secret_key=secret, paper=True)

# Used for:
tc.get_account()           # equity, cash, buying_power
tc.get_all_positions()     # open positions list
tc.submit_order(req)       # place market or limit order
tc.get_clock()             # market open/close times (MCP resource)
```

**When used:**
- `GET /account` endpoint — return equity, cash, buying power to dashboard
- `GET /positions` endpoint — open positions for Execution & Reports page
- `GET /alpaca/status` — checks if credentials are valid
- `execute_order()` — called by `ExecutionManager` after HITL approval
- MCP server `get_account_info`, `get_positions`, `submit_order` tools

#### Data Client (`alpaca.data.historical.StockHistoricalDataClient`)

Fetches historical OHLCV bars via REST with cache.

```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
dc = StockHistoricalDataClient(api_key=key, secret_key=secret)

req = StockBarsRequest(
    symbol_or_symbols="SPY",
    timeframe=TimeFrame(1, TimeFrameUnit.Hour),
    start=..., end=..., limit=100,
    feed=DataFeed.IEX,          # IEX = free tier; SIP requires paid plan
)
bars = dc.get_stock_bars(req)
```

**When used:**
- `get_ohlcv(symbol, timeframe, count)` — called by `AlpacaConnector` for backtesting data, portfolio history curve, and live ticker fallback
- Cache (`CacheManager`) is checked first with TTL of 60 seconds — REST is only hit on cache miss
- `DataFeed.IEX` is used by default (free tier); SIP feed requires Alpaca Algo Trader Plus subscription

#### WebSocket Stream (`alpaca.data.live.StockDataStream`)

Real-time bar, trade, and quote streaming in a background thread.

```python
stream = StockDataStream(api_key=key, secret_key=secret)
stream.subscribe_bars(_bar_handler, "US30", "US100")
stream.subscribe_quotes(_quote_handler, "US30")
stream.run()   # blocking; runs in daemon thread via threading.Thread
```

**When used:**
- `AlpacaConnector.start_stream(symbols)` — started by `market_stream.py` for live data
- Received events are broadcast to registered listeners via `connector.on("bar", callback)`
- Live bars update the cache so REST calls stay fresh

#### Order Types Supported

| Order | Request Class | When Used |
|-------|--------------|-----------|
| Market | `MarketOrderRequest` | Default execution; immediate fill |
| Limit | `LimitOrderRequest` + `limit_price` | When strategy specifies a price target |

Both use `TimeInForce.GTC` (Good Till Cancelled) by default.

#### Multi-Account Failover

If `ALPACA_API_KEY_2` and `ALPACA_SECRET_KEY_2` are set, a backup `TradingClient` is initialised. `ExecutionManager` can call `execute_order_backup()` if the primary account hits a risk limit or returns a rate-limit error.

**Why Alpaca:**
- Commission-free US equities and fractional shares
- Paper trading environment mirrors live API exactly — no code changes to go live
- Official Python SDK (`alpaca-py`) with async-compatible clients
- WebSocket streaming without extra cost

---

### 14.4 MetaTrader 5 (MT5) Python API

| Attribute | Value |
|-----------|-------|
| **Library** | `MetaTrader5` (Windows DLL wrapper) |
| **Module** | `src/connectors/mt5_connector.py` |
| **Constraint** | **Windows-only** — MT5 is a native Win32 DLL |
| **Env vars** | MT5 login/password/server (configured in terminal) |

**How it works:**

```python
import MetaTrader5 as mt5

mt5.initialize()                            # connect to running MT5 terminal
mt5.copy_rates_from_pos(symbol, tf, 0, n)   # fetch last N OHLCV bars
mt5.order_send(request_dict)                # place order
mt5.positions_get(symbol=symbol)            # open positions
mt5.account_info()                          # balance, equity, margin
mt5.shutdown()                              # disconnect
```

The connector maps internal timeframe strings (`"1h"`, `"5m"`) to MT5 constants (`mt5.TIMEFRAME_H1`, `mt5.TIMEFRAME_M5`) via a lookup dict.

**Zero-MQL rule:** All logic lives in Python. The MT5 terminal is used purely as a **dumb execution gateway** — it receives orders from Python and returns price data. No Expert Advisors (EAs) or MQL scripts are used.

**When it is called:**
- `get_ohlcv(symbol, timeframe, count)` — fetches US30 bars when `BROKER_TYPE=mt5`
- `execute_order(symbol, side, qty)` — sends market/limit orders to MT5 terminal
- `market_stream.py` — polls MT5 for tick data (no native WebSocket; polling interval configurable)

**On Linux / Colab (WSL2):** `connect()` fails gracefully and logs a bridge message:
```
"MT5 is Windows-native. Run a REST/Socket bridge on Windows host for Linux access."
```

**Why MT5 alongside Alpaca:**
- MT5 provides access to CFDs (US30, XAUUSD, Forex pairs) that Alpaca does not offer
- Alpaca handles US equities; MT5 handles indices and FX
- `BROKER_TYPE` env var switches which connector the `connector_factory` creates — no code change required

---

### 14.5 Neon (PostgreSQL) — asyncpg

| Attribute | Value |
|-----------|-------|
| **Library** | `asyncpg` |
| **Module** | `src/db/db_handler.py` |
| **Env var** | `DATABASE_URL` (Neon connection string) |
| **Protocol** | PostgreSQL wire protocol over TLS |

**How it is called:**

```python
import asyncpg

pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)

# Insert a validated alpha
await pool.execute("""
    INSERT INTO alphas (hypothesis, regime, edge_type, created_at)
    VALUES ($1, $2, $3, NOW())
""", hypothesis_text, "trending", "volume_based")

# Query graveyard for Reporter context
rows = await pool.fetch("SELECT * FROM graveyard ORDER BY created_at DESC LIMIT 20")
```

**When it is called:**
- `KillerAgent` — writes `Risk_Audit` entry to `audit_log` table after Monte Carlo run
- `LibrarianAgent` — queries `alphas` table to detect redundant hypotheses before writing a plan
- `ReporterAgent` — reads `graveyard` and `audit_log` for Monday briefing context
- `state_sync.py` — flushes session state to Neon every 60 seconds during an orchestrator run
- Graceful degradation: if `DATABASE_URL` is not set, all DB operations are skipped and the system operates in vault-only mode

**Core tables:**

| Table | Written by | Read by |
|-------|-----------|---------|
| `alphas` | Librarian | Librarian (dedup check), Reporter |
| `graveyard` | Killer | Reporter, Discovery Lab |
| `regimes` | Regime Classifier | Strategist, Librarian |
| `audit_log` | Killer | Reporter, Dashboard (planned) |

**Why asyncpg over SQLAlchemy:**
- Raw asyncpg has ~3× lower overhead than SQLAlchemy async for high-throughput write paths (actor-critic episode logging)
- No ORM magic needed — schema is simple and fixed
- Neon serverless Postgres scales to zero when idle, matching the non-continuous orchestrator run pattern

---

### 14.6 Internal FastAPI Backend

**Base URL:** `http://localhost:8000` (configurable via `TRADER_API_URL` env var)

All endpoints are consumed by the Streamlit dashboard via `requests.get()` with a 3-second timeout. If the API is unreachable, every page falls back to mock/empty data silently.

#### Health & Status

| Endpoint | Method | Response | When Called |
|----------|--------|----------|-------------|
| `/` | GET | `{"message": "...", "timestamp": "..."}` | Dashboard startup health check |
| `/status` | GET | `SystemStatus` (agents list) | Agent Status panel on Home and Execution pages, refreshed on interval |
| `/alpaca/status` | GET | `{"connected": bool}` | Sidebar connection indicator on Execution & Reports page |

#### Dashboard Metrics

| Endpoint | Method | Response | When Called |
|----------|--------|----------|-------------|
| `/metrics` | GET | `PerformanceMetrics` (P&L, Sharpe, Sortino, DD, Hit Rate, e-ratio) | Home page metric cards; uses live Alpaca account if keys set, else mock |
| `/activity` | GET | `List[ActivityEntry]` | Recent Activity table on Home page; currently mock |
| `/risk` | GET | `RiskMetrics` (VaR, drawdown, exposure) | Cockpit Risk Visualizer; uses Alpaca positions for real exposure when available |
| `/signals` | GET | `List[Signal]` | Cockpit Signal Monitor; currently mock |

#### Alpaca-Backed Endpoints

These return live data when `ALPACA_API_KEY` is set; otherwise return empty/mock.

| Endpoint | Method | Response | When Called |
|----------|--------|----------|-------------|
| `/account` | GET | `AccountSummary` (equity, cash, buying_power) | Execution & Reports page account summary |
| `/positions` | GET | `List[PositionSummary]` | Open positions table on Execution page |
| `/portfolio/history?days=30` | GET | `{"history": [...], "source": "alpaca"}` | P&L curve on Home and Execution pages |
| `/quote?symbol=SPY` | GET | `QuoteSummary` (bid, ask, mid) | Live ticker on Execution page; symbol defaults to `ALPACA_TICKER_SYMBOL` env var |

#### Portfolio History — How It Works

Alpaca's free-tier API does not provide a direct portfolio equity history endpoint. The service synthesises it from bar data:

```python
# Fetches daily bars for ALPACA_TICKER_SYMBOL (default: SPY)
df = connector.get_ohlcv(symbol, "1d", days)
# Builds pct-change curve from first close as base
pnl_pct = (close / first_close - 1) * 100
```

This is a proxy curve using the ticker symbol's price, not the account's actual equity curve — a known limitation until Alpaca Portfolio History API is available on the account plan.

#### Response Models (Pydantic)

```python
class PerformanceMetrics(BaseModel):
    pnl_pct: float          # e.g. 12.5 (percent)
    sharpe: float           # e.g. 1.8
    sortino: float          # e.g. 2.1
    max_drawdown_pct: float # e.g. -8.2
    hit_rate: float         # e.g. 0.58
    e_ratio: float          # e.g. 1.6
    active_strategies: int
    total_strategies: int
    delta_sharpe: float | None   # week-over-week change

class PositionSummary(BaseModel):
    symbol: str
    qty: float
    side: str               # "long" | "short"
    market_value: float
    unrealized_pl: float
    entry_price: float | None
    current_price: float | None
```

---

### 14.7 MCP (Model Context Protocol) — Alpaca Server

**File:** `src/mcp/alpaca_server.py`  
**Transport:** stdio (JSON-RPC 2.0)  
**Run:** `python -m src.mcp.alpaca_server`

MCP is a protocol that lets LLMs call tools and read resources via a standardised JSON-RPC interface. The Alpaca MCP server exposes broker functionality directly to Claude Desktop or IDE plugins without going through the FastAPI backend.

#### Tools Exposed

| Tool | Description | When an LLM Calls It |
|------|-------------|---------------------|
| `get_market_data` | Fetch OHLCV bars for a symbol | When agent needs price context to reason about an alpha |
| `submit_order` | Place market or limit order | When agent is authorised to act (only after HITL approval in Approved/) |
| `get_positions` | List all open positions | When agent needs portfolio context for risk or reporting |
| `get_account_info` | Return balance, equity, buying power | When agent needs account state for sizing decisions |

#### Resources Exposed

| Resource URI | Content | Used For |
|-------------|---------|---------|
| `alpaca://market_status` | `{is_open, next_open, next_close}` | Agent checks market hours before scheduling execution |
| `alpaca://account` | Account snapshot | Quick account context in prompts |

#### Prompt

| Prompt | Description |
|--------|-------------|
| `analyze_portfolio` | Pre-fills account + positions + market status into a senior analyst prompt for Claude |

#### How the JSON-RPC Handshake Works

```
Client (Claude / IDE plugin)     →  Server (alpaca_server.py via stdin)
{"method": "initialize", ...}    ←→  {"capabilities": {tools, resources, prompts}}
{"method": "tools/list"}         ←→  [get_market_data, submit_order, ...]
{"method": "tools/call",
 "params": {"name": "get_market_data",
            "arguments": {"symbol": "SPY", "timeframe": "1h", "limit": 50}}}
                                 ←→  {"content": [{"type": "text", "text": "{bars: [...]}"}]}
```

**Why MCP instead of direct API calls:**
- Standardised protocol — works with Claude Desktop, Cursor IDE, and any MCP-compatible client without custom integrations
- LLMs call tools by name with typed arguments; no raw HTTP in prompt context
- Falls back to a DIY JSON-RPC loop when the `mcp` SDK package is not installed

---

### 14.8 yfinance

| Attribute | Value |
|-----------|-------|
| **Library** | `yfinance` |
| **Used in** | Colab notebooks (`colab/us30_model_research.ipynb`, `colab/us30_dxy_equity_vs_fx.ipynb`) |
| **Auth** | None (public, rate-limited) |

**How it is called:**

```python
import yfinance as yf

df = yf.download("^DJI", start="2018-01-01", end="2024-01-01", interval="1d")
dxy = yf.download("DX-Y.NYB", period="5y", interval="1d")
```

**When it is called:**
- Only in **Colab research notebooks** — never in production Python modules
- Used for broad market research: US30 (`^DJI`), DXY, equity indices, correlation studies
- Provides multi-year OHLCV freely without an API key

**Why yfinance (not Alpaca) for research:**
- Alpaca covers US equities (SIP/IEX feeds); it does not provide DXY or direct Dow Jones index data
- yfinance covers indices, FX, commodities, and ETFs in one uniform `download()` call
- Research notebooks are exploratory; yfinance's simplicity reduces setup time on Colab

**Not used in `src/`** — production data always flows through `us30_loader.py` → Alpaca or CSV.

---

### 14.9 API Usage Summary

| API | Auth Method | Called From | Purpose |
|-----|------------|-------------|---------|
| **Anthropic Claude** | `ANTHROPIC_API_KEY` env | `llm_client.py` → agents | Strategy research, code generation |
| **Google Gemini** | `GEMINI_API_KEY` env | `llm_client.py` → agents | Fallback LLM when Claude unavailable |
| **Alpaca Trading** | `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` | `alpaca_connector.py`, `alpaca_service.py` | Order execution, account data, positions |
| **Alpaca Data (REST)** | Same keys | `alpaca_connector.py` → `get_ohlcv()` | Historical bars with 60s cache |
| **Alpaca Data (WS)** | Same keys | `market_stream.py` → `start_stream()` | Real-time bar/quote streaming |
| **MetaTrader 5** | MT5 terminal login | `mt5_connector.py` | CFD/FX execution (Windows only) |
| **Neon (PostgreSQL)** | `DATABASE_URL` | `db_handler.py` | Institutional memory, audit log |
| **FastAPI (internal)** | None (localhost) | Dashboard pages via `requests` | Broker data relay + mock fallback |
| **MCP stdio** | None (process stdio) | Claude Desktop / IDE | LLM tool-calling for broker actions |
| **yfinance** | None (public) | Colab notebooks only | Index/FX research data |

---

### 14.10 Auth & Key Management

- **Never commit `.env`** — use `.env.example` as the template.
- All API keys are read from environment variables at runtime via `os.environ.get(...)`.
- Connectors are **lazy-initialised** — they only connect when first called, so the system boots cleanly even when keys are absent (falls back to mock).
- Paper trading is the **default** for Alpaca (`ALPACA_PAPER=true`). To go live, set `ALPACA_PAPER=false` and confirm HITL approval flow is active.
- Backup Alpaca credentials (`ALPACA_API_KEY_2`, `ALPACA_SECRET_KEY_2`) are optional and only needed for multi-account failover in high-frequency scenarios.
