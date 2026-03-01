# Architecture Adjustment Plan: OpenClaw Reference → Alpha Research & Execution Factory

**Purpose**: Align this project’s architecture with the OpenClaw reference (`02-architecture-analysis.md`), using `OpenClaw_architect.md` as the implementation plan, `Agent_skill.md` as the agent skills specification, and `Paradigms.md` for enhanced failure journaling, market-simulation parametrization, and skills/MCP/subagents/teams placement.

**References**:
- Architectural reference: `agentfactory-main/agentfactory-main/specs/openclaw/research/02-architecture-analysis.md`
- Implementation plan: `OpenClaw_architect.md`
- Agent skills: `Agent_skill.md`
- Paradigms (enhanced spec): `Paradigms.md` — Task 1: failure journaling & alpha decay; Task 2: market elements in validation/execution; Task 3:where Agent skills, MCP, subagents, agent teams has to be used and where they are currently used , we have to revisit design to make it robust.

---

## 1. Executive Summary

| Aspect | OpenClaw Reference | Our Adaptation (Alpha Factory) |
|--------|--------------------|---------------------------------|
| **Control plane** | WebSocket gateway (protocol, auth, sessions) | **Simplified**: Orchestrator + optional lightweight API/scheduler; no full WebSocket protocol |
| **Layers** | Client → Gateway → Agents/Nodes/Channels → Skills → Models | **OpenClaw (Brain)** = agents + skills + Neon; **Nano Claw (Muscle)** = watchers + connectors + PM2 |
| **Directory layout** | Domain-driven (`agents/`, `gateway/`, per-channel) | **Keep** domain-driven: `src/agents/`, `src/connectors/`, `src/edges/`, `src/models/`, `src/tools/`, add `src/skills/`, `src/memory/` |
| **Bootstrap files** | AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md | **Adopt**: workspace-level bootstrap for persona, tools, identity |
| **Skills** | Three-tier (workspace > managed > bundled) | **Adopt**: `./skills/` > `~/.alpha-factory/skills/` > bundled; one SKILL.md per agent under `src/skills/<agent>/` |
| **Session/state** | JSONL transcript + session index | **Adopt**: Neon DB for “institutional memory” + optional JSONL transcript for agent thoughts; 60s state persistence |
| **Approval (HITL)** | Execution approval manager, operator scope | **Adopt**: File-based HITL (Plans → Approved), strategy approval gate (Killer → production), circuit breakers |
| **Skill loading** | Priority order, discovery | **New**: Skill loader that reads `src/skills/<agent>/SKILL.md` and injects into agent context |

---

## 1b. Paradigms.md: Three Enhancement Tasks

| Task | Description | Where it lands |
|------|-------------|----------------|
| **Task 1 – Failure journaling** | Detailed failure analysis and alpha decay reasoning in the strategy graveyard, as professional journal entries. Categorize failure modes (e.g. overfitting, regime shifts, alpha decay/crowding) with metrics, descriptions, mitigations. | Killer → graveyard schema + **FailureAnalyzer** subagent; Neon `strategy_graveyard` with journal fields; Reporter/Telegram graveyard summaries and `/failure_report`. |
| **Task 2 – Market elements** | Parametrize validation (Killer) and execution (Risk/Execution Manager): market types (order-driven vs quote-driven), market maker (bid-ask, delta-neutral), order types (market, limit, stop, stop-limit), infrastructure (latency, clearing). Backtests vary params to test robustness. | Killer: Monte Carlo/backtest param sweeps; Risk & Execution: configurable order types and market sims; connectors: optional market-infrastructure sims. |
| **Task 3 – Implementation locations** | Pin down where skills (Python + .md), MCP, subagents, and agent teams live. | Skills: `src/skills/[agent]/` (.md + e.g. `extract_hypothesis.py`); MCP: `src/tools/monte_carlo_pro.py`; subagents: isolated classes (e.g. `FailureAnalyzer` in Killer); teams: `src/agents/teams/` (e.g. ValidationTeam, perception_team). |

