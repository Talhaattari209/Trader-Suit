# Company Handbook

## Trading Rules
1. Always adhere to risk limits.
2. All strategies must be backtested over multiple market regimes.
3. No manual intervention unless system failure or extreme market conditions.

## Risk Limits
- Max Drawdown per Strategy: 10%
- Max Portfolio VaR (95% CI): 5%
- Position Sizing: Dynamic based on volatility.

## Monte Carlo Validation Protocol (Killer Agent)

All US30 strategies must pass the Killer Agent gate before moving to `/Done`.

1. **Ingest**: Load US30 backtest results from the Strategist (OHLC/V CSV or returns).
2. **Perturb**: Use `inject_execution_friction` to simulate ~2 pip average slippage.
3. **Simulate**: Run 10,000 paths via `simulate_paths`.
4. **Audit**:
   - **IF** `prob_of_ruin` > 1% **OR** p_value > 0.05 → **REJECT** (move to `/Strategy_Graveyard`).
   - **IF** `actual_sharpe / mean_simulated_sharpe` < 0.8 → **FLAG** as Overfit.
   - **ELSE** → **APPROVE** (may move to `/Done`).

Risk Audit reports are written to `/Logs/Risk_Audit_<timestamp>.md`.

## Default US30 Dataset

- Path (override via env `US30_CSV_PATH`):  
  `Dataset-Testing-US30/usa30idxusd-m5-bid-2025-10-09-2025-11-29.csv`  
  (or absolute path on your machine.)

## Code of Conduct
- Maintain clean, documented code.
- Follow the "Code-as-Interface" philosophy.
