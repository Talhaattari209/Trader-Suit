# Trader-Suit UI — Implementation Gap (Detailed)

This document compares **UI_Requirements.md** (the full Trader-Suit Streamlit spec) with the **current codebase** and lists everything that remains to be implemented.

---

## Executive Summary

| Area | Status | Notes |
|------|--------|--------|
| **App structure** | Partial | Single-page Cockpit only; no 8-page Trader-Suit navigation |
| **Global design** | Partial | Wide layout + dark theme exist; 1:4 sidebar ratio and session state not applied consistently |
| **Data sources** | Not implemented | Neon DB, MT5 live feed, 6-year US30 dataset not wired to UI |
| **Page 1: Home/Dashboard** | Not implemented | Spec calls for overview dashboard; current app is signals/risk/agents only |
| **Page 2: Alpha Idea Lab** | Not implemented | No prompt-based alpha entry or Librarian integration in UI |
| **Page 3: Vault Explorer** | Not implemented | No file-based Obsidian vault browser |
| **Page 4: No-Code Strategy Builder** | Not implemented | No 8-step wizard or Strategist integration in UI |
| **Page 5: Strategy Library** | Not implemented | No drafts/production/graveyard browser |
| **Page 6: Backtester & Killer** | Not implemented | No Monte Carlo Pro UI or Killer integration |
| **Page 7: Optimization Lab** | Not implemented | No PPO/Genetic/Ensemble tuning UI |
| **Page 8: Execution & Reports** | Partially aligned | Cockpit has signals/risk; no Reports tab, HITL approve, or briefings |
| **Backend API** | Mock only | `/signals`, `/risk`, `/status` return mock data; no real DB/MT5 |

---

## What Exists Today

### 1. Streamlit app (`src/dashboard/app.py`)

- **Single page** titled “Trader's Workbench — The Cockpit”.
- **Layout**: `st.set_page_config(layout="wide")`, dark theme via custom CSS.
- **Content**:
  - **Signal Monitor**: Cards for active signals (symbol, direction, strategy, confidence, countdown); data from `GET /signals`.
  - **Risk Visualizer**: VaR gauge (Plotly), drawdown progress bar, exposure pie chart; data from `GET /risk`.
  - **Agent Status**: List of agents with health/heartbeat; data from `GET /status`.
- **Sidebar**: API URL, refresh interval slider, auto-refresh toggle, “Refresh now” button.
- **No** multi-page navigation, no routing to other Trader-Suit sections.

### 2. Dashboard config (`src/dashboard/config.py`)

- `API_BASE_URL`, `REFRESH_INTERVAL_SECONDS`, `VAR_*`, `DRAWDOWN_*` thresholds.
- No theme toggle or layout ratio config.

### 3. FastAPI backend (`src/api/main.py`)

- **Endpoints**: `GET /`, `GET /status`, `GET /signals`, `GET /risk`.
- **Data**: All mock (random signals, risk, agent status). No Neon, MT5, or vault integration.
- **Models**: `Signal`, `RiskMetrics`, `AgentStatus`, `SystemStatus`.

### 4. Other Streamlit-related code

- `src/tools/discovery_lab.py`: Standalone “Discovery Lab” (What-If backtest, Regime Scanner, Feature Importance) with placeholder logic; **not** integrated into the main app.
- `src/tools/notifier.py`, `journal.py`, `deployment_optimization.py`: Import `streamlit` but are not the main UI.

### 5. Backend services (no UI integration)

- **Vault/agents**: `LibrarianAgent`, `StrategistAgent`, `KillerAgent`, `RiskArchitectAgent`, `Reporter`; vault dirs: `Needs_Action`, `Plans`, `Approved`, `Logs`, `Reports`, etc.
- **Tools**: `vault_watcher`, `monte_carlo_pro`, `failure_journal`, `instruction_router` (prompt → Needs_Action).
- **Connectors**: `market_stream` (MT5); DB handlers exist but are not used by the API.

---

## Global Design Gaps (Apply to All Pages)

