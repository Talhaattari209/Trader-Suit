### Detailed UI Specifications for Trader-Suit (Streamlit-Based Frontend)

As your CTO, I'll provide granular specs for each of the 8 core pages/sections in the Trader-Suit UI. These are designed for a **Streamlit app** (local/Colab-hosted), balancing simplicity for non-coders with depth for ML engineers. The overall app uses a **wide layout** (`st.set_page_config(layout="wide")`) for desktop optimization, with mobile responsiveness via Streamlit's built-in features.

**Global Design Principles**:
- **Layout Ratio**: Most pages use a 1:4 sidebar-to-main ratio (sidebar for filters/controls, main for content). Use `st.columns([1,4])` for splits.
- **Components**: Focus on interactive elements (inputs, buttons, selects) for non-coders; advanced expanders for engineers.
- **Graphs/Charts**: Use Plotly (interactive) via `st.plotly_chart` for zoom/pan. Limit to 2–4 per page to avoid clutter.
- **Metrics/Ratios**: Display key trading ratios (e.g., Sharpe, Sortino, Max DD, Hit Rate, e-ratio) in cards (`st.metric`) or tables. Color-code: green (>threshold), red (<threshold).
- **Theme**: Dark mode default (trading vibe); use `st.expander` for collapsible sections.
- **Data Sources**: Pull from Neon DB, MT5 live feed, or your 6-year US30 dataset.
- **Interactivity**: Session state for persistence (e.g., selected strategy carries over pages).
- **Number of Components**: Count includes inputs, buttons, tables, charts, etc. — aim for 10–20 per page max.
- **Ratios in UI**: Refers to layout splits (e.g., 2:1 columns) and financial metrics (e.g., Sharpe Ratio displayed as "2.1").

Now, page-by-page details:

#### 1. Home/Dashboard
**Purpose**: Overview of system health, performance, and quick actions. Like TrendSpider's main dash (watchlists + charts) but tailored to your alpha factory.

**Layout**: 
- Sidebar (1:5 ratio to main): Quick filters (e.g., date range, regime).
- Main: 3-row grid — top: metrics cards (1 row, 4 columns); middle: charts (2 columns); bottom: recent activity table.

**Components (Total: 12)**:
- 1 Date Range Selector (`st.date_input` range for performance period, default: last 30 days).
- 4 Metric Cards (`st.metric`): P&L (e.g., +12.5%), Sharpe Ratio (e.g., 1.8), Max Drawdown (e.g., -8.2%), Active Strategies (e.g., 7/10).
- 1 Button: "New Alpha Idea" (links to Alpha Idea Lab).
- 1 Button: "View Live MT5 Feed" (shows real-time US30 ticker).
- 1 Multiselect: Filter by regime (trending, ranging) or session (London, NY).
- 1 Expander: System Status (PM2 processes, Neon sync, MT5 connection — green/red indicators).
- 1 Table (`st.dataframe`): Recent Activity Log (5 rows: e.g., "Strategy X validated", columns: Timestamp, Event, Status).
- 2 Alerts: st.info for decay warnings (e.g., "Alpha decay in Strategy Y: Sharpe dropped 20%").

**Graphs/Charts (Total: 3)**:
- 1 Line Chart (Plotly): Cumulative P&L curve over time (full width, interactive hover for daily returns).
- 1 Bar Chart: Regime Performance Breakdown (e.g., returns in trending vs. ranging, 2:1 split with metrics table).
- 1 Heatmap: Signal Decay Matrix (rows: strategies, columns: months, color by e-ratio decay).

**Ratios/Metrics Displayed**:
- Sharpe (target >1), Sortino (target >1.5), Max DD (<20%), Hit Rate (>55%), e-ratio (>1.5) — shown in cards with delta arrows (e.g., +0.2 from last week).

#### 2. Alpha Idea Lab
**Purpose**: Prompt-based entry for non-coders to start alpha generation. Inspired by TrendSpider's AI Strategy Lab prompt but with your hypothesis extraction.

**Layout**: 
- Sidebar (1:3 ratio): Suggested templates/examples.
- Main: Vertical flow — top: input prompt; middle: generated plan preview; bottom: options expander.

