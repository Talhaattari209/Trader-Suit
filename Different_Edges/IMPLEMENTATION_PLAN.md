# Implementation Plan: User Prompt → LLM → Models & Workflows

This document provides an **efficient, unified plan** to implement all approaches in `Different_Edges/` so that:

1. **User** prompts an idea/instruction (e.g. “add pattern-based edge”, “exploit tokenized asset arb”).
2. **LLM** interprets the instruction and drives **code generation** (Strategist) and **workflow selection**.
3. **Models and workflows** (ML/DL/RL, financial sims, connectors) do the actual work.

The plan reuses the existing **Ralph Wiggum Loop** (Librarian → Strategist → Killer → Risk Architect) and adds a **prompt entry point**, an **edge registry**, and **modular edge implementations** that plug into the same pipeline.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER PROMPT (idea/instruction)                                               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  INSTRUCTION ROUTER (new)                                                    │
│  • Parse prompt → edge_type(s) + intent                                       │
│  • Write Needs_Action or inject into Librarian                                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RALPH WIGGUM LOOP (existing)                                                 │
│  Watchers → Needs_Action → Librarian → Plans → Strategist → Drafts → Killer │
│  LLM (Librarian/Strategist) uses EDGE REGISTRY + plan context to:             │
│  • Choose which edge module(s) and models (ML/DL/RL) to reference            │
│  • Generate code that calls src/edges/<edge>/ and src/ml, src/dl, src/rl    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  EDGE MODULES (new, under src/edges/)                                         │
│  Each edge: data prep → models (ML/DL/RL) → validate (Monte Carlo/GARCH)     │
│  → execute (connectors). Orchestrator runs “workflow” for selected edge(s).  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Edge Registry (Single Source of Truth)

Add **one module** that maps user-facing concepts to edge types, file paths, and workflow steps. The LLM (Librarian/Strategist) and the Instruction Router use this to stay aligned.

**New file: `src/edges/edge_registry.py`**

| Edge Type | Keywords / Intent | Core Modules | Models Used | Data Sources |
|-----------|-------------------|--------------|-------------|--------------|
| **Statistical** | pairs trading, cointegration, z-score, mean reversion | `statistical_edges.py`, `preprocessor.py` | XGBoost, KMeans, LSTM, PPO | Polygon, US30 loader |
| **Pattern-Based** | head-and-shoulders, candlestick, chart pattern | `pattern_based/` | RF, Boruta, CNN, LSTM, PPO | US30, Polygon OHLCV |
| **Volume-Based** | volume spike, VWAP, TWAP, institutional footprint | `volume_based/` | RF, CNN, PPO | Polygon tick/agg |
| **Market Structure** | ICT, order block, FVG, BOS, liquidity sweep | `market_structure.py`, `structure_agent` | Hurst, RF, Transformer, DQN | Alpaca, US30 |
| **Tokenized Assets** | tokenized RWA, cross-chain arb, BUIDL, gas | `tokenized_assets.py`, `coingecko_connector` | XGBoost, GNN, DQN | CoinGecko |
| **Geopolitical** | EM, multipolar, USD weak, regime, conflict | `geo_agent`, `regime_clustering`, `ppo_geo` | GARCH, LSTM, KMeans, PPO | Polygon (EEM), X/news |
| **Prediction/Event** | prediction market, Polymarket, Kalshi, earnings, calendar | `prediction_event/` | XGBoost, BERT/Transformer, PPO | Polymarket, Kalshi, Trading Economics |
| **AI-Enhanced** | sentiment, factor mining, momentum, arb, microstructure, hybrid | `sentiment_news`, `factor_mining`, `momentum_reversion`, etc. | BERT, XGBoost, Autoencoder, LSTM, PPO | RSS, X, us30_loader |

**Efficiency**: One registry; all agents and the router read from it. Adding a new edge = one row + implementing the listed modules.

---

## 3. User Prompt Entry Point