---

## 2. Pattern Mapping: OpenClaw → Alpha Factory

### 2.1 High-Value Patterns to Implement

| Pattern | OpenClaw | Our Implementation |
|---------|----------|--------------------|
| **Bootstrap files** | AGENTS.md, SOUL.md, TOOLS.md, etc. | Add `Obsidian_Vault/` (or workspace) root: `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`. Injected into agent context at session/cycle start. |
| **Three-tier skill loading** | workspace > ~/.openclaw/skills > bundled | `./skills/` (or `src/skills/`) > `~/.alpha-factory/skills/` > repo-bundled skills. Resolver in `src/skills/loader.py`. |
| **Transcript / state persistence** | JSONL per session | Neon DB: `agent_state`, `transcripts` (or JSONL in `~/.alpha-factory/agents/<id>/sessions/`). Persist “thoughts” and task state every 60s. |
| **Approval concept** | Human-in-the-loop for execution | (1) Strategy: Killer approves → move to `src/models/production/`; graveyard for failures. (2) Execution: file move from Plans to Approved; high-leverage/live requires manual approve. |

### 2.2 Patterns to Simplify (Not Copy Fully)

| Pattern | OpenClaw | Our Approach |
|---------|----------|--------------|
| **Control plane** | Full WebSocket, 50+ message types, pairing | **Orchestrator + cron/Cloud Run**: Keep `orchestrator.run_one_cycle()`; add optional REST or serverless trigger; no WebSocket protocol. |
| **Session scoping** | main / per-peer / per-channel-peer | **Single workspace + optional per-cycle session id**; session = “run” or “day” for transcript. |
| **Channel integrations** | 12+ messaging SDKs | **Telegram + Gmail only** (Reporter); no multi-channel gateway. |

### 2.3 Out of Scope (Reference Only)

- Native apps (macOS/iOS/Android), device pairing, TLS pinning.
- Full OpenClaw gateway protocol and auth handshake.

---

## 3. Target Directory Structure (Aligned)

