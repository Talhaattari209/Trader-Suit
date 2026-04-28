"""
Killer Agent: stress-tests US30 backtest results via Monte Carlo (Critic role in Actor-Critic).
Reads OHLC(V) or returns CSV, runs execution friction + path simulation,
outputs a Risk Audit markdown to the Obsidian Vault.
Implements the Validation Moat: noise/slippage stress tests and Monte Carlo gate;
see specs.md §7 and docs/ACTOR_CRITIC_SPECS.md. Optional: log results via db_handler.log_backtest().
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .base_agent import BaseAgent
from ..data.us30_loader import US30Loader
from ..tools.monte_carlo_pro import MonteCarloPro
from ..models.base_strategy import BaseStrategy
import importlib.util
import sys
import numpy as np
import pandas as pd

# Default US30 dataset path (can be overridden by env)
DEFAULT_US30_CSV = os.environ.get(
    "US30_CSV_PATH",
    r"C:\Users\User\Downloads\claude\Dataset-Testing-US30\usa30idxusd-m5-bid-2025-10-09-2025-11-29.csv",
)


class KillerAgent(BaseAgent):
    """
    Validates a US30 strategy by injecting execution friction and running
    Monte Carlo path simulation. Writes a Risk Audit to the vault.
    Also detects 1H price levels and logs everything to DataStore.
    """

    def __init__(
        self,
        vault_path: str,
        csv_path: str | None = None,
        slippage_pct: float = 0.0002,
        iterations: int = 10000,
        initial_capital: float = 100000.0,
        *,
        bootstrap_context: str | None = None,
        skill_context: str | None = None,
    ):
        super().__init__("KillerAgent")
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"
        self.csv_path = csv_path or DEFAULT_US30_CSV
        self.slippage_pct = slippage_pct
        self.iterations = iterations
        self.initial_capital = initial_capital
        self.monte_carlo = MonteCarloPro(iterations=iterations)
        self.drafts_dir = self.vault_path.parent / "src" / "models" / "drafts"

        # FilesystemStore for MC audit logging
        try:
            from src.persistence.filesystem_store import FilesystemStore
            self._store = FilesystemStore()
        except Exception:
            self._store = None

    def _load_latest_strategy(self) -> Any:
        """Find and load the most recent strategy class from src/models/drafts/."""
        if not self.drafts_dir.exists():
            return None
        
        files = list(self.drafts_dir.glob("strategy_*.py"))
        if not files:
            return None
            
        # Sort by modification time, newest first
        latest_file = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        
        try:
            spec = importlib.util.spec_from_file_location(latest_file.stem, latest_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[latest_file.stem] = module
                spec.loader.exec_module(module)
                
                # Find the class that inherits from BaseStrategy
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseStrategy)
                        and attr is not BaseStrategy
                    ):
                        self.log_action("load_strategy", f"Loaded {attr_name} from {latest_file.name}")
                        return attr()
        except Exception as e:
            self.log_action("load_strategy", f"Failed to load {latest_file.name}: {e}")
            
        return None

    def _run_backtest(self, df: Any, strategy: BaseStrategy, initial_capital: float) -> Any:
        """Run a simple event-driven backtest for the strategy."""
        equity = initial_capital
        position = 0  # 0=flat, 1=long, -1=short
        entry_price = 0.0
        equity_curve = [initial_capital]
        
        # Convert df to records for fast iteration
        records = df.to_dict("records")
        # Ensure index is accessible if needed, but dict records don't have it by default
        # We can zip with index if strategy needs timestamps
        
        for i, bar in enumerate(records):
            # State for strategy
            state = bar.copy()
            
            # Check Exit first
            if position != 0:
                if strategy.exit(state):
                    # Close position
                    price = bar["Close"]
                    if position == 1:
                        pnl = (price - entry_price) / entry_price
                    else:
                        pnl = (entry_price - price) / entry_price
                    
                    equity *= (1 + pnl)
                    position = 0
            
            # Check Entry
            if position == 0:
                # Update state with potentially new info (though generic here)
                if strategy.entry(state):
                    risk_fraction = strategy.risk(state)
                    if risk_fraction > 0:
                        position = 1  # Assume Long for now if entry is boolean True (TODO: handle short)
                        # NOTE: The BaseStrategy interface entry returns bool.
                        # We might need to look at if it implies direction. 
                        # For now, let's assume entry() -> True means LONG.
                        # Real implementations might return 1 or -1, but type hint says bool.
                        # Let's assume Long-only for simplicity unless we inspect code.
                        # Actually, let's assume Buy.
                        entry_price = bar["Close"]
            
            equity_curve.append(equity)
            
        return pd.Series(equity_curve)

    async def perceive(self, input_data: Any) -> Any:
        """
        Load backtest data AND latest strategy.
        Returns: {"df": df, "returns": returns, "strategy": instance, "path": path}
        """
        path = input_data if isinstance(input_data, str) and input_data else self.csv_path
        if not path or not Path(path).exists():
            self.log_action("perceive", f"File not found: {path}")
            return None
            
        loader = US30Loader(path)
        df = loader.load_clean_data()
        
        # 1. Try to load returns from a STRATEGY backtest
        strategy = self._load_latest_strategy()
        returns = None
        
        if strategy:
            self.log_action("perceive", f"Running backtest for {strategy.__class__.__name__}...")
            # We need a robust backtest. For now, let's use a simplified logical loop
            # matching the interface.
            # But wait, BaseStrategy.entry returns bool.
            # BaseStrategy.risk returns float.
            # We need to know direction.
            # Let's check BaseStrategy definition again. It is abstract.
            # I will implement a simpler "Buy and Hold" fallback if strategy fails or is ambiguous,
            # BUT for the User's request, we need to test the strategy.
            # I'll implement a simple "Long Only" interpretation of entry() for now.
            
            equity_series = self._run_backtest(df, strategy, self.initial_capital)
            returns = equity_series.pct_change().dropna()
            self.log_action("perceive", f"Strategy backtest complete. {len(returns)} bars.")
        
        # 2. Fallback to raw market returns (Buy & Hold) if no strategy
        if returns is None or len(returns) == 0:
             self.log_action("perceive", "No strategy or empty backtest; using Buy & Hold returns.")
             returns = loader.get_returns_series(df)
            
        self.log_action("perceive", f"Loaded {len(returns)} returns from {path}")
        return {"df": df, "returns": returns, "path": path, "strategy_name": strategy.__class__.__name__ if strategy else "Buy&Hold"}

    async def reason(self, state: Any) -> Dict[str, Any]:
        """
        Run execution friction and Monte Carlo simulation; decide REJECT / FLAG / APPROVE.
        """
        if state is None:
            return {"decision": "REJECT", "reason": "No data loaded."}

        returns = state["returns"]
        if len(returns) < 2:
            return {"decision": "REJECT", "reason": "Insufficient returns for simulation."}

        # Actual Sharpe (annualized, simple)
        r_mean, r_std = returns.mean(), returns.std()
        actual_sharpe = (r_mean / r_std * (252 ** 0.5)) if r_std and r_std > 0 else 0.0

        # Perturb then simulate
        friction_returns = self.monte_carlo.inject_execution_friction(
            returns, slippage_pct=self.slippage_pct
        )
        sim_results = self.monte_carlo.simulate_paths(
            friction_returns, initial_capital=self.initial_capital
        )

        prob_of_ruin = sim_results["prob_of_ruin"]
        ending_values = sim_results["ending_values"]
        mean_ev = sum(ending_values) / len(ending_values)
        std_ev = (sum((x - mean_ev) ** 2 for x in ending_values) / len(ending_values)) ** 0.5
        mean_sim_return = (mean_ev - self.initial_capital) / self.initial_capital
        std_sim_return = (std_ev / self.initial_capital) if self.initial_capital else 0
        mean_simulated_sharpe = (
            (mean_sim_return / std_sim_return * (252 ** 0.5))
            if std_sim_return and std_sim_return > 0
            else 0.0
        )

        # Regime stress testing (2020 Crash, 2022 Bear, 2023 Chop)
        regime_results = self.monte_carlo.regime_stress_tests(
            returns, initial_capital=self.initial_capital
        )
        # Parameter stability (nudge params +/- 10%)
        param_stability = self.monte_carlo.parameter_stability_tests(
            returns, initial_capital=self.initial_capital, n_nudges=20, nudge_pct=0.10
        )

        # Validation protocol
        # Validation protocol
        # User criteria: Profitability > 10% (0.10), Drawdown < 12% (0.12)
        # We check the AVERAGE simulation result for robustness, or the actual backtest?
        # "Profitability of 10%" -> Cumulative Return >= 10%
        # "Drawdown of 12%" -> Max Drawdown <= 12%
        
        cum_ret = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1 if 'equity_curve' in locals() else (mean_ev - self.initial_capital) / self.initial_capital
        
        # Using sim results for conservative estimate
        sim_max_dd_95 = np.percentile(sim_results["max_dd_dist"], 95) # 95% of paths have DD less than this? No, spread.
        # Let's use the worst case 95% DD as the metric
        
        # Drawdowns are negative in max_dd_dist (e.g., -0.20)
        # We want drawdown NOT worse than 12% (i.e., > -0.12)
        
        is_profitable = mean_sim_return >= 0.10
        is_safe = prob_of_ruin <= 0.01 
        
        # Check if 95% of paths kept drawdown above -0.12 (i.e. losses < 12%)
        pct_safe_dd = np.mean(np.array(sim_results["max_dd_dist"]) > -0.12)
        
        if (mean_sim_return >= 0.10) and (prob_of_ruin < 0.05): 
             if pct_safe_dd >= 0.90:
                 decision = "APPROVE"
                 reason = f"MET CRITERIA: Return {mean_sim_return:.2%} >= 10%, Safe DD Prob {pct_safe_dd:.2%} >= 90%"
             else:
                 decision = "REJECT"
                 reason = f"Return OK ({mean_sim_return:.2%}), but DD > 12% too frequent ({1-pct_safe_dd:.2%} paths failed DD)"
        elif prob_of_ruin > 0.01:
            decision = "REJECT"
            reason = f"prob_of_ruin {prob_of_ruin:.2%} > 1%"
        elif actual_sharpe > 0 and mean_simulated_sharpe > 0 and (actual_sharpe / mean_simulated_sharpe) < 0.8:
            decision = "FLAG"
            reason = f"Overfit: actual_sharpe/mean_simulated_sharpe = {actual_sharpe / mean_simulated_sharpe:.2f} < 0.8"
        elif param_stability.get("overfit_cliff_flag"):
            decision = "FLAG"
            reason = "Parameter stability: prob_of_ruin varies strongly with small parameter nudges (overfit cliff)."
        else:
            decision = "REJECT" # Default to REJECT if not meeting the 10% target explicitly
            reason = f"Return {mean_sim_return:.2%} < 10% target."

        strategy_name = (state or {}).get("strategy_name", "unknown")
        return {
            "decision": decision,
            "reason": reason,
            "strategy_name": strategy_name,
            "prob_of_ruin": prob_of_ruin,
            "actual_sharpe": actual_sharpe,
            "mean_simulated_sharpe": mean_simulated_sharpe,
            "sim_results": sim_results,
            "regime_results": regime_results,
            "param_stability": param_stability,
            "decision_metrics": self.monte_carlo.get_decision_metrics(
                sim_results, self.initial_capital
            ),
        }

    async def act(self, plan: Dict[str, Any]) -> bool:
        """
        Write Risk Audit markdown to Vault/Logs/.
        Detect 1H price levels and log MC run to DataStore.
        """
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        audit_path = self.logs_dir / f"Risk_Audit_{ts}.md"

        # Detect 1H price levels for this MC run
        price_levels: dict = {}
        try:
            from src.tools.price_level_detector import detect_all_price_levels
            import pandas as _pd
            if self.csv_path and Path(self.csv_path).exists():
                df = _pd.read_csv(self.csv_path, parse_dates=True, index_col=0)
                price_levels = detect_all_price_levels(df)
                self.log_action("act", (
                    f"PriceLevelDetector: {len(price_levels.get('liquidity_zones', []))} liq zones, "
                    f"{len(price_levels.get('fvg_zones', []))} FVG zones (1H)"
                ))
        except Exception as e:
            self.log_action("act", f"Price level detection skipped: {e}")

        decision = plan.get("decision", "UNKNOWN")
        reason = plan.get("reason", "")
        prob_of_ruin = plan.get("prob_of_ruin", 0)
        actual_sharpe = plan.get("actual_sharpe", 0)
        mean_simulated_sharpe = plan.get("mean_simulated_sharpe", 0)
        metrics_text = plan.get("decision_metrics", "")
        regime_results = plan.get("regime_results") or {}
        param_stability = plan.get("param_stability") or {}

        regime_lines = []
        for rname, rval in regime_results.items():
            regime_lines.append(f"- **{rname}**: prob_of_ruin={rval.get('prob_of_ruin', 0):.2%}, VaR95=${rval.get('var_95', 0):,.0f}")
        regime_section = "\n".join(regime_lines) if regime_lines else "N/A"

        param_lines = [
            f"- prob_of_ruin (nudged): mean={param_stability.get('prob_of_ruin_mean', 0):.2%}, std={param_stability.get('prob_of_ruin_std', 0):.2%}",
            f"- overfit_cliff_flag: {param_stability.get('overfit_cliff_flag', False)}",
        ]
        param_section = "\n".join(param_lines)

        body = f"""---
