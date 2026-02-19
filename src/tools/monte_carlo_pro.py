import numpy as np
import pandas as pd
from typing import Dict, List, Optional


class MonteCarloPro:
    """
    Professional-grade Monte Carlo engine for Alpha Robustness and Risk.
    Addresses: Bootstrapping, Slippage Modeling, and Tail Risk.
    """

    def __init__(self, iterations: int = 10000, confidence_level: float = 0.95):
        self.iterations = iterations
        self.confidence_level = confidence_level

    def simulate_paths(
        self, returns: pd.Series, initial_capital: float = 100000.0
    ) -> Dict:
        """
        Objective 1, 2, & 4: Trade Sequence Randomization and Risk Estimation.
        Returns a distribution of outcomes and drawdown metrics.
        """
        returns_arr = np.asarray(returns)
        results = []
        max_drawdowns = []

        for _ in range(self.iterations):
            # Bootstrapping: Shuffle trade order to test path dependency
            shuffled_returns = np.random.choice(
                returns_arr, size=len(returns_arr), replace=True
            )
            equity_path = initial_capital * np.cumprod(1 + shuffled_returns)

            # Calculate Max Drawdown for this path
            peak = np.maximum.accumulate(equity_path)
            drawdown = (equity_path - peak) / np.where(peak != 0, peak, 1)

            results.append(equity_path[-1])
            max_drawdowns.append(np.min(drawdown))

        results_arr = np.array(results)
        p5 = np.percentile(results_arr, 5)
        tail = results_arr[results_arr < p5]
        expected_shortfall = float(np.mean(tail)) if len(tail) > 0 else float(p5)

        return {
            "ending_values": results,
            "max_dd_dist": max_drawdowns,
            "var_95": np.percentile(results, (1 - self.confidence_level) * 100),
            "expected_shortfall": expected_shortfall,
            "prob_of_ruin": np.mean(results_arr < (initial_capital * 0.5)),
        }

    def inject_execution_friction(
        self,
        returns: pd.Series,
        slippage_pct: float = 0.0002,
        latency_shocks: float = 0.1,
    ) -> pd.Series:
        """
        Objective 5: Slippage & Microstructure Modeling.
        Simulates real-world 'Fill Uncertainty'.
        """
        returns_arr = np.asarray(returns)
        noise = np.random.normal(0, slippage_pct, size=len(returns_arr))
        shocks = np.where(
            np.random.random(len(returns_arr)) < latency_shocks,
            -slippage_pct * 2,
            0,
        )
        return pd.Series(returns_arr + noise + shocks, index=returns.index)

    def stress_test_regimes(
        self, returns: pd.Series, vol_multiplier: float = 2.0
    ) -> Dict:
        """
        Objective 7: Regime & Stress Testing.
        Simulates high-volatility correlation shocks.
        """
        stressed_returns = returns * vol_multiplier
        return self.simulate_paths(stressed_returns)

    # Named regimes: 2020 Crash, 2022 Bear, 2023 Chop (vol multipliers)
    REGIME_STRESS_MULTIPLIERS = {
        "2020_crash": 2.5,
        "2022_bear": 1.8,
        "2023_chop": 1.2,
    }

    def regime_stress_tests(
        self,
        returns: pd.Series,
        initial_capital: float = 100000.0,
        regimes: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Dict]:
        """
        Run stress tests for named regimes (e.g. 2020 Crash, 2022 Bear, 2023 Chop).
        Returns dict regime_name -> {prob_of_ruin, var_95, ...}.
        """
        regimes = regimes or self.REGIME_STRESS_MULTIPLIERS
        out = {}
        for name, vol_mult in regimes.items():
            stressed = returns * vol_mult
            sim = self.simulate_paths(stressed, initial_capital=initial_capital)
            out[name] = {
                "prob_of_ruin": sim["prob_of_ruin"],
                "var_95": sim["var_95"],
                "expected_shortfall": sim["expected_shortfall"],
            }
        return out

    def parameter_stability_tests(
        self,
        returns: pd.Series,
        initial_capital: float = 100000.0,
        n_nudges: int = 20,
        nudge_pct: float = 0.10,
        seed: Optional[int] = None,
    ) -> Dict:
        """
        Randomly nudge returns (simulate parameter sensitivity): scale by (1 + U(-nudge_pct, +nudge_pct)).
        High variance in prob_of_ruin suggests overfitting cliff.
        """
        if seed is not None:
            np.random.seed(seed)
        returns_arr = np.asarray(returns)
        prob_ruins = []
        for _ in range(n_nudges):
            scale = 1.0 + np.random.uniform(-nudge_pct, nudge_pct, size=len(returns_arr))
            nudged = pd.Series(returns_arr * scale, index=returns.index)
            res = self.simulate_paths(nudged, initial_capital=initial_capital)
            prob_ruins.append(res["prob_of_ruin"])
        prob_ruins = np.array(prob_ruins)
        return {
            "prob_of_ruin_mean": float(np.mean(prob_ruins)),
            "prob_of_ruin_std": float(np.std(prob_ruins)),
            "prob_of_ruin_min": float(np.min(prob_ruins)),
            "prob_of_ruin_max": float(np.max(prob_ruins)),
            "overfit_cliff_flag": bool(np.std(prob_ruins) > 0.05 or (np.max(prob_ruins) - np.min(prob_ruins)) > 0.10),
        }

    def get_decision_metrics(self, sim_results: Dict, initial_capital: float = 100000.0) -> str:
        """
        Objective 9: Probability-Based Decision Making.
        Converts raw distributions into actionable logic for the 'Librarian'.
        """
        ending = np.array(sim_results["ending_values"])
        prob_win = np.mean(ending > initial_capital)
        worst_dd = np.percentile(sim_results["max_dd_dist"], 1)
        return (
            f"Alpha Probability Profile:\n"
            f"- Win Probability: {prob_win:.2%}\n"
            f"- 95% Value at Risk: ${sim_results['var_95']:,.2f}\n"
            f"- Worst Case Drawdown (99th): {worst_dd:.2%}"
        )
