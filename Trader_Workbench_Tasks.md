# Post-Deployment Tasks (Phase 5: The Trader's Workbench)

## Overview
Based on `client-check-1.md`, these tasks focus on the **Human Interface ("Workbench")** to empower the trader with real-time insights, interactive discovery, and seamless execution control.

## 1. Real-Time Dashboard (The Cockpit)
- [ ] Create `src/dashboard/app.py` (Streamlit or Dash)
  - [ ] Implement **Signal Monitor**:
    - [ ] Real-time display of active signals from `Approved` strategies.
    - [ ] Countdown timers to candle close for potential setups.
  - [ ] Implement **Risk Visualizer**:
    - [ ] Live Portfolio VaR gauge.
    - [ ] Current Drawdown vs Max Drawdown Limit progress bar.
    - [ ] Exposure by Asset Class pie chart.
  - [ ] Implement **Agent Status Panel**:
    - [ ] Watcher/Librarian/Strategist health indicators.
    - [ ] Last "Heartbeat" timestamp.

## 2. Interactive Discovery Lab
- [ ] Create `src/tools/discovery_lab.py`
  - [ ] Implement **"What-If" Engine**:
    - [ ] UI to trigger quick backtests on ad-hoc ideas (e.g., "What if I bought every RSI < 30 on H1?").
    - [ ] Visualization of Monte Carlo outcomes for these ad-hoc tests.
  - [ ] Implement **Regime Scanner**:
    - [ ] Scan watchlist for current regime classification (Trending, Ranging, Volatile).
    - [ ] Alert on regime shifts (e.g., Low Vol -> High Vol breakout).
  - [ ] Implement **Feature Importance Analyzer**:
    - [ ] Tool to run SHAP analysis on a strategy to show *why* it took a trade.

## 3. Trade Journaling & Feedback Loop
- [ ] Create `src/tools/journal.py`
  - [ ] Implement **Automated Trade Logger**:
    - [ ] Capture Entry/Exit execution details (Spread, Slippage).
    - [ ] Snap chart image at time of trade.
  - [ ] Implement **Metadata Tagger**:
    - [ ] Prompt user for "Emotional State" (e.g., Calm, Anxious, FOMO) via UI/CLI after trade.
    - [ ] Tag "Mistake Category" (e.g., Late Entry, Early Exit).
  - [ ] Implement **Performance Analytics**:
    - [ ] Monthly Win Rate by Strategy / Time of Day / Interaction Type (Auto vs Manual).

## 4. Alerting & Notifications
- [ ] Create `src/tools/notifier.py`
  - [ ] Implement **Telegram/Discord Bot Integration using MCP**:
    - [ ] Send critical alerts: "Setup Detected - Await Approval".
    - [ ] Send risk warnings: "Drawdown Limit Approaching".
  - [ ] Implement **Actionable Notifications**:
    - [ ] "Approve Trade" button directly in chat interface (if possible) or link to Dashboard to approve.

## 5. Deployment Optimization
- [ ] Optimize for Low Latency (for Execution Co-Pilot features).
- [ ] Set up secure remote access to Dashboard (VPN/Auth).