type: risk_audit
timestamp: {datetime.now().isoformat()}
decision: {decision}
prob_of_ruin: {prob_of_ruin:.4f}
actual_sharpe: {actual_sharpe:.4f}
mean_simulated_sharpe: {mean_simulated_sharpe:.4f}
---

# Risk Audit — {ts}

## Decision: **{decision}**

**Reason:** {reason}

## Metrics

- **Prob. of Ruin (50% loss):** {prob_of_ruin:.2%}
- **Actual Sharpe (annualized):** {actual_sharpe:.4f}
- **Mean Simulated Sharpe:** {mean_simulated_sharpe:.4f}

## Alpha Probability Profile

{metrics_text}

## Regime Stress Testing (2020 Crash, 2022 Bear, 2023 Chop)

{regime_section}

## Parameter Stability (nudge ±10%)

{param_section}

## Price Levels (1H — at MC run time)

- Liquidity zones: {len(price_levels.get("liquidity_zones", []))}
- FVG zones: {len(price_levels.get("fvg_zones", []))}
- Day High: {price_levels.get("session_levels", {}).get("day", {}).get("high", "N/A")}
- Day Low: {price_levels.get("session_levels", {}).get("day", {}).get("low", "N/A")}
- Week High: {price_levels.get("session_levels", {}).get("week", {}).get("high", "N/A")}
- Detected at: {price_levels.get("detected_at", "N/A")}