**Components (Total: 10)**:
- 1 Text Area (`st.text_area`): Natural Language Prompt (e.g., "Mean-reversion on US30 post-news").
- 1 Button: "Generate Hypothesis" (triggers Librarian Agent → RESEARCH_PLAN.md).
- 1 Selectbox: Template Selection (5 options: e.g., "Momentum Breakout", "Pattern Failure" from your examples).
- 1 Multiselect: Add Data Sources (e.g., "6-year US30 Dataset", "Live MT5", "PDF Upload").
- 1 File Uploader (`st.file_uploader`): Upload research PDFs/CSVs.
- 1 Expander: Advanced Hypothesis Tweaks (e.g., regime tags: Hurst >0.5).
- 1 Markdown Display: Generated RESEARCH_PLAN.md preview.
- 1 Button: "Proceed to Builder" (saves to session state, navigates to No-Code Strategy Builder).
- 1 Progress Bar: For agent processing (if async).
- 1 Alert: st.warning if redundancy detected (from Neon check).

**Graphs/Charts (Total: 1)**:
- 1 Scatter Plot: Initial Data Preview (e.g., US30 price vs. volume for hypothesis context, interactive).

**Ratios/Metrics Displayed**:
- Initial e-ratio estimate (from quick scan, e.g., >1.2) and regime-specific returns (e.g., +5% in high-vol).

#### 3. Vault Explorer
**Purpose**: File-based interaction with your Obsidian_Vault. Like Build Alpha's file browser but integrated with agents.

**Layout**: 
- Sidebar (1:4 ratio): Folder navigation tree.
- Main: 2 columns (1:1 ratio) — left: file list/table; right: preview pane.

**Components (Total: 11)**:
- 1 Tree Selector (`st.tree` or expander): Folders (Needs_Action, Plans, Approved, Reports, Logs).
- 1 Search Bar (`st.text_input`): Filter files by name/hypothesis.
- 1 Table (`st.dataframe`): File List (columns: Name, Date, Type, Status; 10–20 rows paginated).
- 1 Button: "Upload File" (to selected folder).
- 1 Button: "Trigger Watcher" (manual scan for new files).
- 1 Button: "Edit File" (opens markdown editor for .md files).
- 1 Markdown Viewer: Preview selected file (e.g., RESEARCH_PLAN.md).
- 1 Download Button: For selected file.
- 1 Expander: File Metadata (e.g., regime tags, linked strategies).
- 1 Multiselect: Bulk Actions (e.g., move to Approved, delete).
- 1 Alert: st.success on successful upload/scan.

**Graphs/Charts (Total: 0)**:
- None — this is file-centric; previews can include embedded charts if .md has them.

**Ratios/Metrics Displayed**:
- None primary; secondary: File stats (e.g., redundancy ratio: 20% similar to existing).

#### 4. No-Code Strategy Builder
**Purpose**: Step-by-step wizard for non-coders/ML engineers. Core no-code feature, like Build Alpha's builder but with ML model choices.

**Layout**: 
- Sidebar (1:5 ratio): Progress stepper (8 steps) + agent recommendations.
- Main: Tabbed per step (use `st.tabs` for navigation) + 3-column grid for choices.

**Components (Total: 18)**:
- 1 Stepper (`st.progress` + buttons): 8 steps (as in workflow).
- 8 Tabs: One per step (e.g., "Data & Features", "Model Architecture").
- 1 Selectbox per step (avg 5 options): e.g., Model: LSTM, CNN, Combo (with tooltips).
- 4 Sliders: e.g., Layers (1–5), Dropout (0–0.5), Epochs (10–100), Batch Size (16–128).
- 1 Multiselect: Preprocessing (Normalization, Pooling, etc.; default agent picks).
- 1 Button per tab: "Next" (validates choices).
- 1 Button: "Generate Code" (triggers Strategist → drafts/).
- 1 Expander: Advanced Code View (editable Python snippet for engineers).
- 1 Preview Table: Feature Impact (e.g., Boruta scores).
- 1 Alert: st.info with agent suggestions (e.g., "LSTM for time-series").

**Graphs/Charts (Total: 2)**:
- 1 Line Chart: Sample Training Curve Preview (simulated loss over epochs).
- 1 Bar Chart: Feature Importance (post-selection, e.g., ATR top-ranked).

**Ratios/Metrics Displayed**:
- Model-specific: e.g., Expected Sharpe (simulated >1.2), Risk Tolerance (1% per trade).

#### 5. Strategy Library
**Purpose**: Central repo for drafts/production/graveyard. Like TrendSpider's saved bots.

**Layout**: 
- Sidebar (1:4 ratio): Filters (status, regime).
- Main: 2 rows — top: searchable table; bottom: detailed view (2:1 split: summary + journal).