**Goal**: User types an instruction → system turns it into a **Needs_Action** item (or direct Librarian input) so the existing loop does the rest.

**Option A – File-based (minimal change)**  
- **New**: `src/prompt/instruction_router.py`  
  - Input: `user_instruction: str`  
  - Uses LLM to: (1) classify intent, (2) pick `edge_type(s)` from the registry, (3) produce a short “research request” text.  
  - Writes one file into `VAULT_PATH/Needs_Action/instruction_<timestamp>.md` (directly in Needs_Action so the Librarian sees the full EDGE_TYPE and request without following links).  
- **Entry script**: `run_from_prompt.py`  
  - Reads instruction from CLI arg or stdin, calls `instruction_router.run(instruction)`, then runs `run_one_cycle` (orchestrator or `run_workflow.py`).  
- No change to Librarian’s contract: it still reads from Needs_Action and produces Plans.

**Option B – Direct Librarian prompt (faster for single shot)**  
- **New**: `run_from_prompt.py --direct`  
  - Builds a single “synthetic” plan content via LLM: “User asked: …; suggest edge type and research plan.”  
  - Writes that as `RESEARCH_PLAN_<slug>.md` into Plans/ and then runs only Strategist → Killer (skip Watchers/Librarian).  
- Use when the user instruction is already a clear “implement this edge” and you want one cycle only.

**Recommended**: Implement **Option A** first (file-based), then add Option B as a shortcut.

**New/updated files**:
- `src/prompt/__init__.py`
- `src/prompt/instruction_router.py` (LLM + edge_registry to create Needs_Action content)
- `run_from_prompt.py` (CLI: `python run_from_prompt.py "Add pattern-based head-and-shoulders edge"`)

---

## 4. LLM-Driven Code Generation (Strategist + Edge Context)

**Goal**: Strategist’s generated code **fulfills the instruction** by calling the right **models and workflows** for the chosen edge.

**Changes**:
1. **Librarian output**  
   - Include in each Research Plan: **edge_type** (from registry) and **required_components** (e.g. “ML classifier + backtest + Monte Carlo”).  
   - Instruction Router (or Librarian) sets these from the registry based on the user prompt.

2. **Strategist system prompt**  
   - Add: “You have access to edge modules under `src/edges/`. The plan specifies edge_type and required_components. Generate code that imports and uses the appropriate edge module (e.g. `from src.edges.pattern_based.pattern_workflow import run_pattern_edge`) and implements the strategy interface.”  
   - Provide the **edge registry** (or a short summary) in the prompt so the Strategist knows file paths and function names.

3. **Draft contract**  
   - Drafts remain `BaseStrategy` implementations for Killer’s backtest.  
   - The **strategy class** can delegate to an edge workflow (e.g. `run_pattern_edge()` for pattern-based) that runs ML/DL/RL internally; `entry`/`exit`/`risk` then use the workflow’s outputs (signals, position size).

**Efficiency**: One prompt upgrade and registry in context; no separate “code generator” per edge.

---

## 5. Workflow Layer (Orchestrate Models per Edge)

**Goal**: Each edge has a **single workflow** that: Perceive (data) → Reason (optional LLM/agents) → Validate (Monte Carlo/GARCH) → Execute (connectors). The pipeline runs this workflow when that edge is selected.

**New**: `src/edges/base_workflow.py` (abstract)

- Define interface, e.g.:
  - `get_data() -> pd.DataFrame | dict`
  - `run_models(state) -> signals/weights`
  - `validate(signals, data) -> approved: bool, metrics: dict`
  - `execute(signals, connector) -> None`
- Shared helpers: call `MonteCarloPro`, GARCH (from `src/tools`), and connectors.

**Per-edge workflow** (one per edge type, in the paths already specified in the Different_Edges docs):