| Requirement | Status | To Do |
|-------------|--------|--------|
| Layout ratio 1:4 sidebar-to-main | Not applied | Use `st.columns([1,4])` (or 1:5/1:3 where spec says) for every page. |
| Plotly for charts | Partial | Cockpit uses Plotly for VaR and pie; add Plotly everywhere spec says “Line/Bar/Heatmap” (replace any `st.line_chart` etc.). |
| Metrics color-coding | Partial | Implement green (>threshold) / red (<threshold) for Sharpe, Sortino, Max DD, Hit Rate, e-ratio. |
| Dark mode default | Done | Already in Cockpit CSS. |
| Data from Neon / MT5 / 6-year US30 | Missing | Backend + UI: add APIs and env config to pull from these sources. |
| Session state for cross-page persistence | Missing | e.g. `st.session_state.selected_strategy`, selected date range, regime filters. |
| Component count 10–20 per page | N/A | Use as guidance when implementing each page. |

---

## Page 1: Home/Dashboard — To Implement

**Purpose (from spec):** Overview of system health, performance, quick actions.

**Layout:** Sidebar 1:5 (quick filters); main = 3-row grid: metrics row → charts row → activity table.

### Components (spec total: 12) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Date Range Selector | `st.date_input` range, default last 30 days | Not implemented |
| 2–5 | 4 Metric Cards | P&L (e.g. +12.5%), Sharpe (e.g. 1.8), Max DD (e.g. -8.2%), Active Strategies (e.g. 7/10) | Not implemented (Cockpit has no P&L/Sharpe/DD/active-strategy cards) |
| 6 | Button | “New Alpha Idea” → link to Alpha Idea Lab | Not implemented (no nav) |
| 7 | Button | “View Live MT5 Feed” → real-time US30 ticker | Not implemented |
| 8 | Multiselect | Filter by regime (trending/ranging) or session (London/NY) | Not implemented |
| 9 | Expander | System Status (PM2, Neon sync, MT5 — green/red) | Partially: Agent Status exists in Cockpit; add PM2, Neon, MT5 indicators |
| 10 | Table | Recent Activity Log, 5 rows: Timestamp, Event, Status | Not implemented |
| 11–12 | 2 Alerts | `st.info` for decay warnings (e.g. “Alpha decay in Strategy Y”) | Not implemented |

### Charts (spec total: 3) — all missing

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Line (Plotly) | Cumulative P&L curve over time, full width, hover for daily returns | Not implemented |
| 2 | Bar | Regime Performance Breakdown (returns trending vs ranging), 2:1 with metrics table | Not implemented |
| 3 | Heatmap | Signal Decay Matrix (strategies × months, color by e-ratio decay) | Not implemented |

### Metrics to display (with thresholds)

- Sharpe (target >1), Sortino (>1.5), Max DD (<20%), Hit Rate (>55%), e-ratio (>1.5); delta arrows vs last week.
- **Backend:** API(s) to return performance metrics and activity log (from Neon or computed from backtester/agents).

---

## Page 2: Alpha Idea Lab — To Implement

**Purpose:** Prompt-based entry for non-coders; hypothesis extraction → RESEARCH_PLAN.

**Layout:** Sidebar 1:3 (templates/examples); main: prompt → plan preview → options expander.

### Components (spec total: 10) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Text Area | Natural language prompt (e.g. “Mean-reversion on US30 post-news”) | Not implemented |
| 2 | Button | “Generate Hypothesis” → Librarian Agent → RESEARCH_PLAN.md | Not implemented (wire to `run_instruction` / Librarian) |
| 3 | Selectbox | Template Selection (e.g. Momentum Breakout, Pattern Failure) | Not implemented |
| 4 | Multiselect | Data sources (6-year US30, Live MT5, PDF Upload) | Not implemented |
| 5 | File Uploader | Research PDFs/CSVs | Not implemented |
| 6 | Expander | Advanced Hypothesis Tweaks (e.g. regime tags: Hurst >0.5) | Not implemented |
| 7 | Markdown | Generated RESEARCH_PLAN.md preview | Not implemented |
| 8 | Button | “Proceed to Builder” (session state + nav to No-Code Builder) | Not implemented |
| 9 | Progress Bar | Agent processing (if async) | Not implemented |
| 10 | Alert | `st.warning` if redundancy detected (Neon check) | Not implemented |

### Charts (spec total: 1)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Scatter | Initial data preview (e.g. US30 price vs volume) | Not implemented |

### Metrics

- Initial e-ratio estimate (>1.2), regime-specific returns (e.g. +5% in high-vol). **Backend:** quick-scan endpoint or use existing data APIs.

---

