### Enhanced UI Specifications for Missed Requirements in Trader-Suit (Streamlit-Based Frontend)

Below, I detail the designed components for the missed requirements you specified. These build on the previous 8-page structure, adding two new pages (Situational Analysis and Technical Analysis) and enhancing existing ones. All designs follow the global principles: wide layout, 1:4 sidebar-to-main ratio where applicable, Plotly for interactive charts, and `st.metric` for ratios. For AI models (e.g., PPO, LSTM, CNN), integrate Colab triggers: Use buttons to launch a pre-configured Colab notebook (via URL or API call to your remote Colab setup), passing params via query strings or shared Drive files. This ensures no local heavy compute—models run on Colab, results sync back to Neon DB for display.

I've counted components (inputs, buttons, tables, etc.), graphs, and specified ratios/metrics. Layouts use columns/tabs/expanders for nesting.

#### New Page: Situational Analysis
**Purpose**: Professional-grade probabilistic analysis of market events (e.g., "Friday gap down in DAX: odds on each candle"). Analyzes historical/lIVE data for event odds, using your 6-year US30 + MT5, with extensions to DAX via code_execution or web_search if needed. Outputs odds (e.g., probability of close above/below gap) per candle/timeframe.

**Layout**: 
- Sidebar (1:4 ratio): Event filters and params.
- Main: 2 tabs ("Event Input" and "Analysis Results") + 3-column grid (1:2:1 for inputs, odds table, charts).