```
/
├── .env
├── ecosystem.config.js          # PM2
├── AGENTS.md                     # Bootstrap: operating instructions (optional at root)
├── SOUL.md                       # Bootstrap: persona, boundaries, tone
├── TOOLS.md                      # Bootstrap: tool guidance
├── IDENTITY.md                   # Bootstrap: name, emoji
├── USER.md                       # Bootstrap: user profile (optional)
├── Obsidian_Vault/
│   ├── Needs_Action/             # Perception queue (Watchers → Librarian)
│   ├── Approved/                 # HITL execution queue
│   └── Reports/                  # CEO briefings (regime-tagged metrics, failure journals – Paradigms)
├── src/
│   ├── agents/                   # OpenClaw layer (Brain); agent teams here (Paradigms Task 3)
│   │   ├── base_agent.py
│   │   ├── librarian_agent.py
│   │   ├── strategist_agent.py
│   │   ├── killer_agent.py
│   │   ├── risk_architect.py
│   │   ├── reporter.py
│   │   ├── teams/                # NEW: Coordinated agent groups (Paradigms Task 3)
│   │   │   ├── perception_team.py   # Librarian + subagents
│   │   │   └── validation_team.py   # Killer + Risk subagents in loop
│   │   └── (future: rl_hunter, execution_manager as first-class agents if needed)
│   ├── connectors/               # Nano Claw (Muscle); add market infrastructure sims (Task 2)
│   │   ├── base_connector.py
│   │   ├── alpaca_connector.py
│   │   ├── mt5_connector.py
│   │   ├── execution_manager.py
│   │   ├── market_stream.py      # NEW: stream_market_data skill
│   │   └── market_infrastructure_sims.py  # NEW (Task 2): latency, clearing, order-driven/quote-driven
│   ├── edges/                    # Edge workflows + registry
│   │   ├── edge_registry.py
│   │   ├── base_workflow.py
│   │   └── ...
│   ├── models/
│   │   ├── base_strategy.py
│   │   ├── drafts/
│   │   └── production/
│   ├── tools/                    # Shared tools (Monte Carlo = MCP, DB, vault watcher, failure journaling)
│   │   ├── monte_carlo_pro.py    # MCP – Monte Carlo Pro (Task 3)
│   │   ├── db_handlers.py        # check_redundancy, Neon/pgvector; graveyard + journal writes
│   │   ├── vault_watcher.py      # NEW: monitor_vault skill
│   │   ├── failure_journal.py    # NEW (Task 1): structured journal entry creation for graveyard
│   │   └── ...
│   ├── skills/                   # NEW: Three-tier; .md + Python per Agent_skill (Task 3)
│   │   ├── loader.py             # Resolve workspace > managed > bundled; inject into agents
│   │   ├── watchers/
│   │   │   └── SKILL.md          # monitor_vault, stream_market_data
│   │   ├── librarian/
│   │   │   ├── SKILL.md
│   │   │   └── extract_hypothesis.py   # Optional: .md-defined Python (Task 3)
│   │   ├── strategist/
│   │   │   ├── SKILL.md
│   │   │   └── generate_strategy_code.py
│   │   ├── killer/
│   │   │   ├── SKILL.md
│   │   │   └── run_monte_carlo.py      # Or call src/tools/monte_carlo_pro.py (MCP)
│   │   ├── risk_architect/
│   │   │   └── SKILL.md
│   │   ├── execution_manager/
│   │   │   └── SKILL.md
│   │   └── reporter/
│   │       └── SKILL.md
│   ├── memory/                   # NEW: Session/transcript and state persistence
│   │   ├── session_store.py      # JSONL or Neon-backed transcript
│   │   └── state_sync.py         # 60s state flush to Neon
│   ├── gateway/                  # OPTIONAL: minimal control plane (scheduler, approval hooks)
│   │   └── approval.py           # Approval gate for strategies + execution (lightweight)
│   ├── watchers/
│   ├── orchestration/
│   ├── db/
│   ├── backtest/
│   ├── execution/
│   ├── api/
│   └── ...
├── skills/                       # Workspace skills (top priority tier)
│   └── (user-defined overrides)
└── tests/
```

---

## 4. Bootstrap Files (OpenClaw Pattern)

- **Location**: Project root or `Obsidian_Vault/` root.
- **When**: Loaded at start of orchestration cycle or session; injected into agent context (e.g. Librarian, Strategist) as “system” context.
- **Contents** (templates to add):
  - **AGENTS.md**: Operating instructions (who does what in the loop).
  - **SOUL.md**: Persona, boundaries, tone (e.g. “conservative risk steward”, “no overgeneralization”).
  - **TOOLS.md**: Tool guidance (when to use which tool, safety).
  - **IDENTITY.md**: Name and emoji for the factory.
  - **USER.md**: User profile (optional).

**Implementation**: Add `src/memory/bootstrap_loader.py` that reads these files and returns a single string or dict for the orchestrator to pass into each agent’s context.

---

## 5. Skill System (Three-Tier + Agent_skill.md)

### 5.1 Resolution Order

1. **Workspace**: `./skills/` or `Obsidian_Vault/skills/` (user overrides).
2. **Managed**: `~/.alpha-factory/skills/` (installed/user skills).
3. **Bundled**: `src/skills/<agent>/SKILL.md` (shipped with repo).

### 5.2 Skill File Format (from Agent_skill.md)

Each `SKILL.md` contains:
- **YAML frontmatter**: `name`, `description`.
- **Persona**, **Key Questions**, **Principles**, **Implementation Notes**.

### 5.3 Mapping: Agent → Skills → Code