## Page 3: Vault Explorer — To Implement

**Purpose:** File-based interaction with Obsidian_Vault (Needs_Action, Plans, Approved, Reports, Logs).

**Layout:** Sidebar 1:4 (folder tree); main 1:1 — file list | preview pane.

### Components (spec total: 11) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Tree / expander | Folders: Needs_Action, Plans, Approved, Reports, Logs | Not implemented |
| 2 | Search | Filter files by name/hypothesis | Not implemented |
| 3 | Table | File list: Name, Date, Type, Status; 10–20 rows paginated | Not implemented |
| 4 | Button | “Upload File” to selected folder | Not implemented |
| 5 | Button | “Trigger Watcher” (manual scan) | Not implemented (wire to vault watcher) |
| 6 | Button | “Edit File” (markdown editor for .md) | Not implemented |
| 7 | Markdown viewer | Preview selected file | Not implemented |
| 8 | Download | Selected file | Not implemented |
| 9 | Expander | File metadata (regime tags, linked strategies) | Not implemented |
| 10 | Multiselect | Bulk actions (move to Approved, delete) | Not implemented |
| 11 | Alert | `st.success` on upload/scan | Not implemented |

**Backend:** API or direct file access to vault paths (with auth/path checks). Optional: redundancy stats (e.g. “20% similar to existing”).

---

## Page 4: No-Code Strategy Builder — To Implement

**Purpose:** 8-step wizard for building strategies (non-coders + ML engineers).

**Layout:** Sidebar 1:5 (stepper + agent recommendations); main: tabs per step + 3-column grid.

### Components (spec total: 18) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Stepper | `st.progress` + buttons, 8 steps | Not implemented |
| 2 | Tabs | 8 tabs, one per step (e.g. Data & Features, Model Architecture) | Not implemented |
| 3 | Selectboxes | ~5 options per step (e.g. Model: LSTM, CNN, Combo) with tooltips | Not implemented |
| 4 | Sliders | Layers (1–5), Dropout (0–0.5), Epochs (10–100), Batch Size (16–128) | Not implemented |
| 5 | Multiselect | Preprocessing (Normalization, Pooling, etc.; default from agent) | Not implemented |
| 6 | Buttons | “Next” per tab (with validation) | Not implemented |
| 7 | Button | “Generate Code” → Strategist → drafts/ | Not implemented |
| 8 | Expander | Advanced Code View (editable Python snippet) | Not implemented |
| 9 | Table | Feature Impact (e.g. Boruta scores) | Not implemented |
| 10 | Alert | `st.info` with agent suggestions (e.g. “LSTM for time-series”) | Not implemented |

### Charts (spec total: 2)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Line | Sample training curve (simulated loss vs epochs) | Not implemented |
| 2 | Bar | Feature importance (e.g. ATR top-ranked) | Not implemented |

### Metrics

- Expected Sharpe (simulated >1.2), Risk Tolerance (e.g. 1% per trade). **Backend:** Strategist integration, optional “preview” metrics API.

---

## Page 5: Strategy Library — To Implement

**Purpose:** Central repo for drafts / production / graveyard (like “saved bots”).

**Layout:** Sidebar 1:4 (filters); main: searchable table + detail view (2:1 summary + journal).

### Components (spec total: 13) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Search | By name/hypothesis/failure mode | Not implemented |
| 2 | Table | Strategy list: ID, Name, Status, Metrics; ~20 rows | Not implemented |
| 3 | Multiselect | Filters: drafts, production, graveyard | Not implemented |
| 4 | Button | “View Details” (expand selected) | Not implemented |
| 5 | Button | “Export to Pine Script” (TradingView) | Not implemented |
| 6 | Expander | Full journal (graveyard: mode, reason, metrics) | Not implemented |
| 7 | Download | Code/Report | Not implemented |
| 8 | Button | “Retrigger Validation” (graveyard revive) | Not implemented |
| 9 | Alert | `st.error` for decayed strategies | Not implemented |
| 10–13 | 4 Metric cards | Per strategy: Sharpe, DD, etc. | Not implemented |

### Charts (spec total: 2)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Line | Equity curve per strategy | Not implemented |
| 2 | Pie | Portfolio breakdown (e.g. 40% momentum) | Not implemented |

**Backend:** List strategies from `src/models/drafts`, production, graveyard; journals from failure_journal / vault Logs.