| Edge | Workflow File | Responsibilities |
|------|----------------|------------------|
| Statistical | `src/edges/statistical_workflow.py` | Preprocess → StatisticalModels (XGBoost, LSTM, PPO) → pairs_trading_test → Killer-style validation → deploy_rl |
| Pattern | `src/edges/pattern_based/pattern_workflow.py` | Preprocess OHLCV → pattern hypothesis (LLM) → ML/DL detection → backtest + Monte Carlo → PPO execution |
| Volume | `src/edges/volume_based/volume_workflow.py` | load_volume_data → RF/CNN → PPO (VWAP) → validate → execute |
| Market Structure | `src/edges/market_structure_workflow.py` | Preprocess → Hurst/regime → Structure Agent (LLM) + Transformer → DQN → validate → execute |
| Tokenized | `src/edges/tokenized_workflow.py` | CoinGecko → GNN/discrepancy ML → DQN router → Monte Carlo (gas/jumps) → execute |
| Geopolitical | `src/edges/geo_workflow.py` | X/Polygon data → Geo/Macro agents → LSTM/KMeans → PPO reallocation → validate → execute |
| Prediction/Event | `src/edges/prediction_event/executor.py` + validator | data_fetchers → Event/Debate agents → XGBoost/Transformer/PPO → validate → execute |
| AI-Enhanced | `src/edges/ai_enhanced_workflow.py` or per sub-edge | Sentiment / factor / momentum / arb / hybrid: each sub-edge has a small workflow calling shared models |

**Efficiency**: One base interface; each edge implements one workflow that reuses `src/tools`, `src/connectors`, and shared preprocessors.

---

## 6. Phased Implementation Order

Implement in this order so the “user prompt → LLM → models/workflows” path works early and more edges plug in over time.

### Phase 1 – Foundation (no new edge logic yet)
1. Add **edge registry**: `src/edges/edge_registry.py` (table + helper `get_edge_info(edge_type)`).
2. Add **instruction router**: `src/prompt/instruction_router.py` (LLM + registry → Needs_Action file).
3. Add **run_from_prompt.py** (instruction → router → one cycle).
4. Extend **Librarian** so plans can include `edge_type` and `required_components` (from registry).
5. Extend **Strategist** prompt with registry summary and “use src/edges/” instruction.

**Outcome**: User prompt → Needs_Action → Librarian → Plan (with edge_type) → Strategist → draft that *references* edge modules (stubs ok).

### Phase 2 – One full edge end-to-end (e.g. Statistical)
1. Implement **Statistical** edge as in `Statistical_approach.md`:  
   `preprocessor.py`, `statistical_edges.py`, `librarian_stat`/`strategist_stat`/`killer_stat` (or integrate into existing agents via registry).
2. Add **statistical_workflow.py** that runs: load_and_preprocess → StatisticalModels → validate_strategy (Killer-style) → deploy_rl.
3. Ensure Strategist-generated draft can call this workflow and implement `BaseStrategy` using its signals.
4. Test: prompt “implement pairs trading” → plan → code → Killer validates.

**Outcome**: One edge fully driven by user prompt and executed by models/workflows.

### Phase 3 – Remaining edges (parallelizable)
Implement in parallel (by different devs or incrementally):

1. **Pattern-Based** – `pattern_based/` (preprocessor, ML/DL, RL, pattern_agent, pattern_workflow).
2. **Volume-Based** – `volume_based/` (volume_loader, volume_analyzer, volume_rl_agent, volume_workflow).
3. **Market Structure** – `market_structure.py`, `structure_agent`, `regime_classifier`, `dqn_breakout`, workflow.
4. **Tokenized Assets** – `tokenized_assets.py`, `coingecko_connector`, `tokenized_ml`, `gnn_models`, `dqn_router`, workflow.
5. **Geopolitical** – `geo_agent`, `macro_agent`, `regime_clustering`, `ppo_geo`, `lstm_fx`, workflow.
6. **Prediction/Event** – `prediction_event/` (data_fetchers, models_ml/dl/rl, agents, validator, executor).
7. **AI-Enhanced** – sentiment, factor_mining, momentum_reversion, arbitrage, microstructure, alternative_data, hybrid (each with a small workflow; can share `ai_enhanced_workflow.py` dispatcher).