| Agent | Skills (from Agent_skill.md) | Implementation Location |
|-------|------------------------------|--------------------------|
| **Watchers** | monitor_vault, stream_market_data | `src/tools/vault_watcher.py`, `src/connectors/market_stream.py` |
| **Librarian** | extract_hypothesis, check_redundancy | `src/agents/librarian/extract.py` (or inline), `src/tools/db_handlers.py` |
| **Strategist** | generate_strategy_code | `src/agents/strategist/draft.py` (or equivalent) |
| **Killer** | run_monte_carlo | `src/tools/monte_carlo_pro.py` (existing) |
| **Risk Architect** | apply_kelly_sizing | `src/agents/risk_architect/sizing.py` |
| **Execution Manager** | execute_order | `src/connectors/execution_manager.py` (or execution.py) |
| **Reporter** | generate_briefing | `src/agents/reporter/brief.py` (or reporter.py) |

### 5.4 Skill Loader Contract

- **Input**: Agent name (e.g. `librarian`), optional workspace path.
- **Output**: Merged skill context (from highest-priority tier that has a SKILL.md for that agent).
- **Use**: Orchestrator or each agent loads skill text and adds it to the LLM/system context so the agent “adopts” the persona and principles.

### 5.5 Paradigms Task 3: Skills, MCP, Subagents, Teams

- **Skills**: Implement as .md-defined **Python functions** in `src/skills/[agent]/` (e.g. `extract_hypothesis.py`, `generate_strategy_code.py`); SKILL.md describes persona/principles; .py is callable by the agent.
- **MCP**: Monte Carlo Pro lives in `src/tools/monte_carlo_pro.py`; Killer (and optionally others) invoke it for validation.
- **Subagents**: Isolated classes (e.g. `FailureAnalyzer` in Killer) for specialized work; can live under `src/agents/<parent>/` or `src/agents/subagents/`.
- **Agent teams**: Coordinated groups in `src/agents/teams/` (e.g. `perception_team.py` = Librarian + subagents; `validation_team.py` = Killer + Risk in loop).

---

## 6. Session & State Persistence (OpenClaw-Inspired + Paradigms)

- **Neon DB** (existing): Primary for “institutional memory” (alphas, strategy_graveyard, regime tags, e-ratio, templates). **Paradigms Task 1**: Extend `strategy_graveyard` with journal fields: `failure_mode`, `alpha_decay_reason`, `metrics_json`, and structured journal entries (Date, Strategy ID, Failure Mode, Metrics pre/post, Description, Limitations, Mitigation).
- **State every 60s**: Current task, agent “thoughts”, regime tags, iteration history, **and failure journal entries** (Paradigms) → Neon table `agent_state` (or equivalent).
- **Transcript (optional)**: JSONL under `~/.alpha-factory/agents/<agent_id>/sessions/<session_id>.jsonl` for audit/debug; or store transcript rows in Neon.

**New modules**:
- `src/memory/session_store.py`: Create/append transcript, list sessions.
- `src/memory/state_sync.py`: Periodic flush of agent state to Neon (e.g. from orchestrator or agent base class).
- `src/tools/failure_journal.py`: Build structured journal entries for graveyard (Task 1); used by Killer/FailureAnalyzer subagent.

---

## 7. HITL & Approval

- **Strategy approval**: Killer passes → strategy moves to `src/models/production/`; failure → **journaled post-mortem to graveyard** (Paradigms Task 1): structured entry with failure_mode (e.g. overfitting, alpha decay, regime shift), metrics (pre/post decay Sharpe), description, limitations, mitigation. Approval gate: e.g. >10% return, <12% max DD, e-ratio >1.5.
- **Execution approval**: High-leverage or live trades require file move from Plans to Approved; Execution Manager only executes when approved (or when in paper mode). **Task 2**: Execution supports parametrizable order types (market, limit, stop, stop-limit) and market/infrastructure sims.
- **Circuit breakers**: Risk Architect triggers cooldown after N consecutive losses; Reporter alerts via Telegram; **Paradigms**: alert on alpha decay detected; Telegram `/failure_report` to query graveyard journals.

**Optional**: `src/gateway/approval.py` to centralize “can this strategy/order run?” checks.

---