**Components (Total: 13)**:
- 1 Search Bar: By name/hypothesis/failure mode.
- 1 Table: Strategy List (columns: ID, Name, Status, Metrics; 20 rows).
- 1 Multiselect: Filters (drafts, production, graveyard).
- 1 Button: "View Details" (expands selected).
- 1 Button: "Export to Pine Script" (for TradingView).
- 1 Expander: Full Journal (for graveyard: mode, reason, metrics).
- 1 Download Button: Code/Report.
- 1 Button: "Retrigger Validation" (for graveyard revive).
- 1 Alert: st.error for decayed strategies.
- 4 Metric Cards: Per strategy (Sharpe, DD, etc.).

**Graphs/Charts (Total: 2)**:
- 1 Equity Curve Line Chart (per strategy).
- 1 Pie Chart: Portfolio Breakdown (e.g., 40% momentum setups).

**Ratios/Metrics Displayed**:
- All key: Sharpe, Sortino, DD, Hit Rate, e-ratio — in table and cards.

#### 6. Backtester & Killer
**Purpose**: Run validations. Like Build Alpha's tester.

**Layout**: 
- Sidebar (1:3 ratio): Param inputs.
- Main: 3 columns (1:2:1) — inputs, results, charts.

**Components (Total: 14)**:
- 1 Selectbox: Strategy to Test (from library).
- 1 Slider: Iterations (1k–10k).
- 1 Multiselect: Stress Tests (noise, slippage, regimes).
- 1 Button: "Run Monte Carlo Pro".
- 1 Progress Bar: For long runs.
- 1 Table: Results (metrics per run).
- 1 Expander: Market Param Sims (order types, etc.).
- 1 Button: "Approve to Production".
- 1 Button: "Journal Failure" (if fail).
- 1 Alert: Gate Status (pass/fail).
- 4 Checkboxes: e.g., Walk-Forward, Out-of-Sample.

**Graphs/Charts (Total: 3)**:
- 1 Distribution Histogram: Returns across MC runs.
- 1 Heatmap: Regime-Specific Performance.
- 1 Box Plot: Drawdown Scenarios.

**Ratios/Metrics Displayed**:
- Post-test: Sharpe (>1), DD (<20%), e-ratio (>1.5), Hit Rate (>55%).

#### 7. Optimization Lab
**Purpose**: For ML engineers — tune RL/DL. Like TrendSpider's cross-breeding.

**Layout**: 
- Sidebar (1:4 ratio): Hyperparam grid.
- Main: Tabs for modes (PPO, Genetic) + charts.

**Components (Total: 15)**:
- 1 Tab Set: 3 tabs (PPO, Genetic, Ensemble).
- 1 Grid Input: Hyperparams (e.g., learning rate sliders).
- 1 Button: "Train Model".
- 1 Selectbox: Env (custom US30 Gym).
- 1 Multiselect: Features to Encode (Transformers).
- 1 Expander: Code Hooks (editable for engineers).
- 1 Progress Bar: Training.
- 1 Table: Optimization Results (best params).
- 1 Button: "Save to Strategy".
- 1 Alert: Overfitting Warning.
- 4 Sliders: e.g., Rewards (Sharpe * Sortino).

**Graphs/Charts (Total: 3)**:
- 1 Learning Curve: Rewards over episodes.
- 1 Scatter: Param Sensitivity (e.g., LR vs. Sharpe).
- 1 Bar: Ensemble Voting Weights.

**Ratios/Metrics Displayed**:
- Optimized: Sharpe, Sortino, Kelly Fraction (0.5 default).

#### 8. Execution & Reports
**Purpose**: Monitor live + briefings. Like Build Alpha's monitoring.

**Layout**: 
- Sidebar (1:3 ratio): Telegram commands sim.
- Main: 2 tabs (Execution Monitor, Reports) + 2:1 split (live feed + metrics).

**Components (Total: 12)**:
- 1 Tab Set: Execution, Reports.
- 1 Real-Time Ticker: US30 from MT5 (updating every 10s).
- 1 Button: "Approve Trade" (HITL file move sim).
- 1 Table: Open Positions (columns: Entry, Size, P&L).
- 1 Multiselect: Alerts (e.g., cooldown triggers).
- 1 Markdown: Monday Briefing Preview.
- 1 Button: "Send Report" (Gmail/Telegram).
- 1 Expander: Graveyard Summaries.
- 1 Button: "/failure_report" (queries journals).
- 1 Alert: Circuit Breaker Status.
- 1 Download: Full Report PDF.

**Graphs/Charts (Total: 2)**:
- 1 Candlestick Chart: Live US30 (last hour).
- 1 Line Chart: Intraday P&L.

**Ratios/Metrics Displayed**:
- Real-time: P&L Ratio, Volatility (e.g., 10%), Cooldown Count (e.g., 2/3).