**Outcome**: All eight approaches implementable via user prompt; LLM selects edge and generates code that calls the right workflow.

### Phase 4 – Hardening and scaling
- **Multi-edge prompts**: “Combine sentiment and momentum” → registry returns two edge types → Librarian plan mentions both → Strategist generates code that uses hybrid or two workflows.
- **Retraining and schedules**: Per-edge docs (e.g. quarterly retrain); run via cron or workflow trigger.
- **Observability**: Log which edge_type and workflow ran for each cycle; store in Logs and optional DB.

---

## 7. File Layout Summary

```
src/
├── prompt/
│   ├── __init__.py
│   └── instruction_router.py      # User instruction → Needs_Action + edge_type
├── edges/
│   ├── __init__.py
│   ├── edge_registry.py           # Single table + get_edge_info()
│   ├── base_workflow.py           # Abstract workflow interface
│   ├── statistical_edges.py
│   ├── statistical_workflow.py
│   ├── pattern_based/
│   │   ├── pattern_workflow.py
│   │   ├── pattern_detector_ml.py
│   │   ├── pattern_detector_dl.py
│   │   ├── pattern_rl_agent.py
│   │   └── pattern_agent.py
│   ├── volume_based/
│   │   ├── volume_workflow.py
│   │   ├── volume_analyzer.py
│   │   ├── volume_rl_agent.py
│   │   └── volume_agent.py
│   ├── market_structure.py
│   ├── market_structure_workflow.py
│   ├── tokenized_assets.py
│   ├── tokenized_workflow.py
│   ├── geo_workflow.py
│   ├── prediction_event/
│   │   ├── data_fetchers.py
│   │   ├── models_ml.py, models_dl.py, models_rl.py
│   │   ├── agents.py
│   │   ├── validator.py
│   │   └── executor.py
│   └── (ai_enhanced: sentiment_news, factor_mining, momentum_reversion, ...)
├── data/
│   ├── preprocessor.py            # Shared PCA/normalization
│   ├── volume_loader.py
│   ├── market_structure_preprocessor.py
│   └── pattern_preprocessor.py
├── ml/
│   ├── regime_classifier.py
│   ├── tokenized_ml.py
│   └── regime_clustering.py
├── dl/
│   ├── gnn_models.py
│   ├── transformer_analyzer.py
│   └── lstm_fx.py
├── rl/
│   ├── stat_rl_agent.py
│   ├── dqn_router.py
│   ├── dqn_breakout.py
│   └── ppo_geo.py
├── agents/                        # Existing + optional edge-specific (e.g. crypto_agent, geo_agent)
├── tools/                         # Existing Monte Carlo, GARCH, etc.
└── connectors/                    # Existing + coingecko, polygon, etc.

run_from_prompt.py                 # CLI: user instruction → router → one cycle
```

---

## 8. Success Criteria

- **User** can say: “Implement a pattern-based head-and-shoulders edge” or “Add tokenized asset arbitrage” and the system:
  1. Creates a Needs_Action (or plan) with the right edge_type.
  2. Librarian produces a plan that references that edge and required models.
  3. Strategist generates Python that uses the correct edge workflow and implements `BaseStrategy`.
  4. Killer validates the draft with Monte Carlo; on APPROVE, the workflow’s execution path (RL/connectors) can run.
- **All eight edge types** are represented in the registry and have a corresponding workflow (or clear stub) so the LLM can “code to fulfill the instruction” by calling these modules.
- **No duplication**: Shared preprocessors, `MonteCarloPro`, GARCH, and connectors are used across edges; only edge-specific logic lives under `src/edges/` and optional `src/ml`, `src/dl`, `src/rl`.

This plan ties every file in `Different_Edges/` into a single path: **user prompt → LLM (Librarian/Strategist) → code and workflow selection → models and workflows do the work.**
