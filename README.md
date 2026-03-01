# Trader-Suit (Alpha Research & Execution Factory)

A modular alpha-research and execution system where AI agents act as Digital FTEs: from raw research to Monte Carlo–validated strategies, risk sizing, and human-in-the-loop execution. Built for a 10-year horizon with **OpenClaw** (brain) and **Nano Claw** (muscle) layers.

---

## Architecture Overview

| Layer | Role | Components |
|-------|------|------------|
| **OpenClaw (Brain)** | Reasoning, strategy generation, HITL, reporting | Agents (Librarian, Strategist, Killer, Risk Architect, Reporter), skills, institutional memory (Neon) |
| **Nano Claw (Muscle)** | Sensing, execution, persistence | Watchers, connectors (Alpaca, MT5), execution manager, PM2 |

- **Control plane**: Orchestrator runs one cycle (Librarian → Strategist → Killer → Risk Architect). Optional REST/scheduler; no full WebSocket protocol.
- **Execution**: Python-only (Zero-MQL); live/high-leverage requires manual approval (file in `Approved/`).
- **References**: `ARCHITECTURE_ADJUSTMENT_PLAN.md`, `Paradigms.md`, `AGENTS.md`, `OpenClaw_architect.md`.

---

## Flow: The Ralph Wiggum Loop

```
Needs_Action/  →  Librarian  →  Plans/ (RESEARCH_PLAN_*.md)
                                    ↓
Plans/         →  Strategist  →  src/models/drafts/*.py
                                    ↓
drafts/        →  Killer      →  Monte Carlo Pro  →  production/ or graveyard (+ journal)
                                    ↓
                        Risk Architect  →  sizing, circuit breakers, cooldowns
                                    ↓
Approved/      →  Execution Manager   →  throttled orders (Alpaca / MT5)
                                    ↓
                        Reporter  →  Monday briefings (Gmail, Telegram), graveyard summaries
```

1. **Librarian**: Reads `Needs_Action/`, produces structured `RESEARCH_PLAN_*.md` in `Plans/`. Extracts alpha hypotheses; tags by regime; checks redundancy via institutional memory.
2. **Strategist**: Reads `Plans/`, writes strategy code to `src/models/drafts/`. Follows `BaseStrategy`; embeds regime filters and market-param hooks.
3. **Killer**: Validates drafts via **Monte Carlo Pro** (10k+ iterations, noise/slippage, walk-forward). Pass → `src/models/production/`; fail → graveyard with **journaled post-mortem** (failure mode, metrics, mitigation).
4. **Risk Architect**: Fractional Kelly, guardrails, circuit breakers. Cooldown after N consecutive losses.
5. **Execution Manager**: Throttled execution; HITL for live (file move Plans → Approved).
6. **Reporter**: Monday briefings; graveyard summaries; Telegram/Gmail; `/failure_report` for graveyard journals.

All agents log to `Logs/` where applicable. High-leverage or live trades require manual approval (file in `Approved/`).

---

## Directory Structure

```
/
├── .env
├── ecosystem.config.js          # PM2 (watchers, connectors)
├── AGENTS.md                    # Bootstrap: operating instructions (injected at cycle start)
├── SOUL.md, TOOLS.md, IDENTITY.md, USER.md
├── ARCHITECTURE_ADJUSTMENT_PLAN.md
├── Paradigms.md
├── AI_Employee_Vault/          # Default vault (or Obsidian_Vault/)
│   ├── Needs_Action/            # Perception queue (Watchers → Librarian)
│   ├── Plans/                  # RESEARCH_PLAN_*.md (Librarian → Strategist)
│   ├── Approved/               # HITL execution queue
│   ├── Reports/                # CEO briefings, compliance
│   └── Logs/
├── src/
│   ├── agents/                 # OpenClaw
│   │   ├── base_agent.py
│   │   ├── librarian_agent.py
│   │   ├── strategist_agent.py
│   │   ├── killer_agent.py
│   │   ├── risk_architect.py
│   │   ├── reporter.py
│   │   └── teams/              # perception_team, validation_team
│   ├── connectors/             # Nano Claw: Alpaca, MT5, market_stream, execution_manager
│   ├── edges/                  # Edge workflows (volume, pattern, statistical, etc.) + registry
│   ├── models/
│   │   ├── base_strategy.py
│   │   ├── drafts/
│   │   └── production/
│   ├── tools/                  # Monte Carlo Pro, db_handlers, vault_watcher, failure_journal
│   ├── skills/                 # Per-agent SKILL.md + loader (three-tier: workspace > managed > bundled)
│   ├── memory/                 # bootstrap_loader, session_store, state_sync (60s → Neon)
│   ├── gateway/                # approval.py (strategy + execution gates)
│   ├── orchestration/          # orchestrator.py
│   ├── watchers/               # vault / research watchers
│   ├── backtest/, execution/, api/, ml/, data/, db/, prompt/, mcp/
│   └── dashboard/
├── skills/                     # Workspace skills (top priority)
└── tests/
```