**Components (Total: 14)**:
- 1 Text Input: Event Description (e.g., "Friday gap down in DAX").
- 1 Selectbox: Asset (default: US30; options: DAX, others via MT5).
- 1 Date Range Selector: Historical Lookback (default: 6 years).
- 1 Slider: Candle Granularity (e.g., 1-min to daily).
- 1 Multiselect: Metrics to Compute (e.g., "Odds of Fill", "Average Recovery Time", "Volatility Spike").
- 1 Button: "Run Analysis" (triggers backend query on dataset/MT5; uses code_execution internally for stats).
- 1 Button: "Export Report" (PDF with odds).
- 1 Table: Odds Breakdown (columns: Candle #, Odds Up (%), Odds Down (%), Historical Matches; 10–20 rows).
- 1 Expander: Advanced Params (e.g., confidence intervals via statsmodels).
- 1 Progress Bar: For computation.
- 1 Alert: st.info with interpretation (e.g., "70% odds of gap fill by EOD").
- 1 Button: "Trigger Colab for Deep Stats" (launches Colab for Monte Carlo odds sim).
- 1 Markdown: Event Summary (auto-generated).
- 1 Checkbox: Include Live MT5 Data.

**Graphs/Charts (Total: 3)**:
- 1 Bar Chart: Odds per Candle (stacked: Up/Down/Neutral; interactive hover for historical examples).
- 1 Histogram: Distribution of Outcomes (e.g., gap sizes vs. recovery odds).
- 1 Line Chart: Cumulative Probability Over Time (e.g., odds evolving per candle).

**Ratios/Metrics Displayed**:
- Odds Ratio (e.g., 70:30 Up:Down), Confidence Interval (e.g., 95%), Historical Hit Rate (>50%), Volatility Ratio (post-event vs. average), e-ratio (>1.2 for bullish odds).

#### New Page: Technical Analysis (Indicator Builder)
**Purpose**: Build custom indicators and variants using advanced math (e.g., Fourier transforms, stochastic processes via sympy/mpmath). For ML engineers/non-coders to create/reuse indicators in strategies.

**Layout**: 
- Sidebar (1:5 ratio): Math library selector and previews.
- Main: Tabs for "Build Indicator" and "Variants" + 2:1 split (builder form + test chart).

**Components (Total: 16)**:
- 1 Text Area: Indicator Specs/Formula (e.g., "EMA variant with wavelet denoising via scipy").
- 1 Selectbox: Base Indicator (e.g., SMA, RSI, MACD; 20+ options).
- 1 Multiselect: Advanced Math Techniques (e.g., Normalization, Fourier Transform, Pooling, Hurst Exponent via statsmodels).
- 1 Slider: Params (e.g., Period: 5–50, default agent-suggested).
- 1 Button: "Generate Variant Code" (triggers code gen with math libs).
- 1 Button: "Test on Data" (applies to US30 sample).
- 1 Expander: Code Description (auto-gen: "This computes denoised EMA using wavelet...").
- 1 Table: Variant List (columns: Name, Formula, Params, Test Metrics; 5–10 rows).
- 1 Button: "Save to Library" (adds to edges/ folder).
- 1 File Uploader: Upload Math Docs (PDF/DOCX for inspiration).
- 1 Button: "Trigger Colab for Compute" (for heavy math like pyscf sims).
- 1 Progress Bar: For building.
- 1 Alert: st.warning if math invalid (e.g., sympy error).
- 1 Markdown: Generated Code Snippet.
- 1 Checkbox: Auto-Optimize Params (via PuLP).
- 1 Download Button: Export Indicator Code (Python/Pine).

**Graphs/Charts (Total: 3)**:
- 1 Candlestick + Overlay Line: Indicator on US30 Chart (interactive, zoom to see variants).
- 1 Heatmap: Param Sensitivity (e.g., period vs. signal strength).
- 1 Scatter Plot: Math Validation (e.g., Fourier spectrum for denoising).

**Ratios/Metrics Displayed**:
- Signal-to-Noise Ratio (post-denoising >2), Lag Metric (candles delayed <5), Correlation to Price (e.g., 0.8), e-ratio (>1.5 for edge).

#### Enhanced: Home/Dashboard
**New Additions**: Nested strategy profiles; 4–5 tabs in recent table for profiles (Strategy, AI Model, Market, Individual Trade).

**Updated Layout**: 
- Sidebar unchanged.
- Main: Add expander for "Strategy Profiles" + enhanced recent table with tabs.

**Added/Updated Components (Total +8 to original 12 = 20)**:
- 1 Expander: Nested Strategy Profiles (clickable tree: Strategy Name → Passed/Failed → Metrics/Chars).
- 1 Table (enhanced): Recent Activity → now with 5 Tabs below:
  - Tab 1: Strategy Profile (columns: Name, Status, Metrics JSON, Chars vs. Market — e.g., "Trending regime: High vol tolerance").
  - Tab 2: AI Model Profile (columns: Model Type (LSTM/PPO), Params, Training Metrics — e.g., "Overfit Score: Low").
  - Tab 3: Market Profile (columns: Regime, Vol Clustering, Infrastructure Sims — e.g., "Order-Driven, Latency: 2ms").
  - Tab 4: Individual Trade Profile (columns: Trade ID, Entry/Exit, P&L, Slippage, Odds from Situational).
  - Tab 5: Composite Profile (summary ratios across all).
- 1 Button: "View Full Profile" (per row, opens modal with details).
- 1 Multiselect: Filter Profiles (passed/failed).
- 1 Alert: st.error for failed characteristics (e.g., "Failed in low-vol: DD >20%").

**Added Graphs/Charts (Total +2 to original 3 = 5)**:
- 1 Tree Map: Nested Chars (strategy vs. market: size by returns).
- 1 Radar Chart: Metrics Comparison (e.g., Sharpe/DD/Hit for passed vs. failed).

**Added Ratios/Metrics**: Overfit Score (0–1), Market Correlation (0.5–1), Regime Fit Ratio (>0.7).

#### Enhanced: Alpha Idea Lab
**New Additions**: Upload DOCX/PDF; Conversational style (up to 10 iterations).

**Updated Layout**: 
- Sidebar: Add upload section.
- Main: Chat-like interface (st.chat_message) for iterations.

**Added/Updated Components (Total +6 to original 10 = 16)**:
- 1 File Uploader: For DOCX/PDF (parses via openpyxl/PyPDF2; max 10MB).
- 1 Chat Input: User Message (e.g., "Refine: Add vol filter").
- 1 Chat Display: Conversation History (up to 10 messages; agent responds via Librarian).
- 1 Button: "Start Conversation" (initiates loop).
- 1 Counter: Iteration Count (e.g., "5/10").
- 1 Button: "Finalize Idea" (saves refined RESEARCH_PLAN.md).

**Added Graphs/Charts (Total +0 = 1)**: Unchanged.

**Added Ratios/Metrics**: Refinement Score (e.g., similarity improvement per iteration >0.2 via embeddings).

#### Enhanced: No-Code Strategy Builder
**New Additions**: Specs-driven dev — user writes specs/code to get generated code/descriptions for workflow/indicators.

**Updated Layout**: 
- Sidebar: Specs input.
- Main: Add "Specs Mode" tab.

**Added/Updated Components (Total +7 to original 18 = 25)**:
- 1 Tab: "Specs-Driven Mode" (beside wizard).
- 1 Text Area: Specs Input (e.g., "Build workflow: Entry on RSI<30, exit ATR*2").
- 1 Button: "Generate Code/Description" (outputs Python + plain-English breakdown).
- 1 Markdown: Code Description (e.g., "This step computes RSI using TA-lib...").
- 1 Expander: Indicator Specs (subset for building variants).
- 1 Button: "Iterate Specs" (refine via chat-like).
- 1 Alert: st.success on valid specs.

**Added Graphs/Charts (Total +1 to original 2 = 3)**:
- 1 Flowchart: Workflow Viz (generated via networkx/Plotly).

**Added Ratios/Metrics**: Workflow Efficiency (steps <10), Indicator Complexity (params <5).

#### Enhanced: Strategy Library
**New Additions**: Separate tabs for production/draft/graveyard.

**Updated Layout**: 
- Main: Replace table with 3 tabs.

**Added/Updated Components (Total +3 to original 13 = 16)**:
- 1 Tab Set: "Drafts", "Production", "Graveyard" (each with table: Name, Info, Metrics).
- 1 Expander per tab: Detailed Info (e.g., Graveyard: Failure Journal).
- 1 Button: "Compare Across Tabs" (e.g., metrics diff).

**Added Graphs/Charts (Total +0 = 2)**: Unchanged.

**Added Ratios/Metrics**: Survival Ratio (production vs. graveyard >50%).

#### Enhanced: Backtester & Killer
**New Additions**: Separate profile per Monte Carlo run with deep characteristics.

**Updated Layout**: 
- Main: Add "MC Profiles" tab.

**Added/Updated Components (Total +5 to original 14 = 19)**:
- 1 Tab: "MC Profiles" (list of runs).
- 1 Table: MC List (columns: Run ID, Chars — e.g., "Noise Level: 2pip, Regime: Trending").
- 1 Expander: Deep Profile (per run: metrics, sim params, failure odds).
- 1 Button: "View Profile" (modal with details).
- 1 Button: "Trigger Colab MC" (for heavy runs).

**Added Graphs/Charts (Total +1 to original 3 = 4)**:
- 1 Violin Plot: Characteristic Distributions (e.g., slippage across runs).

**Added Ratios/Metrics**: Robustness Ratio (passed sims >80%), Characteristic Depth (e.g., 10+ params analyzed).

#### Enhanced: Optimization Lab
**New Additions**: AI model graphs for overfitting, etc.; Colab runs.

**Updated Layout**: 
- Main: Add graphs section.

**Added/Updated Components (Total +4 to original 15 = 19)**:
- 1 Button: "Run on Colab" (per model, passes params).
- 1 Expander: Overfitting Diagnostics.
- 1 Table: Model Metrics (in-sample vs. out-of-sample).
- 1 Alert: st.error if overfit detected.

**Added Graphs/Charts (Total +2 to original 3 = 5)**:
- 1 Line Chart: Train vs. Validation Loss (overfitting if diverging).
- 1 Scatter: In-Sample vs. Out-of-Sample Sharpe (gap indicates overfit).

**Added Ratios/Metrics**: Overfit Gap (Sharpe diff <0.5), Generalization Ratio (>0.8).

---

## Implementation Notes: No-Code Builder Agent & Colab Execution

- **Agent-managed Code | Specs:** The No-Code Strategy Builder includes an **agent** that manages two parallel columns (Code and Specs). When the user edits **code** and clicks **Submit** for a block, the agent re-evaluates that block and all previous steps and updates the **Specs** column with a plain-English description of what the code does. When the user edits **Specs** and clicks **Apply Specs → Code**, the agent updates the code to match. Specs and code stay in sync bidirectionally.
- **Colab execution:** Heavy model runs (RL/DL/ML, Monte Carlo) are not executed locally. The UI provides **Trigger Colab** / **Run on Colab** buttons that open a pre-configured Colab notebook (URL from `COLAB_NOTEBOOK_URL`). Generated strategy code can be synced to Drive (e.g. `COLAB_DRIVE_STRATEGY_PATH`) so the Colab notebook can load and run it. This aligns with the autonomous system that executes model code on Colab (see `.cursor/rules/colab-remote.mdc` and `Manage_colab.md`).