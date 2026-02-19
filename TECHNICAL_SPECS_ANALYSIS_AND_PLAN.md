# Technical Specs (Technical_specs_gemini.md) — Analysis & Plan

**Purpose:** Determine which specs are **already ensured** in the project, which must be **ensured before or alongside** trading/research algorithms, and which are **included only after** implementing those algorithms.  
**Reference:** `Technical_specs_gemini.md` (same content as `specs.md`).

---

## 1. Summary

| Category | Status | When to ensure |
|----------|--------|----------------|
| **§1 System Vision & §2 Infrastructure (structural)** | Partially ensured | Complete in Phase 1 (vault, db_handler, deps); rest with algorithms |
| **§3 Core Agentic Workflow (agents)** | Not ensured | **After** / during implementation of trading & research algorithms |
| **§4 Database Schema** | Ensured (tables) | pgvector when building Librarian knowledge base |
| **§5 Development Milestones** | Phase 1 partial; Phase 2/3 not started | Phase 1 first, then Phase 2/3 with algorithms |
| **§6 Security & HITL** | Structure only | Enforce in code when execution/trading exists |

**Short answer:**  
- **Already ensured:** Schema (tables), BaseWatcher + watchers, partial vault; asyncpg in deps.  
- **Ensure before algorithms:** Full vault structure, `db_handler.py`, HITL folders, modular agent boundaries.  
- **Include after implementation of trading and research algorithms:** All agent logic (Librarian, Strategist, Monte Carlo, Regime Analyst, Risk Architect), Monte Carlo tool, US30 loader, Ralph Wiggum loop, Killer Agent, Monday Morning Briefing, RL/behavioral patches, pgvector knowledge base, GCP/Docker.

---

## 2. Spec-by-spec analysis

### 2.1 §1 System Vision & Objective

| Spec | In project? | Notes |
|------|-------------|--------|
| Multi-agent Digital Employee as Senior Quant Researcher | **Planned only** | No agents implemented yet. |
| Transform raw info → validated, risk-managed alphas for US30 etc. | **Planned only** | End-to-end flow depends on all agents. |
| **Modular 10-year lifecycle** (replace LLMs/models without breaking workflow) | **Not yet ensured** | Ensure by: clear agent interfaces, config-driven model endpoints, no hardcoded LLM in core workflow. Should be **designed before** embedding algorithms. |

**Verdict:** Vision is **not** ensured; it is satisfied **when** we implement the workflow. **Modularity** should be **ensured before** deep algorithm work (interfaces + config).

---

### 2.2 §2 Infrastructure & Tech Stack

| Spec | In project? | Notes |
|------|-------------|--------|
| Reasoning Engine: Claude Code / Agentic Workflows | **Assumed** | No code dependency; operational choice. |
| Memory (Dashboard/GUI): Obsidian Vault, local-first | **Partial** | Vault exists; full folder structure (Needs_Action, Plans, Done, etc.) **not** created. Ensure in Phase 1. |
| Long-term Memory: Neon DB (PostgreSQL + pgvector) | **Partial** | `database/schema.sql` has tables; **pgvector** not in schema yet. Add when implementing Librarian’s “Market Theory Knowledge Base”. |
| Compute: GCP (Cloud Run/Functions for 24/7 watchers) | **Not in project** | Include **after** algorithms + watchers are stable; deployment step. |
| Environment: Docker on WSL2 | **Not in project** | Include with or after GCP; no Dockerfile in repo yet. |
| Python libs: Pandas, Numpy, Stable-Baselines3, Scikit-Learn, Asyncpg | **Partial** | `requirements.txt` has **asyncpg** only. Add Pandas, Numpy when building data loaders/backtests; SB3/sklearn when building Risk Architect / regime logic. |

**Verdict:**  
- **Ensure now (Phase 1):** Vault folder structure, Neon connection via `db_handler.py`, asyncpg.  
- **Include with algorithms:** Pandas, Numpy (data/backtest); SB3, Scikit-Learn (RL/regime); pgvector (knowledge base).  
- **Include after algorithms:** GCP, Docker.

---

### 2.3 §3 Core Agentic Workflow (The Factory Line)

These specs **are** the trading and research algorithms. They are **not** ensured in code today; they are **included when we implement** each agent.