---

## Progress (vs ARCHITECTURE_ADJUSTMENT_PLAN)

### Implemented

- **Orchestrator**: One cycle (Librarian → Strategist → Killer → Risk Architect) with optional bootstrap + per-agent skills (`use_bootstrap_and_skills=True`).
- **Bootstrap**: `AGENTS.md`, `SOUL.md`, `TOOLS.md`, etc.; `src/memory/bootstrap_loader.py` loads at cycle start.
- **Skills**: Three-tier loader `src/skills/loader.py`; per-agent `src/skills/{librarian,strategist,killer,risk_architect,watchers,...}/SKILL.md`.
- **Agents**: Librarian (Needs_Action → Plans), Strategist (Plans → drafts), Killer (Monte Carlo, production/graveyard), Risk Architect, Reporter; base agent with perceive/reason/act.
- **Tools**: `monte_carlo_pro.py` (MCP), `db_handlers.py`, `vault_watcher.py` (monitor_vault), `failure_journal.py` (graveyard journaling).
- **Connectors**: Alpaca, MT5 Zero-MQL, `market_stream.py`, `execution_manager.py`.
- **Gateway**: `src/gateway/approval.py` (file-based HITL: Approved/, production move).
- **Memory**: `session_store.py`, `state_sync.py` (60s flush to Neon).
- **Agent teams**: `perception_team.py`, `validation_team.py`.
- **Edges**: Volume, pattern, statistical, sentiment, factor mining, etc.; edge registry and workflows.

### In progress / planned (see ARCHITECTURE_ADJUSTMENT_PLAN phases 2–4)

- **Paradigms Task 1**: Full failure journal schema in Neon (`failure_mode`, `alpha_decay_reason`, `metrics_json`); FailureAnalyzer subagent; Reporter graveyard summaries and Telegram `/failure_report`.
- **Paradigms Task 2**: Market-element parametrization in Killer/Risk/Execution (order types, market maker sims, infrastructure); `market_infrastructure_sims.py`; backtest param sweeps.
- **Paradigms Task 3**: Pin all skill implementations (e.g. `extract_hypothesis.py`, `generate_strategy_code.py`) under `src/skills/<agent>/`; wire subagents and teams into orchestration.
- **Watchers**: PM2 ecosystem; stream_market_data integration.
- **Tests**: Skill loader, bootstrap loader, approval gate, failure journal schema, full-cycle smoke.

---

## Running

- **Trader-Suit UI** (Streamlit, 8-page dashboard):
  ```bash
  streamlit run src/dashboard/app.py
  ```
  From project root. Requires Streamlit 1.30+ (for `st.switch_page`). Optional: start the FastAPI backend for live metrics/signals/activity:
  ```bash
  uvicorn src.api.main:app --reload
  ```
  Set `TRADER_API_URL` if the API runs elsewhere. See `UI_Requirements.md`, `UI_Implementation_Gap.md`, and `docs/UI_Design_Best_Practices.md`.

  **Alpaca (live data):** When the API runs with Alpaca credentials, the Dashboard and Execution & Reports pages use live account, positions, P&L curve, and ticker. Set in env (or `.env`):
  - `ALPACA_API_KEY` — Alpaca API key
  - `ALPACA_SECRET_KEY` — Alpaca secret key
  - `ALPACA_PAPER` — `true` (default) for paper trading, `false` for live
  - `ALPACA_TICKER_SYMBOL` — Symbol for live ticker (default `SPY`; US equities only)

- **One orchestration cycle** (from project root, e.g. on Colab over SSH):
  ```bash
  python -m src.orchestration.orchestrator
  ```
  Environment: `VAULT_PATH` (default `AI_Employee_Vault`), `US30_CSV_PATH` (optional, for Killer backtest).
- **With bootstrap + skills** (optional): Set `use_bootstrap_and_skills=True` in `run_one_cycle()`.
- **Heavy compute** (training, backtests, Monte Carlo): Run on the **remote Colab** terminal, not locally (see `.cursor/rules/colab-remote.mdc`). Save checkpoints/logs under Drive paths for persistence.

---

## Conventions

- **Zero-MQL**: All execution logic in Python; no logic in MT5 terminal.
- **HITL**: Strategy approval = Killer → production or graveyard. Execution approval = file in `Approved/` for live/high-leverage.
- **Logs**: Agents log to vault `Logs/` where applicable; state synced to Neon every 60s.
- **Skills**: One `SKILL.md` per agent under `src/skills/<agent>/`; loader injects into agent context at cycle start.

For phased implementation details and per-agent checklists, see **ARCHITECTURE_ADJUSTMENT_PLAN.md**. For Paradigms (failure journaling, market elements, skills/MCP/subagents/teams), see **Paradigms.md**.
