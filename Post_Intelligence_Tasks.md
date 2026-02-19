# Post-Intelligence Layer Tasks (Phase 3 & Beyond)

## Overview
After the Intelligence Layer (Librarian, Strategist, basic Orchestration) is operational, the focus shifts to **Execution Robustness, Live Trading safeguards, and Deployment**.

## 1. Risk Architect Agent
- [ ] Create `src/agents/risk_architect.py`
  - [ ] Implement **Position Sizing Logic**:
    - [ ] Kelly Criterion (fractional).
    - [ ] Volatility targeting (e.g., target 5% daily vol).
  - [ ] Implement **Behavioral Guardrails**:
    - [ ] "Cool-down" forced breaks after X consecutive losses.
    - [ ] Max daily drawdown lockout.
  - [ ] Implement **SL/TP Optimizer**:
    - [ ] Dynamic stop-loss based on ATR.

## 2. Advanced Validation ("Killer Agent" Expansion)
- [ ] Expand `src/agents/killer_agent.py`
  - [ ] Add **Regime Stress Testing**:
    - [ ] Simulate performance during 2020 Crash, 2022 Bear, 2023 Chop.
  - [ ] Add **Parameter Stability Tests**:
    - [ ] Randomly nudge strategy parameters (e.g., MA period +/- 10%) to check for overfitting cliffs.

## 3. Reporting & Feedback
- [ ] Create `src/agents/reporter.py` ("Monday Morning Briefing")
  - [ ] Analyze `Logs/` and `Accounting/` data.
  - [ ] Generate weekly Markdown report in `AI_Employee_Vault/Reports/`:
    - [ ] P&L summary.
    - [ ] Strategy approvals/rejections stats.
    - [ ] Market regime analysis.

## 4. Live Execution Bridge (Phase 4)
- [ ] Implement API connectors (OANDA / MetaTrader 5 / IBKR).
- [ ] Create `src/execution/broker_adapter.py`.
- [ ] Implement **Human-in-the-Loop Enforcer**:
  - [ ] Code must strictly check `AI_Employee_Vault/Approved/` before sending any live order.

## 5. Deployment & Infrastructure
- [ ] Create `Dockerfile`.
- [ ] Set up `docker-compose.yml` for local testing (App + Neon DB proxy if needed).
- [ ] Create logic for **Cloud Deployment** (GCP Cloud Run or VM).
- [ ] Set up **CI/CD pipeline** (GitHub Actions) to run unit tests and basic Monte Carlo checks on commit.