---

## Page 6: Backtester & Killer — To Implement

**Purpose:** Run validations (Monte Carlo Pro); pass → production, fail → journal.

**Layout:** Sidebar 1:3 (params); main 1:2:1 — inputs | results | charts.

### Components (spec total: 14) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Selectbox | Strategy to test (from library) | Not implemented |
| 2 | Slider | Iterations (1k–10k) | Not implemented |
| 3 | Multiselect | Stress tests (noise, slippage, regimes) | Not implemented |
| 4 | Button | “Run Monte Carlo Pro” | Not implemented (wire to `monte_carlo_pro`) |
| 5 | Progress bar | Long runs | Not implemented |
| 6 | Table | Results (metrics per run) | Not implemented |
| 7 | Expander | Market param sims (order types, etc.) | Not implemented |
| 8 | Button | “Approve to Production” | Not implemented |
| 9 | Button | “Journal Failure” (if fail) | Not implemented (wire to Killer/failure_journal) |
| 10 | Alert | Gate status (pass/fail) | Not implemented |
| 11–14 | 4 Checkboxes | e.g. Walk-Forward, Out-of-Sample | Not implemented |

### Charts (spec total: 3)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Histogram | Distribution of returns across MC runs | Not implemented |
| 2 | Heatmap | Regime-specific performance | Not implemented |
| 3 | Box plot | Drawdown scenarios | Not implemented |

### Metrics

- Post-test: Sharpe (>1), DD (<20%), e-ratio (>1.5), Hit Rate (>55%). **Backend:** Monte Carlo Pro API (or subprocess) + Killer integration.

---

## Page 7: Optimization Lab — To Implement

**Purpose:** For ML engineers — tune RL/DL (PPO, Genetic, Ensemble).

**Layout:** Sidebar 1:4 (hyperparam grid); main: tabs (PPO, Genetic, Ensemble) + charts.

### Components (spec total: 15) — all missing

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Tab set | PPO, Genetic, Ensemble | Not implemented |
| 2 | Grid | Hyperparams (e.g. learning rate sliders) | Not implemented |
| 3 | Button | “Train Model” | Not implemented |
| 4 | Selectbox | Env (custom US30 Gym) | Not implemented |
| 5 | Multiselect | Features to encode (Transformers) | Not implemented |
| 6 | Expander | Code hooks (editable) | Not implemented |
| 7 | Progress bar | Training | Not implemented |
| 8 | Table | Optimization results (best params) | Not implemented |
| 9 | Button | “Save to Strategy” | Not implemented |
| 10 | Alert | Overfitting warning | Not implemented |
| 11–15 | Sliders | e.g. rewards (Sharpe * Sortino) | Not implemented |

### Charts (spec total: 3)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Line | Learning curve (rewards over episodes) | Not implemented |
| 2 | Scatter | Param sensitivity (e.g. LR vs Sharpe) | Not implemented |
| 3 | Bar | Ensemble voting weights | Not implemented |

### Metrics

- Optimized Sharpe, Sortino, Kelly fraction (0.5 default). **Backend:** Training jobs (Colab/remote as per project rules) + results API or file-based results.

---

## Page 8: Execution & Reports — To Implement

**Purpose:** Monitor live + briefings (HITL, Telegram-like commands, reports).

**Layout:** Sidebar 1:3 (Telegram commands sim); main: 2 tabs (Execution Monitor, Reports) + 2:1 live feed | metrics.

### Components (spec total: 12) — partially present

| # | Component | Spec | Status |
|---|-----------|------|--------|
| 1 | Tab set | Execution, Reports | Not implemented (Cockpit has no tabs) |
| 2 | Real-time ticker | US30 from MT5, update every 10s | Not implemented |
| 3 | Button | “Approve Trade” (HITL file move sim) | Not implemented |
| 4 | Table | Open positions: Entry, Size, P&L | Not implemented |
| 5 | Multiselect | Alerts (e.g. cooldown triggers) | Not implemented |
| 6 | Markdown | Monday Briefing preview | Not implemented |
| 7 | Button | “Send Report” (Gmail/Telegram) | Not implemented |
| 8 | Expander | Graveyard summaries | Not implemented |
| 9 | Button | “/failure_report” (query journals) | Not implemented |
| 10 | Alert | Circuit breaker status | Not implemented |
| 11 | Download | Full report PDF | Not implemented |