| Agent / spec | In project? | When to include |
|--------------|-------------|------------------|
| **A. Librarian** — Watcher on Needs_Action; LLM extract hypothesis; compare to Market Theory KB in Neon; output `RESEARCH_PLAN.md` to `/Plans` | **No** | **After** vault + db_handler + (optional) pgvector KB. Implement as first “research” algorithm. |
| **B. Strategist** — Research plan → Python code; entry/exit + ideal regime; output to `src/models/drafts/` | **No** | **After** Librarian and folder structure. Implement with “trading” codegen. |
| **C. Monte Carlo Engine** — 10k+ iterations; shuffle OHLCV to stress-test edge | **No** | **After** US30 data loader and draft strategies. Implement as core “research” algorithm. |
| **D. Regime Analyst** — 1m/5m/1h/1D; High Vol (2020), Bear (2022), Trending; GER40, NAS100 for drift | **No** | **After** Monte Carlo and multi-timeframe data. Implement with regime/backtest logic. |
| **E. Risk Architect** — PPO/DQN for sizing (Kelly), SL/TP; guardrails for Disposition Effect, FOMO | **No** | **After** validated strategies exist. Implement with “trading” execution/sizing algorithms. |

**Verdict:** Entire §3 is **included only after (or during) implementation of trading and research algorithms**. No part of §3 is “ensured” in the repo today.

---

### 2.4 §4 Database Schema (Neon DB)

| Spec | In project? | Notes |
|------|-------------|--------|
| `alphas` — validated strategy parameters, Sharpe | **Yes** | `database/schema.sql` has `alphas` with params, entry/exit logic, regime, sharpe_ratio, etc. |
| `strategy_graveyard` — failed hypotheses, reason for failure | **Yes** | Present in `schema.sql`. |
| `market_regimes` — US30 historical periods for cross-regime testing | **Yes** | Present in `schema.sql`. |
| Optional: Market Theory Knowledge Base (EMH, Mean Reversion, etc.) | **No** | Could be new table(s) or pgvector embeddings; add **when** implementing Librarian. |

**Verdict:** Core schema from Technical_specs_gemini.md **is** ensured. Add **pgvector** and any “knowledge base” tables **when** implementing the Librarian and its fundamental filter.

---

### 2.5 §5 Development Milestones

| Milestone | In project? | When to include |
|-----------|-------------|------------------|
| **Phase 1.1** — Initialize Obsidian Vault folder structure | **No** | **Before** algorithms. Do in Phase 1. |
| **Phase 1.2** — `db_handler.py` to connect to Neon | **No** | **Before** algorithms. Do in Phase 1. |
| **Phase 1.3** — BaseWatcher to detect new files in `/Needs_Action` | **Yes** (design: watchers create files in Needs_Action) | No change needed for Phase 1. |
| **Phase 2.1** — Monte Carlo tool as Python skill for Claude | **No** | **With** trading/research algorithms (Phase 2). |
| **Phase 2.2** — US30 Data Loader (CSV/dataset) | **No** | **With** algorithms (Phase 2). |
| **Phase 2.3** — Ralph Wiggum Loop: Plan → Monte Carlo → Done | **No** | **After** Plan + Monte Carlo exist (Phase 2). |
| **Phase 3.1** — “Killer Agent” (synthetic slippage/noise in backtests) | **No** | **After** backtest pipeline exists (Phase 3). |
| **Phase 3.2** — Monday Morning CEO Briefing in Obsidian | **No** | **After** we have results to report (Phase 3). |

**Verdict:** Phase 1 is partially done (BaseWatcher); rest of Phase 1 (vault, db_handler) **ensure before** algorithms. Phase 2 and 3 **are** the implementation of trading and research algorithms — include them **during/after** that work.

---

### 2.6 §6 Security & Human-in-the-Loop (HITL)

| Spec | In project? | Notes |
|------|-------------|--------|
| No trade “Live” without manual file move to `/Approved` | **Structure only** | Folders not created yet. **Enforce in code** when we add execution/trading (e.g. only read “approved” proposals). |
| Docker isolation: limit filesystem to Vault + `src` | **Not in project** | Add with Docker/deployment **after** algorithms. |

**Verdict:** HITL **semantics** (Approved/Pending_Approval/Rejected) should be **ensured** when creating vault structure (Phase 1); **enforcement** (no live trade without Approved) is **included when** implementing trading/execution logic.

---

## 3. What is already ensured vs what comes after algorithms

### 3.1 Already ensured in the project

- **Database schema:** `alphas`, `strategy_graveyard`, `market_regimes`, `agent_audit_logs` in `database/schema.sql`.
- **BaseWatcher:** Abstract base + `ResearchWatcher` + data-ingestion watcher; create action files in `Needs_Action` from external inputs.
- **Obsidian vault:** Exists with `.obsidian` and `Welcome.md`.
- **Dependencies:** `asyncpg` in `requirements.txt`.

### 3.2 Ensure before / alongside implementing algorithms

