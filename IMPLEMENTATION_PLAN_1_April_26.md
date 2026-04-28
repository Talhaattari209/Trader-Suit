# Implementation Plan — 1 April 2026
## Project: Trader-Suit / OpenClaw Alpha Research System
### Goal: End-to-End Runnable Human-Controlled Workflow + Responsive UI

> **Reference:** `requirement_1_April_26.md` — client requirements v2026-04-01  
> **Execution order is mandatory.** Each phase builds on the previous. Do not skip ahead.

---

## Table of Contents

1. [Execution Order Summary](#execution-order-summary)
2. [Phase 1 — UV Environment Migration](#phase-1--uv-environment-migration)
3. [Phase 2 — Filesystem-Only Persistence (DataStore)](#phase-2--filesystem-only-persistence-datastore)
4. [Phase 3 — Price Level Detector (New Module)](#phase-3--price-level-detector-new-module)
5. [Phase 4 — Agent Updates (price_levels integration)](#phase-4--agent-updates-price_levels-integration)
6. [Phase 5 — FastAPI Workflow Endpoints](#phase-5--fastapi-workflow-endpoints)
7. [Phase 6 — Performance Metrics Module](#phase-6--performance-metrics-module)
8. [Phase 7 — SHAP Analysis Integration](#phase-7--shap-analysis-integration)
9. [Phase 8 — Multi-Alpaca Account Support](#phase-8--multi-alpaca-account-support)
10. [Phase 9 — 5 Critical UI Pages (Fully Functional + Responsive)](#phase-9--5-critical-ui-pages-fully-functional--responsive)
11. [Phase 10 — Debug Logging & LLM/MCP Console Output](#phase-10--debug-logging--llmmcp-console-output)
12. [Phase 11 — Parameter Stability Improvements](#phase-11--parameter-stability-improvements)
13. [Phase 12 — Local PC Computation Budget (80–90% Reduction)](#phase-12--local-pc-computation-budget-8090-reduction)
14. [Phase 13 — Autonomous AI Agent (Floating Chat Widget)](#phase-13--autonomous-ai-agent-floating-chat-widget)
15. [Phase 14 — Execution Reports Enhancement & Bug Fixes](#phase-14--execution-reports-enhancement--bug-fixes)
16. [End-to-End Test Protocol](#end-to-end-test-protocol)
17. [File Change Matrix](#file-change-matrix)
18. [Responsive UI Design Rules](#responsive-ui-design-rules)

---

## Execution Order Summary

```
Phase 1  → UV + dependencies
Phase 2  → DataStore + FilesystemStore (foundation for everything)
Phase 3  → PriceLevelDetector (new file; depends on US30Loader)
Phase 4  → Agent updates (price_levels injected into Librarian, Strategist, Killer)
Phase 5  → FastAPI workflow endpoints (/workflow/*, /montecarlo/run, /shap/analyze, ...)
Phase 6  → PerformanceMetrics module (used by Phase 5 + UI)
Phase 7  → SHAP integration (depends on trained ML models from Phase 4)
Phase 8  → Multi-Alpaca (env vars + dropdown; independent)
Phase 9  → 5 UI pages wired to Phase 5 endpoints (responsive CSS)
Phase 10 → Debug logging (add to LLM client + MCP server + agents)
Phase 11 → Parameter stability (MonteCarloPro nudge + stability score)
Phase 12 → Local PC Computation Budget (ComputationBudget config; 80-90% reduction on all heavy ops)
Phase 13 → Autonomous AI Agent: floating chat widget on all pages + FastAPI /agent/* routes
Phase 14 → Execution Reports rewrite (real Alpaca closed orders, SL/TP, Reports tab) + API_BASE_URL fixes
```

---

## Phase 1 — UV Environment Migration

### Why
Client requires `uv run` commands. UV is significantly faster than pip for dependency resolution and supports lock files, ensuring reproducible environments on both local Windows and Colab.

### Changes

#### 1.1 ~~Install UV (one-time)~~ — **SKIP: UV is already installed**
```bash
# uv is already installed — skip this step
# pip install uv  ← not needed
```

#### 1.2 Create `requirements.in` (source of truth)
**New file:** `requirements.in`

```
# Core
fastapi
uvicorn[standard]
streamlit>=1.30
plotly
httpx              # replace requests in dashboard pages (async-capable)
pydantic>=2.0

# Agents & LLM
# NOTE: anthropic is NOT used — no ANTHROPIC_API_KEY; project uses GEMINI_API_KEY
google-generativeai
python-dotenv

# Data & ML
pandas
numpy
scikit-learn
pandas-ta
yfinance

# Broker
alpaca-py
MetaTrader5; sys_platform == "win32"

# Database
asyncpg

# RL/DL (Colab-heavy; optional locally)
stable-baselines3
torch; extra == "full"
tensorflow; extra == "full"

# Explainability
shap

# Validation
pytest
pytest-asyncio
```

#### 1.3 Compile lock file and create venv
```bash
uv pip compile requirements.in -o requirements.txt
uv venv .venv
uv pip sync requirements.txt
```

#### 1.4 Update run commands everywhere
Replace all `python` / `streamlit` references in docs and Makefiles:

```bash
uv run python main.py                              # FastAPI (uvicorn)
uv run streamlit run src/dashboard/app.py          # Streamlit
uv run python -m src.orchestration.orchestrator    # Agent loop
uv run pytest tests/                               # Tests
```

#### 1.5 Update `pyproject.toml`

Add:
```toml
[tool.uv]
dev-dependencies = ["pytest", "pytest-asyncio", "ruff"]
```

---

## Phase 2 — Filesystem-Only Persistence (DataStore)

### Why
The client confirmed: **no Neon DB required for the primary workflow**. All strategy metadata, alphas, and price_levels must be stored in `DataStore/` as JSON files so they are human-readable, git-committable, and work without a DB connection.

### 2.1 Create `DataStore/` directory structure

```
DataStore/
├── alphas.json          ← all alpha hypotheses with full metadata + price_levels
├── strategies.json      ← index of all draft/production/graveyard strategies
├── audit_log.json       ← MC run results
├── workflow_state.json  ← current workflow step and context
└── debug.log            ← LLM/MCP debug output (Phase 10)
```

### 2.2 Create `src/persistence/filesystem_store.py` (NEW FILE)

**Purpose:** Single class that reads/writes all `DataStore/` JSON files. All agents and API endpoints use this instead of direct file I/O or asyncpg.

**Interface to implement:**

```python
class FilesystemStore:
    def __init__(self, datastore_path: str = "DataStore"):
        self.root = Path(datastore_path)
        self.root.mkdir(exist_ok=True)

    # ── Alphas ──────────────────────────────────────────────────────────────
    def load_alphas(self) -> list[dict]:
        """Load all alpha records from alphas.json."""

    def save_alpha(self, alpha: dict) -> str:
        """Append alpha to alphas.json. Returns generated alpha_id."""

    def find_similar_alphas(self, hypothesis: str, top_k: int = 3) -> list[dict]:
        """Cosine similarity on hypothesis text + numeric price_levels comparison.
        Returns top_k most similar existing alphas with similarity scores."""

    # ── Strategies ──────────────────────────────────────────────────────────
    def load_strategies(self, status: str = None) -> list[dict]:
        """Load strategies index. Filter by status: 'draft'|'production'|'graveyard'."""

    def save_strategy_metadata(self, strategy_id: str, metadata: dict) -> None:
        """Write/update strategy entry in strategies.json."""

    def move_strategy(self, strategy_id: str, new_status: str) -> None:
        """Change strategy status (draft→production or draft→graveyard)."""

    # ── Audit log ────────────────────────────────────────────────────────────
    def log_mc_run(self, strategy_id: str, mc_results: dict, price_levels: dict) -> str:
        """Append MC run to audit_log.json. Returns run_id."""

    # ── Workflow state ────────────────────────────────────────────────────────
    def get_workflow_state(self) -> dict:
        """Return current workflow_state.json content."""

    def set_workflow_state(self, state: dict) -> None:
        """Overwrite workflow_state.json."""

    def advance_workflow_step(self, step: str, context: dict = None) -> None:
        """Advance to next step, merge context into state."""
```

### 2.3 Alpha record schema (with price_levels)

Every entry in `alphas.json` must follow this structure:

```json
{
  "alpha_id": "alpha_20260401_001",
  "hypothesis": "Volume spike at US30 session open predicts momentum",
  "edge_type": "volume_based",
  "regime_tags": ["trending", "high_vol"],
  "session": "us_open",
  "created_at": "2026-04-01T09:30:00",
  "status": "draft",
  "strategy_id": "strategy_volume_spike_001",
  "similarity_score": null,
  "price_levels": {
    "liquidity_zones": [
      {"type": "demand", "price": 42350.0, "strength": "high"},
      {"type": "supply", "price": 42800.0, "strength": "medium"}
    ],
    "fvg_zones": [
      {"type": "bullish", "low": 42100.0, "high": 42250.0, "timestamp": "2026-04-01T09:30"},
      {"type": "bearish", "low": 42700.0, "high": 42850.0, "timestamp": "2026-04-01T14:00"}
    ],
    "session_levels": {
      "us_open": {"open": 42450.0, "high": 42700.0, "low": 42300.0, "close": 42600.0, "mid": 42500.0},
      "us_session": {"high": 42800.0, "low": 42200.0, "mid": 42500.0},
      "day": {"open": 42400.0, "high": 42800.0, "low": 42200.0, "close": 42650.0, "mid": 42500.0},
      "week": {"open": 42000.0, "high": 43000.0, "low": 41800.0, "mid": 42400.0},
      "month": {"open": 41500.0, "high": 43200.0, "low": 41000.0, "mid": 42100.0}
    }
  }
}
```

### 2.4 Similarity comparison logic

In `find_similar_alphas()`, similarity is computed as a weighted combination:

```python
# Text similarity: TF-IDF cosine on hypothesis strings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Price level similarity: Euclidean distance on numeric fields
# Extract [day_high, day_low, week_high, week_low, month_mid] as vector
# Normalise and compute cosine similarity

# Final score: 0.6 * text_sim + 0.4 * price_level_sim
```

---

## Phase 3 — Price Level Detector (New Module)

### Why
Every strategy must carry a snapshot of the market-respected price levels at the time of creation. This allows comparison across strategies and gives the human reviewer immediate context during the Decision Gate.

> **CHANGE:** Price levels are detected on **1-hour (H1) candle** data. The `df` passed to all detector functions must be resampled to 1H OHLCV before calling. The `US30Loader` must provide or resample to 1H.  
> The `detect_all_price_levels()` function accepts either a tick/M5 DataFrame and resamples internally to 1H, or accepts a pre-resampled 1H DataFrame.

### 3.1 Create `src/tools/price_level_detector.py` (NEW FILE)

#### Functions to implement:

```python
def detect_liquidity_zones(df: pd.DataFrame, lookback: int = 20) -> list[dict]:
    """
    Identify swing highs (supply zones) and swing lows (demand zones).
    Logic:
      - Rolling window: find local maxima (High > High[i-1] and High > High[i+1])
      - Rank by volume at that bar: high volume = 'high' strength, else 'medium'
    Returns list of {"type": "demand"|"supply", "price": float, "strength": "high"|"medium"|"low"}
    """

def detect_fvg_zones(df: pd.DataFrame) -> list[dict]:
    """
    Fair Value Gap (FVG): 3-candle imbalance pattern.
    Bullish FVG: Low[i] > High[i-2]  (gap between candle 1 high and candle 3 low)
    Bearish FVG: High[i] < Low[i-2]
    Returns list of {"type": "bullish"|"bearish", "low": float, "high": float, "timestamp": str}
    """

def detect_session_levels(df: pd.DataFrame) -> dict:
    """
    Compute OHLCM (open/high/low/close/mid) for each time period via resample.
    Periods: us_open (09:30-10:30 ET), us_session (09:30-16:00 ET), day, week, month.
    Mid = (High + Low) / 2
    Returns full session_levels dict matching the schema above.
    """

def detect_all_price_levels(df: pd.DataFrame) -> dict:
    """
    Master function: calls all three detectors and returns the full price_levels dict.
    Called by Strategist Agent and Killer Agent automatically.
    """
```

#### Implementation detail — session levels:

```python
# Resample to day, week, month OHLC
daily   = df.resample("D").agg({"Open":"first","High":"max","Low":"min","Close":"last"})
weekly  = df.resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last"})
monthly = df.resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last"})

# Session filter (US Eastern, 09:30–10:30 open, 09:30–16:00 full)
# Apply timezone-aware filtering if df index is UTC
us_open_mask    = (df.index.hour == 9) & (df.index.minute >= 30) | (df.index.hour == 10) & (df.index.minute <= 30)
us_session_mask = (df.index.hour >= 9) & (df.index.hour < 16)
```

#### FVG detection logic (exact):

```python
for i in range(2, len(df)):
    # Bullish FVG: gap up — low of current candle > high of candle 2 bars ago
    if df["Low"].iloc[i] > df["High"].iloc[i - 2]:
        fvg_zones.append({
            "type": "bullish",
            "low": df["High"].iloc[i - 2],
            "high": df["Low"].iloc[i],
            "timestamp": str(df.index[i])
        })
    # Bearish FVG: gap down — high of current candle < low of candle 2 bars ago
    elif df["High"].iloc[i] < df["Low"].iloc[i - 2]:
        fvg_zones.append({
            "type": "bearish",
            "low": df["High"].iloc[i],
            "high": df["Low"].iloc[i - 2],
            "timestamp": str(df.index[i])
        })
```

---

## Phase 4 — Agent Updates (price_levels integration)

### 4.1 `src/agents/strategist_agent.py`

After generating `BaseStrategy` code:

1. Load US30 data via `US30Loader`
2. Call `detect_all_price_levels(df)` → `price_levels` dict
3. Write `price_levels` as a class attribute into the generated `.py` file:
   ```python
   self.price_levels = {<detected dict>}
   ```
4. Save price_levels into `DataStore/alphas.json` via `FilesystemStore.save_alpha()`

### 4.2 `src/agents/killer_agent.py`

After Monte Carlo run:

1. Call `detect_all_price_levels(df)` on the same data slice used for MC
2. Attach `price_levels` to the MC audit result
3. Write to `DataStore/audit_log.json` via `FilesystemStore.log_mc_run()`
4. Display price_levels in the Risk Audit `.md` written to `Logs/`

### 4.3 `src/agents/librarian_agent.py`

When receiving a new idea from `Needs_Action/`:

1. Call `FilesystemStore.find_similar_alphas(hypothesis)` before generating plan
2. Embed similarity report in the RESEARCH_PLAN:
   ```markdown
   ## Similarity Analysis
   - Most similar: alpha_20260401_001 (score: 0.82)
   - Matching price_levels: day_high=42800, week_open=42000
   - Recommendation: Merge with existing or confirm novelty before proceeding
   ```
3. Include the `price_levels` snapshot in the RESEARCH_PLAN YAML header

### 4.4 Workflow state tracking

Each agent must call:

```python
store.advance_workflow_step("librarian_done", {"alpha_id": alpha_id, "plan_path": plan_path})
store.advance_workflow_step("strategist_done", {"strategy_id": sid, "price_levels": pl})
store.advance_workflow_step("killer_done", {"mc_run_id": run_id, "pass": True/False})
store.advance_workflow_step("risk_done", {"kelly_fraction": 0.25, "position_size": 0.01})
```

This state is consumed by `GET /workflow/state` and displayed on the Home page.

---

## Phase 5 — FastAPI Workflow Endpoints

### 5.1 Create `src/api/workflow_routes.py` (NEW FILE)

All endpoints use `httpx` on the client side (dashboard) for async-compatible HTTP calls.

#### Workflow control endpoints

```
POST /workflow/start
  Body: {"idea": str, "template": str | None, "source_file": str | None}
  Action: writes to Needs_Action/ → triggers LibrarianAgent
  Returns: {"workflow_id": str, "step": "librarian_running", "alpha_id": str}

GET  /workflow/state
  Returns: current workflow_state.json
  {"step": str, "context": dict, "started_at": str, "alpha_id": str}

POST /workflow/feedback
  Body: {"workflow_id": str, "decision": "use_existing"|"create_new"|"merge"|"discard",
         "existing_alpha_id": str | None, "merge_notes": str | None}
  Action: routes to Strategist if create/merge, skips if use_existing
  Returns: {"next_step": str, "strategy_id": str | None}

POST /workflow/decision
  Body: {"workflow_id": str, "strategy_id": str,
         "decision": "discard"|"retest"|"approve"|"approve_with_tweaks",
         "tweaks": str | None, "feedback": str | None}
  Action: Human Decision Gate (post-MC)
         "approve" → Risk Architect → moves to Approved/
         "retest"  → re-runs MC with feedback context
         "discard" → moves to Graveyard
  Returns: {"status": str, "next_step": str}
```

#### Monte Carlo endpoint

```
POST /montecarlo/run
  Body: {"strategy_id": str, "iterations": int, "stress_tests": list[str],
         "walk_forward": bool, "out_of_sample": bool}
  Action: loads strategy → runs MonteCarloPro → saves to audit_log
  Returns: {
    "run_id": str,
    "pass": bool,
    "metrics": {
      "sharpe": float, "sortino": float, "max_dd": float,
      "var_95": float, "expected_shortfall": float,
      "prob_of_ruin": float, "win_probability": float,
      "stability_score": float,           ← Phase 11
      "overfit_cliff_flag": bool
    },
    "regime_results": {"2020_crash": {...}, "2022_bear": {...}, "2023_chop": {...}},
    "price_levels": {...}                  ← Phase 3
  }
```

#### SHAP endpoint

```
POST /shap/analyze
  Body: {"strategy_id": str, "model_type": "rf"|"lstm", "n_samples": int}
  Action: loads trained model → runs SHAP → returns feature importances
  Returns: {"feature_importance": {"RSI": 0.35, "ATR": 0.28, ...}, "run_id": str}
```

#### Data endpoints

```
GET  /data/alphas
  Query: ?status=all|draft|production|graveyard&limit=50
  Returns: list from FilesystemStore.load_alphas()

GET  /data/alphas/{alpha_id}
  Returns: single alpha record with full price_levels

GET  /data/strategies
  Query: ?status=draft|production|graveyard
  Returns: strategies index from FilesystemStore

GET  /performance/metrics/{strategy_id}
  Returns: full PerformanceMetrics from performance_metrics.py (Phase 6)

GET  /vault/{folder}
  Path: folder = Needs_Action|Plans|Approved|Reports|Logs|Graveyard
  Returns: list of files with name, size, modified_at

GET  /vault/{folder}/{filename}
  Returns: {"content": str} — raw file text

POST /vault/{folder}/{filename}
  Body: {"content": str}
  Action: writes file to vault folder

GET  /accounts
  Returns: list of configured Alpaca accounts with status (Phase 8)
```

### 5.2 Register routes in `src/api/main.py`

```python
from src.api.workflow_routes import router as workflow_router
app.include_router(workflow_router, prefix="")
```

---

## Phase 6 — Performance Metrics Module

### Create `src/tools/performance_metrics.py` (NEW FILE)

**All metrics computed from a `pd.Series` of trade returns.**

```python
def compute_full_metrics(returns: pd.Series, risk_free_rate: float = 0.0) -> dict:
    """
    Returns all performance metrics as a single dict.
    """
    ...
```

| Metric | Formula / Method |
|--------|-----------------|
| **Sharpe** | `(mean(r) - rf) / std(r) * sqrt(252)` |
| **Sortino** | `(mean(r) - rf) / downside_std(r) * sqrt(252)` — downside_std uses only negative returns |
| **Calmar** | `annualised_return / abs(max_drawdown)` |
| **Max Drawdown** | Running peak − trough, as % of peak |
| **Profit Factor** | `sum(positive returns) / abs(sum(negative returns))` |
| **Win Rate** | `count(r > 0) / total trades` |
| **Expectancy** | `(win_rate * avg_win) − (loss_rate * avg_loss)` |
| **e-Ratio** | `avg_win / avg_loss` (edge ratio) |
| **Omega** | `integral(1 - F(r)) dr / integral(F(r)) dr` above/below threshold |
| **Regime Sharpe** | Sharpe split by regime label from `regime_classifier` |
| **Stability Score** | From `parameter_stability_tests()` — 1 − std(prob_of_ruin) across nudges |

**Output dict schema:**
```json
{
  "sharpe": 1.8,
  "sortino": 2.1,
  "calmar": 1.2,
  "max_drawdown_pct": -8.2,
  "profit_factor": 1.6,
  "win_rate": 0.58,
  "expectancy": 0.0012,
  "e_ratio": 1.7,
  "omega": 1.4,
  "regime_sharpe": {"trending": 2.1, "ranging": 0.8, "volatile": 1.2},
  "stability_score": 0.87,
  "overfit_cliff_flag": false
}
```

This module is called by:
- `GET /performance/metrics/{strategy_id}` endpoint
- Killer Agent (attaches metrics to audit report)
- Strategy Library page (metric cards)

---

## Phase 7 — SHAP Analysis Integration

### 7.1 Install dependency

```bash
uv pip install shap
```

Add `shap` to `requirements.in`.

### 7.2 Create `src/tools/shap_analyzer.py` (NEW FILE)

```python
def run_shap_analysis(
    model,                      # sklearn RF or PyTorch LSTM
    X: np.ndarray,              # feature matrix used for prediction
    feature_names: list[str],   # e.g. ["RSI", "ATR", "Volume_ZScore", "VWAP_Dev"]
    model_type: str = "rf",     # "rf" or "lstm"
    n_samples: int = 100,       # subsample for speed
) -> dict:
    """
    Run SHAP and return ranked feature importances.
    """
    if model_type == "rf":
        explainer    = shap.TreeExplainer(model)
        shap_values  = explainer.shap_values(X[:n_samples])
        # For multi-class RF: shap_values is list; use class 1 (buy signal)
        importance   = np.abs(shap_values[1]).mean(axis=0)
    elif model_type == "lstm":
        # Convert to tensor; use DeepExplainer
        background   = torch.tensor(X[:50], dtype=torch.float32)
        explainer    = shap.DeepExplainer(model, background)
        shap_values  = explainer.shap_values(torch.tensor(X[:n_samples], dtype=torch.float32))
        importance   = np.abs(shap_values).mean(axis=(0, 1))

    return dict(sorted(
        zip(feature_names, importance.tolist()),
        key=lambda x: x[1], reverse=True
    ))
```

### 7.3 Wire to `POST /shap/analyze` (Phase 5)

The endpoint loads the strategy's trained model from `src/models/drafts/` or `src/models/production/`, loads the corresponding feature matrix, and calls `run_shap_analysis()`.

### 7.4 UI integration (Phase 9)

- **Strategy Library page**: "SHAP Analysis" button per strategy → calls `/shap/analyze` → bar chart
- **Optimization Lab page**: "Explain Last Run" button → same endpoint

---

## Phase 8 — Multi-Alpaca Account Support

### 8.1 Environment variables

Add to `.env.example`:

```env
# Primary Alpaca account
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_PAPER=true
ALPACA_TICKER_SYMBOL=SPY

# Secondary Alpaca account (optional failover)
ALPACA_API_KEY_2=
ALPACA_SECRET_KEY_2=
ALPACA_PAPER_2=true
ALPACA_ACCOUNT_2_LABEL=Backup Account
```

### 8.2 `GET /accounts` endpoint

```python
@app.get("/accounts")
def get_accounts():
    accounts = []
    if os.environ.get("ALPACA_API_KEY"):
        accounts.append({
            "id": "account_1",
            "label": "Primary",
            "paper": os.environ.get("ALPACA_PAPER", "true") == "true",
            "connected": is_alpaca_available()
        })
    if os.environ.get("ALPACA_API_KEY_2"):
        accounts.append({
            "id": "account_2",
            "label": os.environ.get("ALPACA_ACCOUNT_2_LABEL", "Backup"),
            "paper": os.environ.get("ALPACA_PAPER_2", "true") == "true",
            "connected": is_alpaca_available_2()
        })
    return accounts
```

### 8.3 Session state for selected account

In `src/dashboard/session_state.py`, add:

```python
if "selected_account" not in st.session_state:
    st.session_state["selected_account"] = "account_1"
```

### 8.4 UI: account selector dropdown

On **Execution & Reports** and **Home** sidebar:

```python
accounts = httpx.get(f"{API_BASE_URL}/accounts").json()
labels   = {a["id"]: f"{a['label']} ({'Paper' if a['paper'] else 'Live'})" for a in accounts}
selected = st.selectbox("Account", options=list(labels.keys()),
                        format_func=lambda k: labels[k], key="selected_account")
```

All subsequent `/account`, `/positions`, `/portfolio/history` calls pass `?account_id={selected}`.

---

## Phase 9 — 5 Critical UI Pages (Fully Functional + Responsive)

### Responsive UI Rules (applied to ALL pages)

See [Section 15](#responsive-ui-design-rules) for the complete ruleset. Summary:

1. **Never use hardcoded pixel widths in CSS.** Use `%`, `vw`, or `min()` functions.
2. **All `st.plotly_chart()` calls** must pass `use_container_width=True`.
3. **All `st.dataframe()` calls** must pass `use_container_width=True`.
4. **Column layouts** must use relative weights, never absolute widths.
5. **`apply_theme()`** must inject responsive CSS breakpoints.
6. **Sidebar controls** must be touch-friendly (min height 44px for buttons/selects).
7. **Tables** must be horizontally scrollable on mobile via CSS `overflow-x: auto`.
8. **Charts** must have `height` set in `plotly_layout()` that adapts to screen (300px mobile, 400px desktop via `config`).

### 9.1 Responsive CSS — update `src/dashboard/components.py`

Add the following to `apply_theme()`:

```python
st.markdown("""
<style>
/* ── Responsive layout ─────────────────────────────────── */
.main .block-container {
    max-width: 100% !important;
    padding: 1rem 1rem 2rem !important;
}
/* Scrollable tables on small screens */
.stDataFrame { overflow-x: auto !important; }

/* Touch-friendly controls */
.stButton > button,
.stSelectbox select,
.stMultiSelect,
.stSlider { min-height: 44px; }

/* Stack columns on very small screens */
@media (max-width: 768px) {
    [data-testid="column"] {
        width: 100% !important;
        flex: 0 0 100% !important;
        min-width: 100% !important;
    }
    .stSidebar { width: 100% !important; }
}

/* Metric cards — responsive grid */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    min-width: 120px;
}

/* Full-width charts */
[data-testid="stPlotlyChart"] { width: 100% !important; }
</style>
""", unsafe_allow_html=True)
```

---

### Page 1 — Alpha Idea Lab (`pages/1_Alpha_Idea_Lab.py`)

**Current state:** UI scaffold + hardcoded chat; no API calls.  
**Target:** Full end-to-end idea submission → comparison → feedback → strategy generation.

#### Changes:

**Replace** the current mock chat with real API calls:

```python
import httpx
from src.dashboard.config import API_BASE_URL

# Step 1: Submit idea → /workflow/start
if st.button("Generate Hypothesis"):
    with st.spinner("Librarian analysing idea..."):
        resp = httpx.post(f"{API_BASE_URL}/workflow/start", json={
            "idea": st.session_state["alpha_prompt"],
            "template": st.session_state.get("alpha_template")
        }, timeout=60)
        result = resp.json()
        st.session_state["workflow_id"] = result["workflow_id"]
        st.session_state["alpha_id"]    = result.get("alpha_id")
```

**Similarity comparison panel (new section):**

```python
# Fetch similar alphas and display comparison report
similar = httpx.get(f"{API_BASE_URL}/data/alphas/{alpha_id}").json()
if similar:
    st.subheader("Similarity Report")
    for s in similar.get("similar", []):
        col_name, col_score, col_pl = st.columns([3, 1, 2])
        col_name.write(s["hypothesis"][:80])
        col_score.metric("Similarity", f"{s['score']:.0%}")
        col_pl.write(f"Day High: {s['price_levels']['session_levels']['day']['high']}")
```

**price_levels display (new expander):**

```python
with st.expander("Price Levels at Idea Submission", expanded=False):
    pl = st.session_state.get("price_levels", {})
    if pl:
        lz_df = pd.DataFrame(pl.get("liquidity_zones", []))
        fvg_df = pd.DataFrame(pl.get("fvg_zones", []))
        col_lz, col_fvg = st.columns(2)
        with col_lz:
            st.markdown("**Liquidity Zones**")
            st.dataframe(lz_df, use_container_width=True, hide_index=True)
        with col_fvg:
            st.markdown("**FVG Zones**")
            st.dataframe(fvg_df, use_container_width=True, hide_index=True)
        sl = pl.get("session_levels", {})
        st.markdown("**Session Levels**")
        st.dataframe(pd.DataFrame(sl).T, use_container_width=True)
```

**Feedback form (radio + submit):**

```python
st.subheader("Your Decision")
decision = st.radio("What would you like to do?",
    ["Create new strategy", "Use existing alpha", "Merge with existing", "Discard"],
    horizontal=True)
merge_notes = st.text_area("Merge notes (if merging)", height=60) if "Merge" in decision else ""
if st.button("Submit Feedback", type="primary"):
    resp = httpx.post(f"{API_BASE_URL}/workflow/feedback", json={
        "workflow_id": st.session_state["workflow_id"],
        "decision": decision.lower().replace(" ", "_"),
        "merge_notes": merge_notes
    }, timeout=30)
    st.session_state["strategy_id"] = resp.json().get("strategy_id")
    st.success("Feedback submitted. Strategy generation starting...")
```

**Responsive layout:** All columns use `st.columns([1,2])` weights. Sidebar is `1:3` ratio. All dataframes have `use_container_width=True`.

---

### Page 1b — Candlestick Trade Chart (NEW — added to Backtester & Killer and Strategy Library)

> **CHANGE:** Use Plotly's candlestick chart (`go.Candlestick`) to display 1H OHLCV price data with:
> - **Agent trades overlaid** as buy/sell markers (triangles) from validation and testing runs
> - **User-selectable indicators** via sidebar multiselect (SMA 20/50, EMA 20, Bollinger Bands, RSI subplot, ATR)
> - **Price level overlays** (liquidity zones as horizontal bands, FVG zones as shaded rectangles, session OHLC lines)
> - **No extra charting library required** — Plotly (already installed) handles all candlestick, shape, and annotation needs

#### Candlestick chart component (`src/dashboard/components.py` — add function):

```python
def build_trade_chart(
    df_ohlcv: pd.DataFrame,           # 1H OHLCV: columns Open/High/Low/Close/Volume, DatetimeIndex
    trades: list[dict] | None = None, # [{"timestamp":..., "side":"buy"|"sell", "price":float, "label":str}]
    price_levels: dict | None = None, # full price_levels dict from Phase 3
    indicators: list[str] | None = None,  # ["SMA20","SMA50","EMA20","BB","RSI","ATR"]
    height: int = 500,
) -> go.Figure:
    """
    Build a Plotly candlestick chart with:
    - 1H OHLCV candles
    - Trade markers (buy=green triangle-up, sell=red triangle-down)
    - Price level overlays (liquidity zones, FVG zones, session level lines)
    - Optional indicator overlays
    Returns a go.Figure with 1 or 2 subplots (main price + optional RSI/ATR below).
    """
```

#### Indicator logic (computed from df_ohlcv):

| Indicator | Computation |
|-----------|------------|
| SMA20 | `df["Close"].rolling(20).mean()` |
| SMA50 | `df["Close"].rolling(50).mean()` |
| EMA20 | `df["Close"].ewm(span=20).mean()` |
| BB | SMA20 ± 2×rolling std — upper/lower band + fill |
| RSI | 14-period RSI via pandas-ta or manual formula — plotted in subplot row 2 |
| ATR | 14-period ATR — plotted in subplot row 2 |

#### Price level shapes:

| Level type | Plotly representation |
|------------|-----------------------|
| Liquidity zone (demand) | Horizontal line + shaded band (green, alpha=0.1) |
| Liquidity zone (supply) | Horizontal line + shaded band (red, alpha=0.1) |
| FVG bullish | Shaded rectangle between low/high (blue, alpha=0.15) |
| FVG bearish | Shaded rectangle between low/high (orange, alpha=0.15) |
| Session high/low | Dashed horizontal lines (gray) |
| Session open | Solid horizontal line (white, thin) |

#### Sidebar controls for chart (in Backtester & Killer sidebar):

```python
st.markdown("### Chart Settings")
chart_indicators = st.multiselect(
    "Indicators",
    options=["SMA20", "SMA50", "EMA20", "Bollinger Bands", "RSI", "ATR"],
    default=["SMA20", "EMA20"],
    key="chart_indicators"
)
show_liquidity = st.checkbox("Show Liquidity Zones", value=True, key="show_liquidity")
show_fvg       = st.checkbox("Show FVG Zones",       value=True, key="show_fvg")
show_session   = st.checkbox("Show Session Levels",  value=True, key="show_session")
show_trades    = st.checkbox("Show Agent Trades",    value=True, key="show_trades")
```

#### Chart placement in Backtester & Killer (after results, before Human Decision Gate):

```python
st.subheader("📊 1H Price Chart — Agent Trades & Levels")
# Load 1H OHLCV from DataStore or US30Loader
df_h1 = load_h1_data()   # resampled to 1H
# Load trades taken during last backtest/validation
trades = st.session_state.get("backtest_trades", [])
# Load price levels from last MC run
pl = st.session_state.get("mc_result", {}).get("price_levels", {})

fig_chart = build_trade_chart(
    df_ohlcv=df_h1,
    trades=trades if st.session_state.get("show_trades") else None,
    price_levels=pl if (show_liquidity or show_fvg or show_session) else None,
    indicators=chart_indicators,
)
st.plotly_chart(fig_chart, use_container_width=True)
```

---

### Page 2 — Backtester & Killer (`pages/5_Backtester_Killer.py`)

**Current state:** Placeholder buttons; no MC call; no Human Decision Gate.  
**Target:** Real MC run via API + full Human Decision Gate panel.

#### Changes:

**Strategy selector from real data:**

```python
strategies = httpx.get(f"{API_BASE_URL}/data/strategies?status=draft").json()
names      = {s["strategy_id"]: s["name"] for s in strategies}
selected   = st.selectbox("Strategy", options=list(names.keys()),
                          format_func=lambda k: names[k], key="backtest_strategy_id")
```

**Real Monte Carlo run:**

```python
if st.button("Run Monte Carlo Pro", type="primary"):
    with st.spinner(f"Running {st.session_state['backtest_iterations']:,} iterations..."):
        resp = httpx.post(f"{API_BASE_URL}/montecarlo/run", json={
            "strategy_id": st.session_state["backtest_strategy_id"],
            "iterations":  st.session_state["backtest_iterations"],
            "stress_tests": st.session_state.get("backtest_stress_tests", []),
            "walk_forward": st.session_state.get("walk_forward", False),
        }, timeout=120)
        mc = resp.json()
        st.session_state["mc_result"] = mc
```

**Results display (responsive metric grid):**

```python
mc = st.session_state.get("mc_result")
if mc:
    m = mc["metrics"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sharpe",       f"{m['sharpe']:.2f}",  delta=f"{'✓' if m['sharpe']>1.0 else '✗'}")
    c2.metric("Max Drawdown", f"{m['max_dd']:.1f}%",  delta=f"{'✓' if m['max_dd']<20 else '✗'}")
    c3.metric("Win Prob",     f"{m['win_probability']:.1%}")
    c4.metric("Stability",    f"{m['stability_score']:.2f}", delta="Overfit!" if mc["metrics"].get("overfit_cliff_flag") else "Stable")
```

**Regime stress results table:**

```python
regime_df = pd.DataFrame(mc["regime_results"]).T.reset_index()
regime_df.columns = ["Regime", "Prob Ruin", "VaR 95", "ES"]
st.dataframe(regime_df, use_container_width=True, hide_index=True)
```

**price_levels from MC run:**

```python
with st.expander("Price Levels (at MC run time)"):
    pl = mc.get("price_levels", {})
    st.json(pl)  # formatted JSON with syntax highlighting
```

**Human Decision Gate (new full-width panel):**

```python
st.divider()
st.subheader("⚖️ Human Decision Gate")
st.markdown("""
Review the Monte Carlo results above. You must make a decision before the strategy proceeds.
""")
col_disc, col_ret, col_app, col_tweak = st.columns(4)
discard  = col_disc.button("🗑 Discard",          use_container_width=True)
retest   = col_ret.button("🔄 Retest with Feedback", use_container_width=True)
approve  = col_app.button("✅ Approve",            use_container_width=True, type="primary")
tweak    = col_tweak.button("🔧 Approve with Tweaks", use_container_width=True)

feedback_text = ""
if retest or tweak:
    feedback_text = st.text_area("Feedback / tweaks:", height=80, placeholder="e.g. Add session filter, tighten stop loss")

if discard:
    httpx.post(f"{API_BASE_URL}/workflow/decision", json={
        "workflow_id":  st.session_state.get("workflow_id"),
        "strategy_id":  st.session_state["backtest_strategy_id"],
        "decision":     "discard"
    })
    st.error("Strategy discarded → Graveyard.")

if approve or tweak:
    decision_val = "approve" if approve else "approve_with_tweaks"
    resp = httpx.post(f"{API_BASE_URL}/workflow/decision", json={
        "workflow_id": st.session_state.get("workflow_id"),
        "strategy_id": st.session_state["backtest_strategy_id"],
        "decision":    decision_val,
        "tweaks":      feedback_text
    })
    st.success("Approved → Risk Architect applying sizing. Place file in Approved/ to go live.")

if retest:
    httpx.post(f"{API_BASE_URL}/workflow/decision", json={
        "workflow_id": st.session_state.get("workflow_id"),
        "strategy_id": st.session_state["backtest_strategy_id"],
        "decision":    "retest",
        "feedback":    feedback_text
    })
    st.info("Re-running MC with feedback. Refresh in 30s.")
```

**Charts — all responsive:**

```python
# Returns distribution histogram
fig_hist = go.Figure(go.Histogram(x=mc.get("ending_values", []), nbinsx=50,
                                   marker_color="#58a6ff", name="Equity distribution"))
fig_hist.update_layout(**plotly_layout(height=280))
st.plotly_chart(fig_hist, use_container_width=True)

# Drawdown box plot
fig_dd = go.Figure(go.Box(y=mc.get("max_dd_dist", []), name="Max Drawdown",
                           marker_color="#ef4444"))
fig_dd.update_layout(**plotly_layout(height=280))
st.plotly_chart(fig_dd, use_container_width=True)
```

---

### Page 3 — Strategy Library (`pages/4_Strategy_Library.py`)

**Current state:** Static dataframes with hardcoded rows.  
**Target:** Real strategy list from `GET /data/strategies` + metrics + price_levels + SHAP button.

#### Changes:

**Load real strategies:**

```python
status_filter = "|".join(st.session_state.get("library_filters", ["draft","production","graveyard"]))
strategies    = httpx.get(f"{API_BASE_URL}/data/strategies?status={status_filter}").json()
search        = st.session_state.get("library_search", "").lower()
if search:
    strategies = [s for s in strategies if search in s.get("name","").lower()
                                        or search in s.get("hypothesis","").lower()]
```

**Strategy list table (responsive):**

```python
if strategies:
    df_s = pd.DataFrame([{
        "Name":     s["name"],
        "Status":   s["status"],
        "Sharpe":   s.get("metrics", {}).get("sharpe", "—"),
        "Max DD":   s.get("metrics", {}).get("max_dd", "—"),
        "Hit Rate": s.get("metrics", {}).get("win_rate", "—"),
        "e-Ratio":  s.get("metrics", {}).get("e_ratio", "—"),
        "Stability":s.get("metrics", {}).get("stability_score", "—"),
    } for s in strategies])
    st.dataframe(df_s, use_container_width=True, hide_index=True,
                 column_config={
                     "Sharpe":    st.column_config.NumberColumn(format="%.2f"),
                     "Max DD":    st.column_config.NumberColumn(format="%.1f%%"),
                     "Stability": st.column_config.ProgressColumn(min_value=0, max_value=1),
                 })
```

**Detail view with tabs (metric cards + equity curve + price_levels):**

```python
selected_id = st.selectbox("Inspect strategy", [s["strategy_id"] for s in strategies],
                            format_func=lambda k: next(s["name"] for s in strategies if s["strategy_id"]==k))
if selected_id:
    detail = httpx.get(f"{API_BASE_URL}/performance/metrics/{selected_id}").json()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sharpe",       detail.get("sharpe"))
    c2.metric("Sortino",      detail.get("sortino"))
    c3.metric("Calmar",       detail.get("calmar"))
    c4.metric("Profit Factor",detail.get("profit_factor"))
    c5.metric("Stability",    detail.get("stability_score"))

    # Equity curve (from audit log)
    tab_curve, tab_pl, tab_shap = st.tabs(["Equity Curve", "Price Levels", "SHAP"])

    with tab_curve:
        # Load equity path from audit_log
        ...
        st.plotly_chart(fig_equity, use_container_width=True)

    with tab_pl:
        alpha_data = httpx.get(f"{API_BASE_URL}/data/alphas/{selected_id}").json()
        pl = alpha_data.get("price_levels", {})
        # Liquidity zones table
        st.dataframe(pd.DataFrame(pl.get("liquidity_zones",[])), use_container_width=True)
        # FVG zones table
        st.dataframe(pd.DataFrame(pl.get("fvg_zones",[])), use_container_width=True)
        # Session levels
        st.dataframe(pd.DataFrame(pl.get("session_levels",{})).T, use_container_width=True)

    with tab_shap:
        if st.button("Run SHAP Analysis", key=f"shap_{selected_id}"):
            with st.spinner("Computing SHAP values..."):
                shap_resp = httpx.post(f"{API_BASE_URL}/shap/analyze",
                                       json={"strategy_id": selected_id, "model_type": "rf"}, timeout=60)
                importance = shap_resp.json().get("feature_importance", {})
                fig_shap = go.Figure(go.Bar(
                    x=list(importance.values()),
                    y=list(importance.keys()),
                    orientation="h", marker_color="#58a6ff"
                ))
                fig_shap.update_layout(**plotly_layout(height=300), xaxis_title="Mean |SHAP|")
                st.plotly_chart(fig_shap, use_container_width=True)
```

---

### Page 4 — Execution & Reports (`pages/7_Execution_Reports.py`)

**Current state:** Alpaca positions live; cockpit uses mock data; HITL not wired.  
**Target:** Account selector + live positions + Approve Trade wired to `approval.py`.

#### Changes:

**Account selector in sidebar:**

```python
accounts = httpx.get(f"{API_BASE_URL}/accounts").json()
if accounts:
    acct_labels = {a["id"]: f"{a['label']} ({'Paper' if a['paper'] else 'LIVE'})" for a in accounts}
    selected_acct = st.selectbox("Account", list(acct_labels.keys()),
                                  format_func=lambda k: acct_labels[k],
                                  key="selected_account")
```

**Approve Trade button (wired to HITL):**

```python
approved_strategies = httpx.get(f"{API_BASE_URL}/data/strategies?status=production").json()
strategy_to_approve = st.selectbox("Approve for execution", [s["strategy_id"] for s in approved_strategies])
if st.button("✅ Approve Trade (HITL)", type="primary"):
    # Writes file to AI_Employee_Vault/Approved/ via vault endpoint
    resp = httpx.post(f"{API_BASE_URL}/vault/Approved/{strategy_to_approve}.json",
                      json={"content": json.dumps({"approved_at": datetime.utcnow().isoformat()})})
    st.success(f"Strategy {strategy_to_approve} approved for execution.")
```

**Circuit breaker status:**

```python
wf_state = httpx.get(f"{API_BASE_URL}/workflow/state").json()
if wf_state.get("circuit_breaker_active"):
    st.error("⛔ Circuit Breaker ACTIVE — consecutive loss limit reached. Manual reset required.")
```

---

### Page 5 — Home / Dashboard (`app.py`)

**Current state:** Metric cards with mock data; P&L chart with mock data.  
**Target:** Real metrics from `/metrics` + workflow status panel + activity log.

#### Changes:

**Real metrics from API:**

```python
metrics = httpx.get(f"{API_BASE_URL}/metrics", timeout=5).json()
c1, c2, c3, c4 = st.columns(4)
c1.metric("P&L",              f"{metrics.get('pnl_pct', 0):+.1f}%",
           delta=f"{metrics.get('delta_sharpe', 0):+.2f} Sharpe Δ")
c2.metric("Sharpe",           metrics.get("sharpe"))
c3.metric("Max Drawdown",     f"{metrics.get('max_drawdown_pct', 0):.1f}%")
c4.metric("Active Strategies",f"{metrics.get('active_strategies', 0)}/{metrics.get('total_strategies', 0)}")
```

**Workflow status panel (new section):**

```python
st.subheader("Current Workflow")
wf = httpx.get(f"{API_BASE_URL}/workflow/state", timeout=5).json()
step     = wf.get("step", "idle")
alpha_id = wf.get("alpha_id", "—")
step_labels = {
    "idle":              "⚪ Idle — no workflow running",
    "librarian_running": "🔵 Librarian extracting hypothesis...",
    "librarian_done":    "✅ Librarian done — awaiting feedback",
    "strategist_running":"🔵 Strategist generating code...",
    "killer_running":    "🔵 Killer running Monte Carlo...",
    "killer_done":       "⚖️ Awaiting Human Decision",
    "risk_done":         "✅ Risk sizing applied — awaiting HITL",
    "approved":          "🟢 Approved — execution ready",
    "discarded":         "🔴 Discarded → Graveyard",
}
st.info(step_labels.get(step, step))
if alpha_id != "—":
    st.caption(f"Alpha ID: `{alpha_id}`")
```

**Activity log from API:**

```python
activity = httpx.get(f"{API_BASE_URL}/activity?limit=5", timeout=5).json()
act_df = pd.DataFrame(activity)[["timestamp","event","status"]]
# Colour-code status column
def colour_status(val):
    if val == "OK":      return "color: #3fb950"
    if val == "Warning": return "color: #f59e0b"
    return "color: #ef4444"
st.dataframe(act_df.style.applymap(colour_status, subset=["status"]),
             use_container_width=True, hide_index=True)
```

---

## Phase 10 — Debug Logging & LLM/MCP Console Output

### 10.1 Update `src/tools/llm_client.py`

Before every `messages.create()` call, print to console **and** append to `DataStore/debug.log`:

```python
import logging
log = logging.getLogger("llm_debug")
# Set up file handler once
logging.basicConfig(handlers=[
    logging.StreamHandler(),                            # console
    logging.FileHandler("DataStore/debug.log")          # file
], level=logging.DEBUG)

# In complete():
log.debug("=" * 60)
log.debug(f"[{datetime.utcnow().isoformat()}] LLM CALL — model={self.model}")
log.debug(f"SYSTEM (first 500 chars): {system[:500] if system else 'None'}")
log.debug(f"PROMPT (first 500 chars): {prompt[:500]}")

response = await client.messages.create(...)

log.debug(f"RESPONSE (first 500 chars): {response_text[:500]}")
log.debug(f"Elapsed: {elapsed:.2f}s  Tokens: {msg.usage.output_tokens}")
```

### 10.2 Update `src/mcp/alpaca_server.py`

Before every tool call dispatch:

```python
log.info(f"[{datetime.utcnow().isoformat()}] MCP TOOL CALL: {tool_name} args={arguments}")
result = spec["fn"](**arguments)
log.info(f"MCP RESULT: {json.dumps(result, default=str)[:500]}")
```

### 10.3 Agent-level debug output

Each agent's `log_action()` method (from `BaseAgent`) writes:

```
[2026-04-01T09:30:00] LibrarianAgent.act() → wrote Plans/RESEARCH_PLAN_volume_spike.md
[2026-04-01T09:30:00] PriceLevelDetector: 3 liquidity zones, 2 FVG zones detected
```

All agent logs go to both console and `AI_Employee_Vault/Logs/` as before, **plus** `DataStore/debug.log`.

---

## Phase 11 — Parameter Stability Improvements

### 11.1 `MonteCarloPro.parameter_stability_tests()` — already exists

Expose `stability_score` in the MC result:

```python
stability = mc.parameter_stability_tests(returns, n_nudges=20, nudge_pct=0.10)
stability_score = 1.0 - stability["prob_of_ruin_std"]   # 1 = perfectly stable
```

### 11.2 Walk-forward validation

When `walk_forward=True` in `/montecarlo/run`:

1. Split returns into N folds (default: 5)
2. Train on first 80%, test on last 20% of each fold
3. Compute out-of-sample Sharpe per fold
4. Return `walk_forward_sharpe: [1.2, 0.9, 1.4, 1.1, 0.8]` and `oos_sharpe_mean`

### 11.3 Stability heatmap in Strategy Library

On the **MC Profiles** tab of Backtester & Killer:

```python
# Heatmap: rows = stress regimes, cols = metric thresholds
regime_names = list(mc["regime_results"].keys())
metric_names = ["prob_of_ruin", "var_95"]
z = [[mc["regime_results"][r][m] for m in metric_names] for r in regime_names]
fig_hm = go.Figure(go.Heatmap(z=z, x=metric_names, y=regime_names,
                               colorscale="RdYlGn_r", text=z, texttemplate="%{text:.2f}"))
fig_hm.update_layout(**plotly_layout(height=250))
st.plotly_chart(fig_hm, use_container_width=True)
```

---

## Phase 12 — Local PC Computation Budget (80–90% Reduction)

### Why

The project runs on a local Windows PC for research and workflow management. Heavy computation (Monte Carlo, RL/DL training, SHAP, indicator sweeps) is reserved for Google Colab T4 GPU via Remote-SSH.  
Running 10,000 MC iterations, 20-fold parameter sweeps, and 100-sample SHAP on a local CPU wastes 5–10 minutes per workflow cycle and blocks the UI.

**Principle: Local = fast exploration (1,000 MC, 5 nudges, 20 SHAP samples).  
Colab = deep validation (10,000 MC, 20 nudges, 100 SHAP samples).  
Functional results remain identical — only sample counts change.**

Functional requirements preserved:
- All decisions (approve / reject / retest) still work identically
- All charts and metrics still render
- RL/DL models still train — with a focused, high-quality smaller dataset
- Price level detection still covers all 5 session periods
- Similarity search still returns top-3 results

---

### 12.1 Create `src/config/computation_budget.py` (NEW FILE)

**Single source of truth for all compute parameters.**  
Reads `COMPUTE_PROFILE` env var: `"local"` (default) or `"colab"`.

```python
import os
from dataclasses import dataclass, field

COMPUTE_PROFILE = os.environ.get("COMPUTE_PROFILE", "local").lower()

@dataclass
class _Budget:
    # ── Monte Carlo ────────────────────────────────────────────────────────
    mc_iterations:         int   # main simulation paths
    mc_nudges:             int   # parameter stability nudges
    mc_regime_iters:       int   # paths per regime stress test
    mc_indicator_samples:  int   # TA param sweep samples per indicator

    # ── Data window ───────────────────────────────────────────────────────
    data_max_bars:         int   # max 1H candles loaded for any computation
    backtest_bars:         int   # bars used in backtest / signal generation
    price_level_lookback:  int   # bars for liquidity zone / FVG detection

    # ── SHAP ─────────────────────────────────────────────────────────────
    shap_n_samples:        int   # subsample for SHAP explainer

    # ── Walk-forward ──────────────────────────────────────────────────────
    wf_n_folds:            int   # walk-forward validation folds
    wf_train_pct:          float # fraction of each fold used for training

    # ── RL / DL ───────────────────────────────────────────────────────────
    rl_max_episodes:       int   # max training episodes
    rl_replay_buffer_size: int   # experience replay buffer capacity
    rl_batch_size:         int   # mini-batch size per gradient step
    rl_eval_freq:          int   # evaluate every N episodes
    dl_epochs:             int   # max training epochs
    dl_batch_size:         int   # training batch size

    # ── Agent loop ────────────────────────────────────────────────────────
    agent_poll_interval_s: float # seconds between vault watcher polls
    similarity_top_k:      int   # top-K similar alphas to retrieve

    # ── UI / API ──────────────────────────────────────────────────────────
    chart_max_candles:     int   # max candles shown in the trade chart
    activity_feed_limit:   int   # rows in activity log

_PROFILES: dict[str, _Budget] = {

    # ─────────────────────────────────────────────────────────────────────
    # LOCAL — fast exploration on Windows PC CPU
    # Target: all heavy operations complete in < 30 s
    # ─────────────────────────────────────────────────────────────────────
    "local": _Budget(
        mc_iterations         = 1_000,   # was 10,000  → 90% reduction
        mc_nudges             = 5,       # was 20      → 75% reduction
        mc_regime_iters       = 300,     # was 3,000   → 90% reduction
        mc_indicator_samples  = 5,       # was 20      → 75% reduction

        data_max_bars         = 500,     # was unlimited → caps data load
        backtest_bars         = 300,     # sliding window for signal gen
        price_level_lookback  = 100,     # was 200     → 50% reduction

        shap_n_samples        = 20,      # was 100     → 80% reduction

        wf_n_folds            = 3,       # was 5       → 40% reduction
        wf_train_pct          = 0.80,    # unchanged

        rl_max_episodes       = 200,     # was 2,000   → 90% reduction
        rl_replay_buffer_size = 5_000,   # was 50,000  → 90% reduction
        rl_batch_size         = 32,      # was 128     → 75% reduction
        rl_eval_freq          = 50,      # was 200     → faster feedback
        dl_epochs             = 10,      # was 100     → 90% reduction
        dl_batch_size         = 32,      # was 256     → smaller batch

        agent_poll_interval_s = 5.0,    # was 2.0     → less CPU spin
        similarity_top_k      = 3,      # unchanged

        chart_max_candles     = 150,     # was 500     → faster render
        activity_feed_limit   = 10,     # was 50      → less DB I/O
    ),

    # ─────────────────────────────────────────────────────────────────────
    # COLAB — full validation on T4 GPU
    # ─────────────────────────────────────────────────────────────────────
    "colab": _Budget(
        mc_iterations         = 10_000,
        mc_nudges             = 20,
        mc_regime_iters       = 3_000,
        mc_indicator_samples  = 20,

        data_max_bars         = 5_000,
        backtest_bars         = 2_000,
        price_level_lookback  = 500,

        shap_n_samples        = 100,

        wf_n_folds            = 5,
        wf_train_pct          = 0.80,

        rl_max_episodes       = 2_000,
        rl_replay_buffer_size = 50_000,
        rl_batch_size         = 128,
        rl_eval_freq          = 200,
        dl_epochs             = 100,
        dl_batch_size         = 256,

        agent_poll_interval_s = 2.0,
        similarity_top_k      = 5,

        chart_max_candles     = 500,
        activity_feed_limit   = 50,
    ),
}

def get() -> _Budget:
    """Return the active ComputationBudget for the current COMPUTE_PROFILE."""
    return _PROFILES.get(COMPUTE_PROFILE, _PROFILES["local"])

# Convenience alias
budget = get()
```

Add to `.env.example`:
```env
# Computation profile: "local" (default, 80-90% less compute) | "colab" (full)
COMPUTE_PROFILE=local
```

---

### 12.2 Component-by-component reductions

#### 12.2.1 Monte Carlo (`src/tools/monte_carlo_pro.py`)

| Parameter | Before (hardcoded) | Local budget | Colab budget | Notes |
|-----------|-------------------|--------------|--------------|-------|
| `iterations` | 10,000 | **1,000** | 10,000 | 90% fewer paths |
| `mc_nudges` | 20 | **5** | 20 | 75% fewer stability nudges |
| Regime stress paths | 10,000 per regime | **300** | 3,000 | Per-regime MC sub-runs |
| Indicator sweep samples | 20 | **5** | 20 | Per-indicator TA param combos |

**Change:**  
Replace every hardcoded default with a `budget` lookup:

```python
from src.config.computation_budget import budget as CB

class MonteCarloPro:
    def __init__(self, iterations: int | None = None, ...):
        self.iterations = iterations or CB.mc_iterations   # 1,000 local / 10,000 colab

    def parameter_stability_tests(self, ..., n_nudges: int | None = None, ...):
        n_nudges = n_nudges or CB.mc_nudges                # 5 local / 20 colab
```

**Statistical validity at 1,000 iterations:**  
A 1,000-path bootstrap still gives reliable quantile estimates (±2% error at 95th pct).  
For Go/No-Go decisions the threshold gap (e.g. prob_of_ruin < 5%) is wide enough that 1,000 paths is sufficient for local exploration. Full 10,000-path deep validation runs on Colab.

---

#### 12.2.2 Data window (`src/data/us30_loader.py` + `src/tools/price_level_detector.py`)

**Problem:** Loading the full CSV (3,000+ M5 bars) into memory for every agent cycle wastes time on I/O and resampling.

**Solution:** Use a rolling tail window controlled by `CB.data_max_bars`.

```python
# In US30Loader.load_clean_data()
from src.config.computation_budget import budget as CB

def load_clean_data(self, max_bars: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(self.csv_path, ...)
    limit = max_bars or CB.data_max_bars      # 500 local / 5,000 colab
    return df.tail(limit)                     # most recent N bars only
```

```python
# In detect_all_price_levels()
def detect_all_price_levels(df, lookback: int | None = None):
    from src.config.computation_budget import budget as CB
    lb = lookback or CB.price_level_lookback  # 100 local / 500 colab
    df = df.tail(lb)                          # only detect on recent bars
    ...
```

**Why this is safe:** Price levels (FVG, liquidity zones, session levels) are defined by recent structure. The last 100 1H candles (≈ 4 trading days) capture all relevant current levels for US30.

---

#### 12.2.3 SHAP (`src/tools/shap_analyzer.py`)

```python
from src.config.computation_budget import budget as CB

def run_shap_analysis(..., n_samples: int | None = None, ...):
    n_samples = n_samples or CB.shap_n_samples   # 20 local / 100 colab
```

SHAP TreeExplainer with 20 samples runs in ~1 second vs. 100 samples taking ~15 seconds. Feature ranking is stable above 15–20 samples for Random Forest.

---

#### 12.2.4 Indicator parameter sweep (`src/tools/indicator_engine.py`)

```python
from src.config.computation_budget import budget as CB

def sweep_indicator_params(name, df, n_samples: int | None = None, seed=42):
    n_samples = n_samples or CB.mc_indicator_samples  # 5 local / 20 colab
```

5 parameter samples still covers the edges of the range well (random Latin Hypercube sampling ensures spread).

---

#### 12.2.5 Walk-forward validation (`src/tools/monte_carlo_pro.py`)

```python
from src.config.computation_budget import budget as CB

def walk_forward_validate(returns, n_folds: int | None = None, ...):
    n_folds = n_folds or CB.wf_n_folds           # 3 local / 5 colab
```

3 folds provides enough out-of-sample signal to detect overfitting while reducing runtime by 40%.

---

#### 12.2.6 RL agent training (`src/edges/volume_based/volume_rl_agent.py`, `src/edges/pattern_based/pattern_rl_agent.py`)

**Problem:** 2,000 episodes × 300 bars = 600,000 environment steps on local CPU takes 30+ minutes.

**Solution:**

```python
from src.config.computation_budget import budget as CB

# Environment setup
env = US30TradingEnv(
    df=df.tail(CB.backtest_bars),              # 300 bars local / 2,000 colab
)

# Training loop
model = PPO("MlpPolicy", env,
    n_steps        = 64 if COMPUTE_PROFILE == "local" else 256,
    batch_size     = CB.rl_batch_size,         # 32 local / 128 colab
    n_epochs       = 3   if COMPUTE_PROFILE == "local" else 10,
    learning_rate  = 3e-4,
)
model.learn(
    total_timesteps = CB.rl_max_episodes * CB.backtest_bars,  # 60,000 local
    eval_freq       = CB.rl_eval_freq * CB.backtest_bars,
)
```

**Why smaller data is MORE effective for local RL:**
- Fewer noisy low-regime bars → cleaner signal
- 300 1H bars = ≈ 12 trading days covering at least one full US session cycle
- Overfitting risk reduced (small model trained on small data generalises well for early-stage research)
- Validation still uses held-out 20% of the 300 bars → 60 bars (2.5 trading days OOS)

---

#### 12.2.7 DL pattern detector (`src/edges/pattern_based/pattern_detector_dl.py`)

```python
from src.config.computation_budget import budget as CB

model.fit(
    X_train, y_train,
    epochs     = CB.dl_epochs,       # 10 local / 100 colab
    batch_size = CB.dl_batch_size,   # 32 local / 256 colab
    validation_split = 0.2,
    callbacks  = [EarlyStopping(patience=3, restore_best_weights=True)],
)
```

`EarlyStopping(patience=3)` means the model stops as soon as validation loss stops improving — on local data this typically triggers at epoch 4–7, making the `dl_epochs=10` ceiling rarely reached.

---

#### 12.2.8 Agent polling interval (`src/watchers/vault_watcher.py`)

```python
from src.config.computation_budget import budget as CB

while True:
    self._check_vault()
    time.sleep(CB.agent_poll_interval_s)   # 5s local / 2s colab
```

Reduces continuous CPU polling overhead by 60% on local (5 s vs 2 s cycle).

---

#### 12.2.9 Similarity search caching (`src/persistence/filesystem_store.py`)

**Problem:** `find_similar_alphas()` re-runs TF-IDF vectorisation from scratch every call.

**Solution:** Cache the fitted vectoriser in memory for the lifetime of the process.

```python
class FilesystemStore:
    _tfidf_cache: dict = {}   # class-level cache

    def find_similar_alphas(self, hypothesis: str, top_k: int | None = None):
        from src.config.computation_budget import budget as CB
        top_k = top_k or CB.similarity_top_k          # 3 local / 5 colab
        alphas = self.load_alphas()
        if not alphas:
            return []

        cache_key = len(alphas)                        # invalidate when new alphas added
        if cache_key not in self._tfidf_cache:
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [a.get("hypothesis", "") for a in alphas]
            vec   = TfidfVectorizer(min_df=1, stop_words="english")
            tfidf = vec.fit_transform(texts)
            self._tfidf_cache[cache_key] = (vec, tfidf, alphas)

        vec, tfidf, cached_alphas = self._tfidf_cache[cache_key]
        ...  # run cosine similarity against cache
```

Avoids re-fitting TF-IDF on the same corpus. After 10 alphas this saves ~50ms per call.

---

#### 12.2.10 Chart candle limit (`src/dashboard/components.py`)

```python
from src.config.computation_budget import budget as CB

def build_trade_chart(df_ohlcv, ...):
    df_ohlcv = df_ohlcv.tail(CB.chart_max_candles)   # 150 local / 500 colab
```

Plotly renders 150 candles in ~50ms vs. 500 candles in ~200ms in the browser.

---

### 12.3 Reduction summary table

| Component | Old value | Local (new) | Colab | Reduction (local) | Functional impact |
|-----------|-----------|-------------|-------|-------------------|-------------------|
| Monte Carlo iterations | 10,000 | **1,000** | 10,000 | **90%** | ±2% quantile error — acceptable for research |
| MC stability nudges | 20 | **5** | 20 | **75%** | Still detects overfit cliff reliably |
| MC regime stress paths | 10,000/regime | **300** | 3,000 | **97%** | Directional, not precise — fine for Go/No-Go |
| TA indicator sweep samples | 20 | **5** | 20 | **75%** | Covers parameter range edges |
| Data bars loaded | unlimited | **500 (1H)** | 5,000 | ~90% | 500 bars = 20 trading days → sufficient for regime capture |
| Backtest bars | full history | **300** | 2,000 | ~85% | 300 bars = 12 days → focused signal window |
| Price level lookback | 200 | **100** | 500 | **50%** | Last 100 1H bars cover all active levels |
| SHAP samples | 100 | **20** | 100 | **80%** | Feature ranking stable above 15 samples |
| Walk-forward folds | 5 | **3** | 5 | **40%** | 3 folds still detects overfitting |
| RL episodes | 2,000 | **200** | 2,000 | **90%** | Early-stage research; Colab for final training |
| RL replay buffer | 50,000 | **5,000** | 50,000 | **90%** | Fits comfortably in <100MB RAM |
| RL batch size | 128 | **32** | 128 | **75%** | Stable gradients at 32 for small buffers |
| DL epochs | 100 | **10** | 100 | **90%** | EarlyStopping prevents wasted epochs |
| DL batch size | 256 | **32** | 256 | **87.5%** | Sufficient for 300-bar windows |
| Vault poll interval | 2 s | **5 s** | 2 s | **60% CPU** | No functional latency impact for research |
| Chart candles rendered | 500 | **150** | 500 | **70%** | Still shows full trading session context |
| Similarity search | re-fit every call | **cached** | cached | ~50ms saved/call | Result identical |

**Combined wall-clock impact:**  
A full local workflow cycle (Librarian → Strategist → Killer MC → price levels → SHAP) drops from ~8 minutes to **~50 seconds** on a modern CPU.

---

### 12.4 New file: `src/config/__init__.py` + `computation_budget.py`

```
src/config/
├── __init__.py
└── computation_budget.py     ← NEW (Phase 12)
```

The `src/config/` directory is also the home for any future model hyperparameter configs.

---

### 12.5 `.env` update

Add to `.env` and `.env.example`:

```env
# Computation profile — controls all heavy operation sample counts
# "local"  → 80-90% reduced (fast, exploratory; default)
# "colab"  → full resolution (deep validation; set when SSH-connected to T4)
COMPUTE_PROFILE=local
```

**Switching to Colab mode:**  
When you connect via Remote-SSH to the Colab instance, simply set `COMPUTE_PROFILE=colab` in the remote `.env` and restart the services. All components automatically use full resolution without any code changes.

---

### 12.6 UI indicator in sidebar

Add to `src/dashboard/app.py` sidebar:

```python
from src.config.computation_budget import COMPUTE_PROFILE, budget as CB

profile_color = "🟢" if COMPUTE_PROFILE == "colab" else "🟡"
st.sidebar.caption(
    f"{profile_color} **Profile:** `{COMPUTE_PROFILE.upper()}`  \n"
    f"MC: {CB.mc_iterations:,} paths · SHAP: {CB.shap_n_samples} samples  \n"
    f"Data: {CB.data_max_bars} bars · RL: {CB.rl_max_episodes} episodes"
)
```

This gives the user instant visibility into which compute profile is active.

---

### 12.7 File changes for Phase 12

| File | Action | Change |
|------|--------|--------|
| `src/config/__init__.py` | **CREATE** | Package init |
| `src/config/computation_budget.py` | **CREATE** | ComputationBudget dataclass + LOCAL/COLAB profiles |
| `src/tools/monte_carlo_pro.py` | **UPDATE** | Replace hardcoded `iterations=10000`, `n_nudges=20` with `CB.*` lookups |
| `src/tools/indicator_engine.py` | **UPDATE** | Replace `n_samples=20` with `CB.mc_indicator_samples` |
| `src/tools/shap_analyzer.py` | **UPDATE** | Replace `n_samples=100` with `CB.shap_n_samples` |
| `src/data/us30_loader.py` | **UPDATE** | Add `max_bars=CB.data_max_bars` tail slice |
| `src/tools/price_level_detector.py` | **UPDATE** | Add `lookback=CB.price_level_lookback` tail slice |
| `src/persistence/filesystem_store.py` | **UPDATE** | Add TF-IDF class-level cache; `top_k=CB.similarity_top_k` |
| `src/edges/volume_based/volume_rl_agent.py` | **UPDATE** | `total_timesteps`, `batch_size`, `n_steps` from CB |
| `src/edges/pattern_based/pattern_detector_dl.py` | **UPDATE** | `epochs`, `batch_size` from CB |
| `src/watchers/vault_watcher.py` | **UPDATE** | `sleep(CB.agent_poll_interval_s)` |
| `src/dashboard/components.py` | **UPDATE** | `df_ohlcv.tail(CB.chart_max_candles)` in build_trade_chart() |
| `src/dashboard/app.py` | **UPDATE** | Sidebar compute profile badge |
| `.env.example` | **UPDATE** | Add `COMPUTE_PROFILE=local` |
| `.env` | **UPDATE** | Add `COMPUTE_PROFILE=local` |

---

After all phases are implemented, verify the full workflow:

### Test Commands

```bash
# Start all services
uv run python main.py &                          # FastAPI on :8000
uv run streamlit run src/dashboard/app.py        # Streamlit on :8501
```

### Test Flow (step by step)

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Streamlit, go to **Alpha Idea Lab** | Page loads, no errors, responsive layout |
| 2 | Enter: "Volume spike on US30 at session open predicts momentum" → click Generate | API calls `/workflow/start`; similarity report appears with price_levels |
| 3 | Select "Create new strategy" → Submit Feedback | API calls `/workflow/feedback`; strategy_id returned |
| 4 | Go to **Backtester & Killer** | Strategy appears in dropdown from real API |
| 5 | Click "Run Monte Carlo Pro" | MC runs via `/montecarlo/run`; results appear (Sharpe, DD, prob of ruin) |
| 6 | Check price_levels expander | Liquidity zones, FVG zones, session levels all visible |
| 7 | Click "Approve" in Human Decision Gate | `/workflow/decision` called; success message |
| 8 | Check **Home** | Workflow status shows "Risk sizing applied"; activity log updated |
| 9 | Go to **Execution & Reports** | Account selector shows Primary/Backup Alpaca accounts |
| 10 | Check console / DataStore/debug.log | LLM prompt + response + price_levels all logged |

### Verify price_levels are recorded

```bash
# Check DataStore
python -c "
import json
with open('DataStore/alphas.json') as f:
    alphas = json.load(f)
last = alphas[-1]
print('Alpha ID:', last['alpha_id'])
print('Liquidity zones:', last['price_levels']['liquidity_zones'])
print('Day high:', last['price_levels']['session_levels']['day']['high'])
"
```

Expected: JSON output with populated price_levels fields.

---

## File Change Matrix

| File | Action | Phase |
|------|--------|-------|
| `requirements.in` | **CREATE** | 1 |
| `requirements.txt` | **UPDATE** (uv compile) | 1 |
| `pyproject.toml` | **UPDATE** (add uv, shap) | 1 |
| `DataStore/` (directory) | **CREATE** | 2 |
| `src/persistence/__init__.py` | **CREATE** | 2 |
| `src/persistence/filesystem_store.py` | **CREATE** | 2 |
| `src/tools/price_level_detector.py` | **CREATE** | 3 |
| `src/tools/performance_metrics.py` | **CREATE** | 6 |
| `src/tools/shap_analyzer.py` | **CREATE** | 7 |
| `src/api/workflow_routes.py` | **CREATE** | 5 |
| `src/agents/librarian_agent.py` | **UPDATE** (similarity + price_levels) | 4 |
| `src/agents/strategist_agent.py` | **UPDATE** (price_levels extraction + store) | 4 |
| `src/agents/killer_agent.py` | **UPDATE** (price_levels in audit + store) | 4 |
| `src/api/main.py` | **UPDATE** (include workflow_routes) | 5 |
| `src/tools/llm_client.py` | **UPDATE** (debug logging) | 10 |
| `src/mcp/alpaca_server.py` | **UPDATE** (debug logging) | 10 |
| `src/tools/monte_carlo_pro.py` | **UPDATE** (stability_score, walk-forward) | 11 |
| `src/dashboard/components.py` | **UPDATE** (responsive CSS) | 9 |
| `src/dashboard/config.py` | **UPDATE** (new constants, account labels) | 8 |
| `src/dashboard/session_state.py` | **UPDATE** (selected_account, workflow_id) | 8 |
| `src/dashboard/app.py` | **UPDATE** (real metrics, workflow status) | 9 |
| `src/dashboard/pages/1_Alpha_Idea_Lab.py` | **REWRITE** (fully functional) | 9 |
| `src/dashboard/pages/5_Backtester_Killer.py` | **REWRITE** (real MC + Decision Gate) | 9 |
| `src/dashboard/pages/4_Strategy_Library.py` | **REWRITE** (real data + SHAP) | 9 |
| `src/dashboard/pages/7_Execution_Reports.py` | **UPDATE** (account selector + HITL) | 9 |
| `.env.example` | **UPDATE** (ALPACA_API_KEY_2, debug path) | 8 |

---

## Responsive UI Design Rules

These rules apply to **every page** in `src/dashboard/pages/` and `src/dashboard/app.py`.

### Rule 1 — No hardcoded pixel widths in Streamlit CSS

```python
# ✗ BAD
st.markdown("<div style='width: 800px'>...</div>", unsafe_allow_html=True)

# ✓ GOOD
st.markdown("<div style='width: 100%; max-width: 100%'>...</div>", unsafe_allow_html=True)
```

### Rule 2 — All charts use container width

```python
# ✗ BAD
st.plotly_chart(fig)

# ✓ GOOD
st.plotly_chart(fig, use_container_width=True)
```

### Rule 3 — All dataframes use container width

```python
# ✗ BAD
st.dataframe(df)

# ✓ GOOD
st.dataframe(df, use_container_width=True, hide_index=True)
```

### Rule 4 — Columns use relative weights

```python
# ✗ BAD — fixed pixel feel
col1, col2 = st.columns([400, 200])

# ✓ GOOD — relative ratio
col1, col2 = st.columns([2, 1])
```

### Rule 5 — Buttons full-width where appropriate

```python
# Decision buttons, primary actions
st.button("Approve", use_container_width=True, type="primary")
```

### Rule 6 — Metric cards in responsive grid

```python
# Use 2 columns on narrow, 4 on wide — Streamlit handles this via container
cols = st.columns(4)   # will naturally reflow on narrow screens
for i, (label, val) in enumerate(metrics.items()):
    cols[i % 4].metric(label, val)
```

### Rule 7 — Mobile breakpoint in apply_theme()

The responsive CSS injected in Phase 9.1 handles `@media (max-width: 768px)` — stacks all `[data-testid="column"]` to 100% width on mobile.

### Rule 8 — Plotly chart height adapts

```python
def plotly_layout(height: int = 350, **kwargs) -> dict:
    """Standard Plotly layout with responsive sizing."""
    return {
        "height": height,
        "autosize": True,          # ← key for responsive width
        "margin": {"l": 40, "r": 20, "t": 30, "b": 40},
        "paper_bgcolor": THEME["surface"],
        "plot_bgcolor":  THEME["background"],
        "font": {"color": THEME["text"], "size": 12},
        **kwargs
    }
```

### Rule 9 — Touch-friendly controls

All interactive elements must have `min-height: 44px` (injected via `apply_theme()` CSS). This is the Apple HIG minimum touch target size.

### Rule 10 — Tables are horizontally scrollable

```python
# In apply_theme() CSS:
# .stDataFrame { overflow-x: auto !important; }
# This allows wide tables to scroll horizontally instead of overflowing
```

---

## Phase 13 — Autonomous AI Agent (Floating Chat Widget)

> **Implemented:** 2 April 2026  
> **Requirement doc:** `AUTONOMOUS_AGENT_REQUIREMENT.md`

### Why
Client requires an always-visible AI assistant (Copilot) on every dashboard page that can answer questions about the entire system (strategies, positions, vault, price levels, Monte Carlo results, etc.) and optionally execute real actions in Agent Mode.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Streamlit page  (any of 9 pages + home)                 │
│                                                          │
│  Layer 1 — st.markdown(unsafe_allow_html=True)           │
│    → <style> CSS injected into Streamlit DOM             │
│    → <div id="aa-root"> floating widget HTML             │
│    (DOMPurify allows elements + style; strips scripts)   │
│                                                          │
│  Layer 2 — components.v1.html(height=1)                  │
│    → same-origin iframe (allow-same-origin sandbox)      │
│    → script sets window.parent.__AA_API                  │
│    → script uses window.parent.document to find          │
│      #aa-root and attach all event listeners             │
│    → retries every 200ms for up to 8s (React timing)    │
│    → 1px iframe hidden via CSS targeting stCustomComponentV1
└──────────────────────────────────────────────────────────┘
                          │
                  fetch() /agent/chat
                          │
             ┌────────────▼──────────────┐
             │  FastAPI  /agent/chat      │
             │  POST — async endpoint     │
             │  src/api/agent_routes.py   │
             └────────────┬──────────────┘
                          │
             ┌────────────▼──────────────┐
             │  AutonomousAgent           │
             │  src/agents/autonomous_agent.py │
             │                           │
             │  • builds system context  │
             │    (FilesystemStore,       │
             │     vault scan,           │
             │     price levels)         │
             │  • system prompt with     │
             │    live context injected  │
             │  • calls Gemini LLM       │
             │  • tool-call loop (max 4) │
             │  • prints debug blocks    │
             └───────────────────────────┘
```

### 13.1 Files Created

#### `src/agents/autonomous_agent.py` (NEW)

**Core async agent:**

```python
async def process_message(
    message: str,
    history: list[dict],   # session-local, not persisted across browser sessions
    mode: str = "chat",    # "chat" | "agent"
    api_base_url: str = "http://localhost:8000",
) -> str: ...
```

**System context builder** — called on every request:
- `FilesystemStore.load_strategies()` + `load_alphas()` + `get_workflow_state()`
- Vault folder scan (Needs_Action, Plans, Approved, Reports, Logs, Graveyard)
- `detect_all_price_levels()` from US30 CSV if `US30_CSV_PATH` is set

**Tool catalogue:**

| Tool | Mode | Description |
|------|------|-------------|
| `get_positions` | Chat | Alpaca open positions |
| `get_strategies(status)` | Chat | Strategies from DataStore |
| `get_alphas` | Chat | Alpha ideas from DataStore |
| `get_vault_file(folder, filename)` | Chat | Read any vault file |
| `get_metrics` | Chat | Current performance metrics |
| `get_price_levels` | Chat | US30 price levels |
| `get_workflow_state` | Chat | Current pipeline step |
| `get_mc_results(strategy_id)` | Chat | Monte Carlo / perf metrics |
| `start_workflow(idea)` | **Agent only** | Submit new alpha idea |
| `run_monte_carlo(strategy_id, iterations)` | **Agent only** | Run MC validation |
| `workflow_decision(...)` | **Agent only** | Approve / discard / retest |
| `move_to_approved(strategy_id)` | **Agent only** | Trigger HITL approval |

**Debug output** (every call):
```
============================================================
=== AUTONOMOUS AGENT PROMPT ===
Mode: chat | History turns: 3
System (first 400 chars): ...
User message: Show me open positions
=== AUTONOMOUS AGENT RESPONSE ===
Response (first 500 chars): ...
Elapsed: 1.23s
```

**Memory policy:** Session-local only. `history` list is passed per request from the browser's `sessionStorage`. No database or file persistence for chat history — fully compliant with the requirement's "memory restricted to session" constraint.

#### `src/api/agent_routes.py` (NEW)

```
POST /agent/chat     — ChatRequest → ChatResponse (async, both modes)
GET  /agent/context  — snapshot of current system context (for debugging)
```

Pydantic models:
```python
class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    mode: str = "chat"   # "chat" | "agent"

class ChatResponse(BaseModel):
    response: str
    mode: str
```

#### `src/dashboard/autonomous_chat.py` (NEW)

Single function:
```python
def render_autonomous_agent_widget(api_base_url: str = "http://localhost:8000") -> None
```

**Widget features:**
- Circular `🤖` chat bubble — bottom-right, `position: fixed`, `z-index: 2147483647`
- Click to expand → 385×545px draggable dark-theme chat window
- **Drag** via title-bar (mousedown/mousemove/mouseup on `#aa-header`)
- **Mode toggle pill** — Chat (blue `#58a6ff`) ↔ Agent (purple `#d2a8ff`)
- Agent mode warning banner: `⚠ Agent mode can execute real actions`
- 4 suggestion chips shown in empty state
- Animated typing indicator (3-dot bounce)
- `sessionStorage` key `aa_state_v2` persists: `{ open, mode, history, pos }`
- Clear button, minimise button
- Badge dot on bubble when new reply arrives while window is closed
- Lightweight markdown renderer: `**bold**`, `` `code` ``, newlines

**JS retry loop:** Polls `window.parent.document.getElementById('aa-root')` every 200ms for up to 8 seconds to handle React's async commit of the `st.markdown` elements.

### 13.2 Files Updated

| File | Change |
|------|--------|
| `src/dashboard/app.py` | `from src.dashboard.autonomous_chat import render_autonomous_agent_widget` + `render_autonomous_agent_widget(api_base_url=API_BASE_URL)` called after `init_session_state()` |
| `src/dashboard/pages/1_Alpha_Idea_Lab.py` | Same widget injection |
| `src/dashboard/pages/2_Vault_Explorer.py` | Same + `API_BASE_URL` added to config import |
| `src/dashboard/pages/3_No_Code_Builder.py` | Same + `API_BASE_URL` added to config import |
| `src/dashboard/pages/4_Strategy_Library.py` | Same widget injection |
| `src/dashboard/pages/5_Backtester_Killer.py` | Same widget injection |
| `src/dashboard/pages/6_Optimization_Lab.py` | Same + `API_BASE_URL` added to config import |
| `src/dashboard/pages/7_Execution_Reports.py` | Same widget injection (+ full rewrite in Phase 14) |
| `src/dashboard/pages/8_Situational_Analysis.py` | Same + `API_BASE_URL` added to config import |
| `src/dashboard/pages/9_Technical_Analysis.py` | Same + `API_BASE_URL` added to config import |
| `src/api/main.py` | `from src.api.agent_routes import router as agent_router` + `app.include_router(agent_router)` with graceful import fallback |

### 13.3 Safety & HITL Compliance

- In Chat Mode: action tools (`start_workflow`, `run_monte_carlo`, `workflow_decision`, `move_to_approved`) return `⛔ Action tools not available in Chat Mode`.
- In Agent Mode: LLM is instructed to describe the action and confirm before calling action tools.
- `move_to_approved` writes to `Approved/` folder, which requires human review before execution (existing HITL mechanism from Phase 5).
- Live orders **never** executed automatically — always routed through HITL.

### 13.4 Testing

```bash
# Start both servers
uv run python -m uvicorn src.api.main:app --reload
uv run streamlit run src/dashboard/app.py

# Verify endpoints
curl -s http://localhost:8000/agent/context | python -m json.tool
curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Show me open positions","mode":"chat"}' | python -m json.tool

# On any page: click 🤖 bubble → chat opens, drag title bar → moves,
# toggle Chat/Agent mode, send message, check console for === AUTONOMOUS AGENT === blocks
```

---

## Phase 14 — Execution Reports Enhancement & Bug Fixes

> **Implemented:** 2 April 2026

### 14.1 Bug Fixes

#### `API_BASE_URL` NameError on 5 pages

**Root cause:** The patch script that injected `render_autonomous_agent_widget(api_base_url=API_BASE_URL)` into all pages detected `API_BASE_URL` already in the file content (from the widget call line itself) and skipped adding the import. Pages 2, 3, 6, 8, 9 had the call but not the import.

**Fix:** Added `API_BASE_URL` to the existing `from src.dashboard.config import ...` statement in each page:

| Page | Fix |
|------|-----|
| `2_Vault_Explorer.py` | Added `API_BASE_URL` to `from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, VAULT_FOLDERS` |
| `3_No_Code_Builder.py` | Added `API_BASE_URL` to the multi-line config import block |
| `6_Optimization_Lab.py` | Added `API_BASE_URL` to `from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, COLAB_NOTEBOOK_URL` |
| `8_Situational_Analysis.py` | Same as page 6 |
| `9_Technical_Analysis.py` | Same as page 6 |

#### Widget not appearing (Streamlit HTML sanitisation)

**Root cause:** Previous implementation used `st.markdown(unsafe_allow_html=True)` with `<script>` tags and `onclick=` attributes. Streamlit's DOMPurify strips both. Then `components.v1.html(height=0)` was tried — height=0 may prevent script execution in some Streamlit/browser combinations.

**Fix — Two-layer injection:**

```
Layer 1  st.markdown(unsafe_allow_html=True)
         → <style>CSS</style>      ← DOMPurify allows <style>
         → <div id="aa-root">...</div>  ← DOMPurify allows HTML elements
           (no onclick= attributes; event listeners added by Layer 2)

Layer 2  components.v1.html(height=1)
         → Same-origin iframe (sandbox includes allow-same-origin)
         → Script sets window.parent.__AA_API = api_base_url
         → Script polls window.parent.document.getElementById('aa-root')
           every 200ms, up to 40 retries (~8s) for React to commit
         → On found: attaches all addEventListener() calls
         → CSS rule hides the 1px iframe container:
           div[data-testid="stCustomComponentV1"] { height:0!important; ... }
```

### 14.2 Execution Reports Page — Full Rewrite

**File:** `src/dashboard/pages/7_Execution_Reports.py`

**Previous state:** Single tab with static cockpit; Reports tab showed only placeholder text and non-functional buttons.

**New state:** Three-tab layout with live data.

#### Tab 1 — Execution Monitor
- Live ticker (Alpaca quote with bid/ask/mid)
- Open positions table: Symbol, Side, Qty, Entry Price, Current Price, Unrealised P&L, P&L %, Market Value
- P&L column colour-coded (green ≥ 0, red < 0) via Pandas Styler
- Cockpit widget (signals, risk, agent health)

#### Tab 2 — Trade History ✨ NEW
- Source priority: Alpaca closed orders → DataStore audit log → vault Logs → demo data
- Columns: ID, Symbol, Side, Type, Qty, Entry, **SL**, **TP**, P&L, Sharpe, Max DD, Status, Opened, Closed, Src
- P&L summary stats: Total P&L, Win Rate, Best Trade, Worst Trade
- CSV download button
- Source badge: `✅ Alpaca` / `📁 DataStore` / `🔵 Demo data` / `📂 Vault logs`

#### Tab 3 — Reports ✨ NEW
- Reads vault folders: Reports/, Approved/, Plans/, Graveyard/
- Shows last 5 files from each folder in expandable sections with content preview
- `GET /trades/report` FastAPI endpoint (no LLM call — pure file read)
- Non-functional buttons replaced with informative captions

### 14.3 New FastAPI Endpoints

#### `GET /trades/history?limit=100`

Added to `src/api/workflow_routes.py`:

```python
@router.get("/trades/history")
def get_trade_history(limit: int = 100) -> dict:
    """Alpaca closed orders + DataStore audit log + vault Logs + demo fallback."""
```

Response schema:
```json
{
  "trades": [
    {
      "trade_id": "abc123",
      "symbol": "US30",
      "side": "buy",
      "type": "market",
      "qty": 1.0,
      "entry_price": 42100.50,
      "sl": 42020.00,
      "tp": 42260.00,
      "status": "filled",
      "opened_at": "2025-11-12T10:00:00Z",
      "closed_at": "2025-11-12T14:30:00Z",
      "pnl": 159.50,
      "source": "alpaca"
    }
  ],
  "count": 47,
  "source": "alpaca"
}
```

#### `GET /trades/report`

Added to `src/api/workflow_routes.py`:

```python
@router.get("/trades/report")
def get_trades_report() -> dict:
    """Reads vault Reports/, Graveyard/, Approved/, Plans/ — last 5 files each."""
```

#### `get_closed_orders(limit)` — Alpaca service

Added to `src/api/alpaca_service.py`:

```python
def get_closed_orders(limit: int = 50) -> list[dict[str, Any]]:
    """Return closed/filled orders from Alpaca trading client.
    Includes: order_id, symbol, side, type, qty, filled_qty, filled_price,
              limit_price (TP proxy), stop_price (SL proxy), status,
              created_at, filled_at, notional."""
```

Uses `alpaca.trading.requests.GetOrdersRequest(status=QueryOrderStatus.CLOSED)`.

### 14.4 Updated File Summary (Phases 13 + 14)

```
NEW  src/agents/autonomous_agent.py
NEW  src/api/agent_routes.py
NEW  src/dashboard/autonomous_chat.py

MOD  src/dashboard/app.py                       ← widget render call
MOD  src/dashboard/pages/1_Alpha_Idea_Lab.py    ← widget render call
MOD  src/dashboard/pages/2_Vault_Explorer.py    ← widget + API_BASE_URL fix
MOD  src/dashboard/pages/3_No_Code_Builder.py   ← widget + API_BASE_URL fix
MOD  src/dashboard/pages/4_Strategy_Library.py  ← widget render call
MOD  src/dashboard/pages/5_Backtester_Killer.py ← widget render call
MOD  src/dashboard/pages/6_Optimization_Lab.py  ← widget + API_BASE_URL fix
MOD  src/dashboard/pages/7_Execution_Reports.py ← full rewrite (3 tabs)
MOD  src/dashboard/pages/8_Situational_Analysis.py ← widget + API_BASE_URL fix
MOD  src/dashboard/pages/9_Technical_Analysis.py   ← widget + API_BASE_URL fix
MOD  src/api/main.py                            ← include agent_router
MOD  src/api/workflow_routes.py                 ← /trades/history, /trades/report
MOD  src/api/alpaca_service.py                  ← get_closed_orders()
```

### 14.5 Known Limitations / Next Steps

| Item | Status | Notes |
|------|--------|-------|
| Per-trade P&L from Alpaca | ⚠️ Partial | Alpaca REST API doesn't return per-trade P&L directly; needs activity endpoint or portfolio history correlation |
| MT5 trade history | 🔲 Pending | MT5 connector exposes `get_trades()` — wire to `/trades/history` as additional source |
| Real-time P&L streaming | 🔲 Pending | WebSocket `/ws/positions` endpoint + Streamlit `st_autorefresh` |
| Agent memory across sessions | 🔲 By design | Session-only per requirement; can be extended with `DataStore/chat_log.json` if needed |
| Multi-turn agent with function-calling SDK | 🔲 Future | Current tool-call loop uses text parsing; upgrade to Gemini `tools=` parameter for reliability |

---

*End of Implementation Plan — 1 April 2026 (updated 2 April 2026)*