## 8. Ralph Wiggum Loop vs Orchestration

Keep the existing flow and align names:

- **Ingestion & Perception**: Watchers (monitor_vault, stream_market_data) → Librarian (extract_hypothesis, check_redundancy) → RESEARCH_PLAN.md in Plans (or Needs_Action → Plans).
- **Generation**: Strategist (generate_strategy_code) → `src/models/drafts/[Strategy_Name].py`.
- **Adversarial**: Killer (run_monte_carlo) → approve → production or graveyard.
- **RL/DL**: RL/DL Hunter (optional adaptive optimization) → custom gym, PPO; can be a separate agent or part of edges.
- **Risk & Execution**: Risk Architect (apply_kelly_sizing) + Execution Manager (execute_order) with HITL and throttling.

Orchestrator remains the “control plane”: it runs one cycle (Librarian → Strategist → Killer → Risk Architect) and can be extended to call Reporter (e.g. on schedule) and Execution Manager when signals are approved.

---

## 9. Per-Agent Implementation Checklist

Use this to adjust each agent so it follows the architecture and Agent_skill.md.

### 9.1 Watchers (Nano Claw)

- [ ] **Skill file**: `src/skills/watchers/SKILL.md` with `monitor_vault`, `stream_market_data` (from Agent_skill.md).
- [ ] **monitor_vault**: Implement or refactor in `src/tools/vault_watcher.py` (watchdog, PM2-friendly, log to Neon).
- [ ] **stream_market_data**: Implement in `src/connectors/market_stream.py` (e.g. Alpaca stream, persist to Neon/Parquet).
- [ ] Run under PM2 (ecosystem.config.js).

### 9.2 Librarian

- [ ] **Skill file**: `src/skills/librarian/SKILL.md` (extract_hypothesis, check_redundancy).
- [ ] **extract_hypothesis**: Implement in `src/agents/librarian/extract.py` or `src/skills/librarian/extract_hypothesis.py` (PDF/CSV/TXT → hypotheses with regime tags).
- [ ] **check_redundancy**: Implement in `src/tools/db_handlers.py` (pgvector/Neon, similarity threshold).
- [ ] **Context**: Bootstrap (SOUL, TOOLS) + skill text injected at cycle start.
- [ ] **Paradigms**: Output RESEARCH_PLAN.md with regime filters, e-ratio targets, and **potential market simulation params** (e.g. test with market maker spreads) for Killer/Risk.

### 9.3 Strategist

- [ ] **Skill file**: `src/skills/strategist/SKILL.md` (generate_strategy_code).
- [ ] **generate_strategy_code**: Implement in `src/agents/strategist/draft.py` or `src/skills/strategist/generate_strategy_code.py` (read RESEARCH_PLAN.md, BaseStrategy interface, regime filters).
- [ ] **Paradigms**: Include **hooks for market param variations** (e.g. order type simulations) so Killer/backtester can vary market elements.
- [ ] Output: `src/models/drafts/[Strategy_Name].py`.
- [ ] Use edge registry when generating (which edge type / workflow).

### 9.4 Killer Agent

- [ ] **Skill file**: `src/skills/killer/SKILL.md` (run_monte_carlo).
- [ ] **MCP**: `src/tools/monte_carlo_pro.py` (Monte Carlo Pro) — 10k+ iterations, noise/slippage, walk-forward; metrics Sharpe, DD, e-ratio.
- [ ] **Paradigms Task 2 – Market elements**: Parametrize backtests: order-driven vs quote-driven markets, market maker (bid-ask, delta-neutral), order types (market, limit, stop, stop-limit), infrastructure (latency, clearing). Vary params to test robustness (e.g. iceberg, dark pool, AMM-style).
- [ ] **Paradigms Task 1 – Failure journaling**: On fail → write to strategy_graveyard with **structured journal entry** (Date, Strategy ID, Failure Mode e.g. overfitting/alpha decay/regime shift, Metrics pre/post, Description, Limitations, Mitigation). Use **FailureAnalyzer subagent** (isolated class in Killer or `src/agents/killer/failure_analyzer.py`) to produce entries; persist via `src/tools/failure_journal.py` and Neon schema (`failure_mode`, `alpha_decay_reason`, `metrics_json`).
- [ ] **Approval gate**: On pass → move to `src/models/production/`; on fail → graveyard + journal.
- [ ] Tag by regime; require minimum trades (e.g. 50+).

