# Implementation Plan: Agent Interfaces Loader + Monte Carlo

**Scope:** Implement the components specified in:
- **Agent_interfaces_loader.md** — BaseAgent, US30 Data Loader, and tooling/deps.
- **Monte carlo.md** — MonteCarloPro engine, Killer Agent, validation protocol, and tests.

**Deliverable:** This plan is for your review. After approval, implementation can follow this order.

---

## 1. Source of requirements

| Document | Components |
|----------|------------|
| **Agent_interfaces_loader.md** | 1) `BaseAgent` (src/agents/base_agent.py)<br>2) `US30Loader` (src/data/us30_loader.py)<br>3) Prompt also asks for `src/tools/monte_carlo.py` + requirements.txt (pandas, numpy, scikit-learn, stable-baselines3) |
| **Monte carlo.md** | 1) `MonteCarloPro` (src/tools/monte_carlo_pro.py)<br>2) Killer Agent (src/agents/killer_agent.py) using BaseAgent<br>3) Validation Protocol (Company_Handbook or docs)<br>4) Unit test for `prob_of_ruin` |

**Reconciliation:**  
- Use **one** Monte Carlo implementation: **MonteCarloPro** in `src/tools/monte_carlo_pro.py` (professional-grade; satisfies Monte carlo.md and the “monte carlo tool” ask in Agent_interfaces_loader.md).  
- No separate `monte_carlo.py` unless you want a thin wrapper that calls MonteCarloPro; plan assumes **only** `monte_carlo_pro.py`.

---

## 2. Target folder and file layout

```
src/
├── agents/
│   ├── __init__.py          # export BaseAgent, KillerAgent
│   ├── base_agent.py        # BaseAgent (ABC) — from Agent_interfaces_loader.md
│   └── killer_agent.py      # KillerAgent(BaseAgent) — from Monte carlo.md
├── data/
│   ├── __init__.py          # export US30Loader
│   └── us30_loader.py       # US30Loader — from Agent_interfaces_loader.md
├── tools/
│   ├── __init__.py          # export MonteCarloPro
│   └── monte_carlo_pro.py   # MonteCarloPro — from Monte carlo.md
├── db/                      # (existing)
├── watchers/                # (existing)
└── ...
```

**New dirs:** `src/agents/`, `src/data/`, `src/tools/`.  
**New files:** `base_agent.py`, `killer_agent.py`, `us30_loader.py`, `monte_carlo_pro.py`, plus `__init__.py` in each new package.

**Tests (suggested):**

```
tests/
├── __init__.py
├── test_monte_carlo_pro.py   # unit test for prob_of_ruin (and optionally other metrics)
└── (optional) test_us30_loader.py, test_killer_agent.py
```

**Docs / vault:**

- **Validation Protocol** (from Monte carlo.md): either in `AI_Employee_Vault/Company_Handbook.md` or in a small `docs/VALIDATION_PROTOCOL.md` (or both). Plan assumes one canonical place (e.g. Company_Handbook) and optional copy in docs.

---

## 3. Component-by-component plan

### 3.1 BaseAgent (`src/agents/base_agent.py`)

- **Source:** Agent_interfaces_loader.md (verbatim logic).
- **Content:**
  - Class `BaseAgent(ABC)` with `__init__(self, name: str)`.
  - Logger: `logging.getLogger(f"Agent.{name}")`, level INFO.
  - Abstract: `async def perceive(self, input_data: Any) -> Any`.
  - Abstract: `async def reason(self, state: Any) -> Dict[str, Any]`.
  - Abstract: `async def act(self, plan: Dict[str, Any]) -> bool`.
  - Concrete: `def log_action(self, action_name: str, status: str)`.
- **Dependencies:** stdlib only (`logging`, `abc`, `typing`).
- **No tests** in this plan (optional later: a small concrete agent for testing).

---

### 3.2 US30Loader (`src/data/us30_loader.py`)

- **Source:** Agent_interfaces_loader.md (verbatim logic).
- **Content:**
  - Class `US30Loader` with `__init__(self, file_path: str)` and `MinMaxScaler()`.
  - `load_clean_data(self) -> pd.DataFrame`: read CSV, capitalize columns, optional `Timestamp` → index, dropna, sort_index.
  - `get_rl_features(self, df: pd.DataFrame) -> np.ndarray`: `['Open','High','Low','Close','Volume']`, min-max scaled.