- **Full Obsidian Vault folder structure** (Needs_Action, Plans, Done, Logs, Pending_Approval, Approved, Rejected, Research_Data, Alphas, etc.) — so agents and HITL have defined places.
- **`db_handler.py`** — Neon connect and basic read/write for existing tables.
- **Modular agent boundaries** — so “10-year lifecycle” and swapping LLMs/models don’t break the workflow.
- **HITL folder semantics** — Pending_Approval / Approved / Rejected present and used in design; enforcement in code when execution exists.

### 3.3 Include after (or during) implementation of trading and research algorithms

- **§3 entire workflow:** Librarian, Strategist, Monte Carlo Engine, Regime Analyst, Risk Architect (all logic and I/O).
- **Phase 2:** Monte Carlo tool, US30 Data Loader, Ralph Wiggum Loop.
- **Phase 3:** Killer Agent, Monday Morning CEO Briefing.
- **Tech stack:** Pandas, Numpy (data/backtest); Stable-Baselines3, Scikit-Learn (RL/regime); pgvector + knowledge base for Librarian.
- **Security enforcement:** “No live trade without move to Approved” in execution path.
- **Infrastructure:** GCP (Cloud Run/Functions), Docker, WSL2.

---

## 4. Recommended plan (order of work)

### Phase 1 — Ensure structural specs (before algorithms)

1. Create **full vault folder structure** per `IMPLEMENTATION_PLAN.md` (§4.1).
2. Implement **`db_handler.py`** (Neon + asyncpg) and use existing schema.
3. Add **`src/watchers/__init__.py`** and fix data-ingestion watcher name/frontmatter.
4. (Optional) Add **`.env.example`** and document `VAULT_PATH`, `DATABASE_URL`.
5. Define **agent interfaces** (e.g. “Librarian: input path → output path”; “Strategist: plan path → draft script path”) so modularity is ensured before coding agent internals.

### Phase 2 — Implement research & validation algorithms (include §3.C, §3.D, Phase 2 milestones)

1. **US30 Data Loader** — load CSV/dataset (Pandas); add to `requirements.txt`.
2. **Monte Carlo tool** — 10k+ iterations, OHLCV shuffle; callable from Claude or orchestration.
3. **Librarian** — ingest from Needs_Action, extract hypothesis, compare to KB (add pgvector/knowledge base if needed), write `RESEARCH_PLAN.md` to `/Plans`.
4. **Strategist** — read plan from `/Plans`, emit Python draft to `src/models/drafts/`.
5. **Ralph Wiggum Loop** — orchestrate Plan → Monte Carlo → Done (and optionally Librarian → Strategist before that).
6. **Regime Analyst** — multi-timeframe and regime tests (1m/5m/1h/1D; 2020/2022/trending; correlated assets); can follow Monte Carlo.

### Phase 3 — Execution, moat, reporting (include §3.E, Phase 3, §6 enforcement)

1. **Risk Architect** — RL (PPO/DQN) for sizing (Kelly), SL/TP; behavioral guardrails (Disposition Effect, FOMO).
2. **Killer Agent** — inject slippage and noise into every backtest.
3. **Monday Morning CEO Briefing** — generator writing to Obsidian (e.g. `/Reports` or designated folder).
4. **HITL enforcement** — execution path checks for file in `/Approved` before any “live” trade.
5. **Docker + GCP** — containerize watchers and agents; deploy to Cloud Run/Functions as needed.

---

## 5. One-page checklist

| Technical spec (from Technical_specs_gemini.md) | Ensured now? | When to include |
|------------------------------------------------|--------------|------------------|
| 10-year modular lifecycle | No | Design interfaces in Phase 1; keep agent boundaries in Phase 2/3 |
| Obsidian Vault (local-first memory) | Partial (no full folders) | Phase 1: create folders |
| Neon DB (schema) | Yes | — |
| Neon DB (pgvector / knowledge base) | No | With Librarian (Phase 2) |
| db_handler.py | No | Phase 1 |
| BaseWatcher + watchers | Yes | — |
| Librarian agent | No | Phase 2 (research algorithms) |
| Strategist agent | No | Phase 2 (trading codegen) |
| Monte Carlo Engine | No | Phase 2 (research algorithms) |
| Regime Analyst | No | Phase 2 (research algorithms) |
| Risk Architect | No | Phase 3 (trading/execution algorithms) |
| Monte Carlo tool + US30 loader + Ralph Wiggum | No | Phase 2 |
| Killer Agent + Monday Briefing | No | Phase 3 |
| HITL (no live without Approved) | Structure only | Phase 3: enforce in code |
| GCP / Docker | No | After algorithms (deployment) |
| Pandas, Numpy, SB3, Scikit-Learn | No (only asyncpg) | Phase 2/3 as needed |

---

*This document answers: “Are Technical_specs_gemini.md ensured in the project or included after implementation of trading and research algorithms?” — with a concrete breakdown and a phased plan.*