### 9.5 Risk Architect

- [ ] **Skill file**: `src/skills/risk_architect/SKILL.md` (apply_kelly_sizing).
- [ ] **apply_kelly_sizing**: Implement in `src/agents/risk_architect/sizing.py` (fractional Kelly, vol target, risk tolerance).
- [ ] **Paradigms Task 2**: Embed **configurable order types** (market, limit, stop, stop-limit), **market maker sims** (bid-ask, volume-based), **market types** (order-driven LOB vs quote-driven), **infrastructure** (latency/jitter, clearing e.g. DTCC). Test params in backtests; ensure edges hold across scenarios (e.g. iceberg orders).
- [ ] Circuit breaker: cooldown after N consecutive losses; expose state for Reporter. Log failures to graveyard with journal entries when applicable.

### 9.6 Execution Manager

- [ ] **Skill file**: `src/skills/execution_manager/SKILL.md` (execute_order).
- [ ] **execute_order**: Refactor or ensure `src/connectors/execution_manager.py` throttles, tracks order-level data, respects HITL and circuit breakers.
- [ ] **Paradigms Task 2**: Support **configurable order types** (market, limit, stop, stop-limit) and optional **market/infrastructure sim** params for testing (latency, clearing). Bridge: Alpaca and/or MT5 Zero-MQL.

### 9.7 Reporter

- [ ] **Skill file**: `src/skills/reporter/SKILL.md` (generate_briefing).
- [ ] **generate_briefing**: Implement in `src/agents/reporter/brief.py`: audit Neon (P&L, Sharpe, graveyard, e-ratio per setup, regime breakdowns). **Paradigms Task 1**: Include **graveyard summaries with journaled failure insights** (e.g. “Overfitting detected in 3 strategies: in-sample Sharpe 2.5 → out-of-sample 0.8”); add **alpha decay trends** (e.g. crowding indicators).
- [ ] Delivery: Gmail API + Telegram; Monday 08:00 trigger (cron or Cloud Run).
- [ ] **Telegram**: Support `/failure_report` to query graveyard journals (Task 1). Alerts: circuit breaker, regime shift, **alpha decay detected**.

### 9.8 Agent Teams (Paradigms Task 3)

- [ ] **Perception team**: `src/agents/teams/perception_team.py` — coordinates Librarian + subagents for ingestion/perception.
- [ ] **Validation team**: `src/agents/teams/validation_team.py` — coordinates Killer + Risk subagents in a loop (e.g. validate → risk check → re-validate).
- [ ] **Subagents**: Isolated classes invoked by parent agents (e.g. `FailureAnalyzer` in Killer for journaling); can live under `src/agents/<parent>/` (e.g. `killer/failure_analyzer.py`) or shared in `src/agents/subagents/` if reused.

---

## 10. Phased Implementation Order

### Phase 1 – Foundation (no breaking changes)

1. Add **bootstrap files** (templates): AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md at repo root or Obsidian_Vault.
2. Implement **bootstrap_loader** in `src/memory/bootstrap_loader.py` and call it from the orchestrator before running agents.
3. Create **skill directory structure**: `src/skills/{watchers,librarian,strategist,killer,risk_architect,execution_manager,reporter}/SKILL.md` and populate from Agent_skill.md (copy/clip per agent).
4. Implement **skill loader** `src/skills/loader.py` (three-tier resolution, return text for agent name).

### Phase 2 – Skills and state