- **Dependencies:** pandas, numpy, scikit-learn (MinMaxScaler).
- **Edge cases (optional in v1):** Missing columns, non-numeric columns, empty CSV — can be documented or handled with clear errors in a follow-up.

---

### 3.3 MonteCarloPro (`src/tools/monte_carlo_pro.py`)

- **Source:** Monte carlo.md (code block).
- **Content:**
  - `MonteCarloPro(iterations=10000, confidence_level=0.95)`.
  - `simulate_paths(returns: pd.Series, initial_capital=100000.0) -> Dict`: bootstrap shuffle, equity path, max drawdown per path; return dict with `ending_values`, `max_dd_dist`, `var_95`, `expected_shortfall`, `prob_of_ruin` (50% loss threshold).
  - `inject_execution_friction(returns, slippage_pct=0.0002, latency_shocks=0.1) -> pd.Series`.
  - `stress_test_regimes(returns, vol_multiplier=2.0) -> Dict` (reuse `simulate_paths` on stressed returns).
  - `get_decision_metrics(sim_results: Dict) -> str` (win prob, VaR 95, worst-case DD 99th).
- **Dependencies:** numpy, pandas (typing from typing).
- **Fix in provided code:** `expected_shortfall` uses 5th percentile; plan keeps that . `var_95` in the snippet uses `(1 - confidence_level) * 100`; for 0.95 that’s 5th percentile — correct for left tail. No change required unless you want configurable percentiles.

---

### 3.4 KillerAgent (`src/agents/killer_agent.py`)

- **Source:** Monte carlo.md (“Killer Agent” + Implementation Spec).
- **Behavior:**
  - Inherits `BaseAgent`.
  - **perceive:** Read “US30 backtest CSV” (path or content) and parse to a returns series (or OHLCV if we use loader; spec says “backtest CSV” → assume returns or derive from equity/close).
  - **reason:** Run `inject_execution_friction` (e.g. 2 pip ≈ 0.0002), then `simulate_paths` (e.g. 10k paths), compute metrics; decide REJECT / FLAG / APPROVE per Validation Protocol.
  - **act:** Write a “Risk Audit” markdown file into the Obsidian Vault (path configurable, e.g. `Vault/Logs/Risk_Audit_<timestamp>.md` or similar).
- **Output (Risk Audit):** Include at least: `prob_of_ruin`, p_value or equivalent, actual_sharpe vs mean_simulated_sharpe, decision (REJECT/FLAG/APPROVE), and optionally `get_decision_metrics()` text.
- **Dependencies:** BaseAgent, MonteCarloPro, US30Loader (if backtest CSV is OHLCV) or pandas only (if CSV is returns). Vault path from config/env.
- **Clarification:** “US30 backtest CSV” format will be defined (e.g. columns: date, return or open/high/low/close/volume). Plan: support at least one explicit format (e.g. `date, return` or `Timestamp, Open, High, Low, Close, Volume`); document in docstring or Company_Handbook.

---

### 3.5 Validation Protocol (documentation)

- **Source:** Monte carlo.md “Validation Protocol”.
- **Content:**
  1. Ingest: load US30 backtest results from Strategist.
  2. Perturb: `inject_execution_friction` (e.g. 2 pip).
  3. Simulate: 10,000 paths via `simulate_paths`.
  4. Audit rules:
     - IF `prob_of_ruin` > 1% OR p_value > 0.05 → REJECT (move to Strategy_Graveyard).
     - IF `actual_sharpe / mean_simulated_sharpe` < 0.8 → FLAG as Overfit.
     - ELSE → APPROVE (move to Done).
- **Where:** Add to `AI_Employee_Vault/Company_Handbook.md` (or create it if missing) under a “Validation Protocol” or “Monte Carlo Gate” section. Optionally mirror in `docs/VALIDATION_PROTOCOL.md`.
- **Note:** “Move to folder” is a policy; KillerAgent in v1 can write the decision and path suggestions in the Risk Audit so a human or orchestrator can perform the move (or we add file-move in a later phase).

---

### 3.6 Unit test for `prob_of_ruin`

- **Source:** Monte carlo.md “unit test to ensure the prob_of_ruin calculation is accurate for a 10% drawdown series”.
- **Idea:** Construct a small returns series that is known to produce a 50% capital loss (e.g. one or more large negative returns). Run `simulate_paths` and check that `prob_of_ruin` is in an expected range (e.g. > 0 for a bad series, or exact value for a deterministic test). If we use a deterministic seed, we can assert a specific value or a narrow range.
- **File:** `tests/test_monte_carlo_pro.py`.
- **Dependencies:** pytest, numpy, pandas. Add pytest to requirements (dev).