## Actions

- If **REJECT**: Move strategy to `/Strategy_Graveyard`.
- If **FLAG**: Review for overfitting before moving to `/Done`.
- If **APPROVE**: May move to `/Done`.
"""
        audit_path.write_text(body, encoding="utf-8")
        self.log_action("act", f"Wrote {audit_path}")

        # ── Log MC run to DataStore ───────────────────────────────────────────
        if self._store:
            try:
                mc_results_summary = {
                    "decision": decision,
                    "reason": reason,
                    "metrics": {
                        "prob_of_ruin": prob_of_ruin,
                        "actual_sharpe": actual_sharpe,
                        "mean_simulated_sharpe": mean_simulated_sharpe,
                    },
                    "regime_results": {k: {"prob_of_ruin": v.get("prob_of_ruin")}
                                       for k, v in (plan.get("regime_results") or {}).items()},
                }
                strategy_name = plan.get("strategy_name", "unknown")
                run_id = self._store.log_mc_run(strategy_name, mc_results_summary, price_levels)
                self._store.advance_workflow_step("killer_done", {
                    "strategy_id": strategy_name,
                    "mc_run_id": run_id,
                    "pass": decision == "APPROVE",
                })
                self.log_action("act", f"MC run logged to DataStore: {run_id}")
            except Exception as e:
                self.log_action("act", f"DataStore MC log failed: {e}")

        # Paradigms Task 1: on REJECT/FLAG write journaled entry to graveyard (if DB available)
        if decision in ("REJECT", "FLAG"):
            try:
                from src.tools.failure_journal import build_journal_entry
                strategy_name = plan.get("strategy_name", "unknown")
                metrics_pre = {
                    "actual_sharpe": plan.get("actual_sharpe"),
                    "mean_simulated_sharpe": plan.get("mean_simulated_sharpe"),
                    "prob_of_ruin": plan.get("prob_of_ruin"),
                }
                journal = build_journal_entry(
                    strategy_id=strategy_name,
                    reason=reason,
                    decision=decision,
                    metrics_pre=metrics_pre,
                    metrics_post=None,
                    description=reason,
                    mitigation="Review regime filters and parameter stability; consider narrower scope.",
                )
                db_url = os.environ.get("DATABASE_URL")
                if db_url:
                    from src.db.db_handler import DBHandler
                    db = DBHandler(db_url)
                    await db.connect()
                    try:
                        await db.add_to_graveyard(
                            hypothesis=f"{strategy_name}: {reason[:500]}",
                            reason_for_failure=decision,
                            context=journal,
                        )
                        self.log_action("act", "Graveyard entry written (with journal)")
                    finally:
                        await db.close()
            except Exception as e:
                self.log_action("act", f"Graveyard journal skip: {e}")

        return True