### Charts (spec total: 2)

| # | Chart | Spec | Status |
|---|-------|------|--------|
| 1 | Candlestick | Live US30, last hour | Not implemented |
| 2 | Line | Intraday P&L | Not implemented |

### Metrics

- Real-time: P&L ratio, Volatility (e.g. 10%), Cooldown count (e.g. 2/3). **Backend:** MT5 connector, Reporter, approval gateway, optional Telegram/Gmail integration.

---

## Backend / API Gaps

| Need | Status | To Do |
|------|--------|--------|
| Performance metrics (P&L, Sharpe, Sortino, DD, Hit Rate, e-ratio) | Missing | Add endpoints (from Neon or computed); support date range, regime, session filters. |
| Activity log (recent events) | Missing | Log events from agents/watchers; expose e.g. `GET /activity?limit=20`. |
| Alpha decay / redundancy | Missing | Librarian/Neon redundancy check; expose to Alpha Idea Lab and Dashboard. |
| RESEARCH_PLAN generation | Exists in agent | Expose via API or subprocess from Alpha Idea Lab (Librarian + `run_instruction`). |
| Vault file list/read/write/upload | Missing | API or secure file access for Vault Explorer (list, get, upload, trigger watcher). |
| Strategy list (drafts/production/graveyard) | Missing | Scan `src/models/drafts`, production dir, graveyard; return list + metadata + journal. |
| Monte Carlo Pro run | Exists in code | API or job queue to run Killer/Monte Carlo; return metrics and pass/fail. |
| MT5 live prices / US30 ticker | Missing | Use `market_stream` or MT5 connector; endpoint for last quote + optional candlestick. |
| Neon DB connection | Missing | Use `db_handler` / Neon in API for persistence and institutional memory. |

---

## Suggested Implementation Order

1. **App shell:** Multi-page Streamlit app (e.g. `st.sidebar` nav or `st.navigation`), wide layout, session state for selected strategy/date range/regime.
2. **Home/Dashboard:** Date range, 4 metric cards, P&L curve, regime bar chart, decay heatmap, activity table, links to Alpha Lab and MT5 feed; backend metrics + activity API.
3. **Alpha Idea Lab:** Prompt + templates, “Generate Hypothesis” → Librarian, RESEARCH_PLAN preview, “Proceed to Builder”; optional data preview chart and redundancy warning.
4. **Vault Explorer:** Folder tree, file list, preview, upload, trigger watcher; backend vault API or safe file access.
5. **Strategy Library:** Table + filters, detail view, journal expander, export; backend strategy list + journal API.
6. **Backtester & Killer:** Strategy select, params, “Run Monte Carlo Pro”, results table/charts, Approve/Journal; backend Killer + Monte Carlo integration.
7. **No-Code Strategy Builder:** 8-step wizard, tabs, “Generate Code” → Strategist; optional training curve and feature importance.
8. **Optimization Lab:** PPO/Genetic/Ensemble tabs, hyperparams, “Train Model”, learning curve and param sensitivity (run training on Colab per project rules).
9. **Execution & Reports:** Execution tab (live ticker, positions, Approve Trade), Reports tab (briefing, graveyard, Send Report, /failure_report); MT5 + Reporter + approval gateway.

---

## File / Module Reference

| Spec area | Existing modules to wire |
|-----------|---------------------------|
| Librarian, RESEARCH_PLAN | `src/agents/librarian_agent.py`, `src/prompt/instruction_router.py` |
| Strategist, drafts | `src/agents/strategist_agent.py`, `src/models/drafts/` |
| Killer, Monte Carlo, journal | `src/agents/killer_agent.py`, `src/tools/monte_carlo_pro.py`, `src/tools/failure_journal.py` |
| Vault, watchers | `src/tools/vault_watcher.py`, `run_workflow.py` (ensure vault dirs), `src/watchers/*` |
| Approval / HITL | `src/gateway/approval.py`, `src/execution/broker_adapter.py` |
| Reporter, briefings | `src/agents/reporter.py` |
| MT5 / market data | `src/connectors/market_stream.py` |
| DB | `src/db/db_handler.py`, `src/tools/db_handlers.py` |

---

*Document generated from UI_Requirements.md and current codebase. Last section summarizes what remains to implement before the full Trader-Suit UI meets the spec.*