---

## 4. Dependencies (requirements.txt)

**Current:** `asyncpg`

**Add (from Agent_interfaces_loader.md + implementation):**

- pandas  
- numpy  
- scikit-learn  
- stable-baselines3  

**Add for tests:**

- pytest  

**Proposed requirements.txt (append):**

```
pandas
numpy
scikit-learn
stable-baselines3
pytest
```

(Keep asyncpg at top if you prefer.)

---

## 5. Implementation order (for review)

| Step | Task | Delivers |
|------|------|----------|
| 1 | Create `src/agents/`, `src/data/`, `src/tools/` and their `__init__.py` | Package structure |
| 2 | Implement `src/agents/base_agent.py` (exact code from Agent_interfaces_loader.md) | BaseAgent contract |
| 3 | Implement `src/data/us30_loader.py` (exact code from Agent_interfaces_loader.md) | US30Loader |
| 4 | Implement `src/tools/monte_carlo_pro.py` (from Monte carlo.md) | MonteCarloPro |
| 5 | Implement `src/agents/killer_agent.py` (perceive/reason/act using MonteCarloPro + Validation rules) | KillerAgent |
| 6 | Add Validation Protocol to Company_Handbook.md (or create stub + docs) | Documented protocol |
| 7 | Add `tests/test_monte_carlo_pro.py` (prob_of_ruin + optional sanity checks) | Unit test |
| 8 | Update `requirements.txt` (pandas, numpy, scikit-learn, stable-baselines3, pytest) | Deps |

**Optional / follow-up:**

- `tests/test_us30_loader.py` for load_clean_data / get_rl_features.
- `tests/test_killer_agent.py` (integration-style: CSV in → Risk Audit out).
- Thin `src/tools/monte_carlo.py` that imports and re-exposes MonteCarloPro if you want a single “monte_carlo” entry point for Claude.

---

## 6. Open points for your review

1. **Backtest CSV format:** Confirm whether KillerAgent will receive (a) a **returns series** (e.g. `date, return`) or (b) **OHLCV** (then we derive returns via US30Loader or simple close-to-close). Plan assumes we define one canonical format and document it.
2. **Vault path for Risk Audit:** Use a fixed subfolder (e.g. `AI_Employee_Vault/Logs/`) and filename pattern (e.g. `Risk_Audit_YYYYMMDD_HHMMSS.md`)? Or configurable via env (e.g. `VAULT_PATH`, `RISK_AUDIT_DIR`)?
3. **“Move to Strategy_Graveyard / Done”:** Implement as KillerAgent actually moving files in the vault in v1, or only writing the decision in the Risk Audit and leaving moves to a human/orchestrator?
4. **p_value in Validation Protocol:** MonteCarloPro currently doesn’t return a p_value. Options: (a) add a simple p_value (e.g. probability that observed Sharpe could come from random strategy) in MonteCarloPro or KillerAgent, or (b) document “p_value” as TBD and use only `prob_of_ruin` for the first implementation. Plan suggests (b) unless you want (a) in scope now.
5. **Company_Handbook.md:** If it doesn’t exist, create a minimal stub with only the Validation Protocol section, or create a full template (Dashboard, Business_Goals, etc.) — your preference.

---

## 7. Summary checklist (for you to review)

- [ ] **BaseAgent** in `src/agents/base_agent.py` (async perceive/reason/act + log_action).
- [ ] **US30Loader** in `src/data/us30_loader.py` (load_clean_data, get_rl_features).
- [ ] **MonteCarloPro** in `src/tools/monte_carlo_pro.py` (simulate_paths, inject_execution_friction, stress_test_regimes, get_decision_metrics).
- [ ] **KillerAgent** in `src/agents/killer_agent.py` (BaseAgent; CSV → friction → simulate → Risk Audit .md in Vault).
- [ ] **Validation Protocol** in Company_Handbook.md (or docs).
- [ ] **Unit test** for `prob_of_ruin` in `tests/test_monte_carlo_pro.py`.
- [ ] **requirements.txt** updated (pandas, numpy, scikit-learn, stable-baselines3, pytest).
- [ ] **Package __init__.py** for agents, data, tools (exports as above).

Once you confirm or adjust the open points (§6) and the checklist (§7), this plan can be used as the implementation spec.