5. **Librarian**: Add extract_hypothesis and check_redundancy (db_handlers.py with pgvector); wire skill context; RESEARCH_PLAN to include optional market simulation params (Paradigms).
6. **Strategist**: Add or refactor generate_strategy_code; add hooks for market param variations (Paradigms Task 2); wire skill context.
7. **Killer**: Harden Monte Carlo (MCP) and approval gate; **Task 1**: FailureAnalyzer subagent + `failure_journal.py` + Neon graveyard schema (failure_mode, alpha_decay_reason, metrics_json); **Task 2**: parametrize backtests with market elements (order types, market maker, infrastructure); wire skill context.
8. **Risk Architect**: Add apply_kelly_sizing in sizing.py; **Task 2**: configurable order types and market/infra sim params; wire skill context.
9. **Reporter**: Add generate_briefing; **Task 1**: graveyard journal summaries, alpha decay reasons(volume , volatility, regime change , timeFrame , etc) and trends, Telegram `/failure_report`; wire skill context.
10. **State persistence**: Implement `src/memory/state_sync.py` (60s flush, include failure journal refs) and optional `session_store.py` (JSONL or Neon).

### Phase 3 – Nano Claw and execution

11. **Watchers**: Implement vault_watcher (monitor_vault) and market_stream (stream_market_data); add to PM2.
12. **Execution Manager**: Refactor execute_order for throttling, HITL, cooldowns; **Task 2**: order types and market/infra sim options; wire skill.
13. **Market infrastructure** (Task 2): Add `src/connectors/market_infrastructure_sims.py` (latency, clearing, order-driven/quote-driven) for use in Killer backtests and Risk/Execution tests.
14. **Approval**: Add lightweight `src/gateway/approval.py` if needed; ensure file-based HITL (Plans → Approved) is documented and used.

### Phase 4 – Polish and ops

15. **Agent teams** (Task 3): Implement `src/agents/teams/perception_team.py` and `validation_team.py`; wire into orchestration where useful.
16. **Orchestrator**: Inject bootstrap + skill context into each agent; optional session_id for transcript.
17. **Documentation**: Update README, OpenClaw_architect.md, and Paradigms.md to point to this plan and to bootstrap/skill/graveyard/market-param locations.
18. **Tests**: Unit tests for skill loader, bootstrap loader, approval gate, failure journal schema, market-param backtest (smoke), and one full cycle.

---

## 11. Summary Table

| Component | Action |
|-----------|--------|
| **Control plane** | Keep orchestrator; add optional REST/scheduler; no full WebSocket. |
| **Bootstrap files** | Add AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md; load at cycle start. |
| **Skills** | Three-tier loader; `src/skills/<agent>/SKILL.md` (+ optional .py per skill, Task 3); inject into agent context. |
| **Memory** | Neon for institutional memory; 60s state sync; optional JSONL transcript. **Paradigms**: graveyard journal fields (failure_mode, alpha_decay_reason, metrics_json). |
| **HITL** | Strategy: Killer → production/graveyard + **journaled post-mortem** (Task 1); Execution: Plans → Approved; circuit breakers; Telegram `/failure_report`. |
| **Agents** | Each agent gets SKILL.md and implementation locations as in Section 9; **subagents** (e.g. FailureAnalyzer); **teams** in `src/agents/teams/` (Task 3). |
| **Market elements** (Task 2) | Killer/Risk/Execution: parametrize order types, market types, market maker, infrastructure; backtests vary params; `market_infrastructure_sims.py`. |
| **MCP** | Monte Carlo Pro in `src/tools/monte_carlo_pro.py` (Task 3). |
| **Directory** | Add `src/skills/`, `src/memory/`, `src/agents/teams/`, optional `src/gateway/`; `failure_journal.py`, `market_infrastructure_sims.py`; keep existing domain layout. |

This plan aligns the Alpha Research & Execution Factory with the OpenClaw reference patterns (bootstrap, skills, session/state, approval), **Paradigms.md** (failure journaling, market-element parametrization, skills/MCP/subagents/teams locations), and Agent_skill.md as the single source of truth for agent behavior and file locations.
