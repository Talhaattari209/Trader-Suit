from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from src.config.computation_budget import budget as CB


class MonteCarloPro:
    """
    Professional-grade Monte Carlo engine for Alpha Robustness and Risk.
    Addresses: Bootstrapping, Slippage Modeling, and Tail Risk.

    Default sample counts are driven by ComputationBudget (local: 1,000 / colab: 10,000).
    Pass explicit values to override for a single call.
    """

    def __init__(self, iterations: int | None = None, confidence_level: float = 0.95):
        self.iterations = iterations if iterations is not None else CB.mc_iterations
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
        n_nudges: int | None = None,
        nudge_pct: float = 0.10,
        seed: Optional[int] = None,
    ) -> Dict:
        """
        Randomly nudge returns (simulate parameter sensitivity): scale by (1 + U(-nudge_pct, +nudge_pct)).
        High variance in prob_of_ruin suggests overfitting cliff.
        """
        n_nudges = n_nudges if n_nudges is not None else CB.mc_nudges
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

    def indicator_parameter_sweep(
        self,
        df: pd.DataFrame,
        indicator_configs: list[dict],
        signal_fn: Any = None,
        initial_capital: float = 100_000.0,
        n_samples: int | None = None,
        seed: int = 42,
    ) -> dict:
        """
        Sweep TA indicator parameters and measure strategy robustness.

        Uses the local pandas_ta_classic library (via indicator_engine) to compute
        each indicator across ``n_samples`` random parameter combinations, then
        evaluates a simple cross-over signal to produce a returns series.

        Args:
            df:                OHLCV DataFrame (1H preferred).
            indicator_configs: List of {"name": str, "role": "entry"|"exit"|"filter", ...}
                               e.g. [{"name": "RSI", "role": "entry"},
                                     {"name": "MACD", "role": "exit"},
                                     {"name": "ATR", "role": "filter"}]
            signal_fn:         Optional callable(df, indicators_dict) -> pd.Series of returns.
                               If None, uses the built-in RSI/MACD cross-over heuristic.
            initial_capital:   Starting equity for each simulation path.
            n_samples:         Number of parameter combinations to test per indicator.
            seed:              RNG seed for reproducibility.

        Returns:
            {
              "indicator_sweep_results": [
                  {
                    "indicator": str,
                    "params": dict,
                    "sharpe": float,
                    "prob_of_ruin": float,
                    "win_rate": float,
                  }, ...
              ],
              "param_sharpe_std":   float,   ← std of Sharpe across all combos
              "param_ruin_std":     float,   ← std of prob_of_ruin across all combos
              "overfit_cliff_flag": bool,
              "best_params":        dict,    ← params from highest Sharpe run
              "worst_params":       dict,    ← params from lowest Sharpe run
              "sharpe_range":       [float, float],
            }
        """
        n_samples = n_samples if n_samples is not None else CB.mc_indicator_samples

        try:
            from src.tools.indicator_engine import sweep_indicator_params, compute_indicator
        except ImportError:
            return {"error": "indicator_engine not available"}

        rng = np.random.default_rng(seed)
        sweep_results: list[dict] = []

        for config in indicator_configs:
            ind_name = config.get("name", "RSI")
            samples  = sweep_indicator_params(ind_name, df, n_samples=n_samples, seed=seed)

            for sample in samples:
                params  = sample["params"]
                ind_out = sample["result"]

                # Generate returns via signal_fn or built-in heuristic
                returns = _default_signal_returns(df, ind_name, ind_out)
                if returns is None or len(returns) < 10:
                    continue

                # Compute key metrics without full MC (fast path)
                r_arr   = np.asarray(returns.dropna())
                if len(r_arr) < 2:
                    continue
                mean_r  = float(np.mean(r_arr))
                std_r   = float(np.std(r_arr)) or 1e-9
                sharpe  = float(mean_r / std_r * np.sqrt(252))

                # Quick MC path (fewer iterations for speed in sweep)
                sim = self.simulate_paths(
                    pd.Series(r_arr),
                    initial_capital=initial_capital,
                )
                pos = r_arr[r_arr > 0]
                win_rate = float(len(pos) / len(r_arr)) if len(r_arr) else 0.0

                sweep_results.append({
                    "indicator":    ind_name,
                    "params":       params,
                    "sharpe":       round(sharpe, 4),
                    "prob_of_ruin": round(sim["prob_of_ruin"], 4),
                    "win_rate":     round(win_rate, 4),
                })

        if not sweep_results:
            return {
                "indicator_sweep_results": [],
                "param_sharpe_std": 0.0,
                "param_ruin_std": 0.0,
                "overfit_cliff_flag": False,
                "best_params": {},
                "worst_params": {},
                "sharpe_range": [0.0, 0.0],
            }

        sharpes     = np.array([r["sharpe"]       for r in sweep_results])
        ruin_values = np.array([r["prob_of_ruin"] for r in sweep_results])
        sharpe_std  = float(np.std(sharpes))
        ruin_std    = float(np.std(ruin_values))

        best  = sweep_results[int(np.argmax(sharpes))]
        worst = sweep_results[int(np.argmin(sharpes))]

        return {
            "indicator_sweep_results": sweep_results,
            "param_sharpe_std":   round(sharpe_std, 4),
            "param_ruin_std":     round(ruin_std, 4),
            "overfit_cliff_flag": bool(sharpe_std > 0.5 or ruin_std > 0.05),
            "best_params":        best,
            "worst_params":       worst,
            "sharpe_range":       [round(float(sharpes.min()), 4),
                                   round(float(sharpes.max()), 4)],
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


# ── Module-level helpers ──────────────────────────────────────────────────────

def _default_signal_returns(
    df: pd.DataFrame,
    indicator_name: str,
    indicator_output,
) -> "pd.Series | None":
    """
    Generate a simple long/flat returns series from an indicator output.
    Used by MonteCarloPro.indicator_parameter_sweep() when no signal_fn is provided.

    Logic per indicator type:
    - RSI / RSX:     long when RSI < 30 (oversold), flat otherwise
    - MACD:          long when MACD histogram > 0
    - SMA/EMA/WMA:   long when close > MA
    - CCI:           long when CCI < -100
    - MOM/ROC:       long when value > 0
    - BBands:        long when close < lower band (mean-reversion)
    - ATR/NATR:      high ATR = long (volatility breakout proxy)
    - ADX:           long when ADX > 25 (trend present)
    - OBV/CMF/MFI:   long when value > 0 / > 50
    - Default:       random benchmark
    """
    import pandas as pd
    import numpy as np

    close = None
    for c in df.columns:
        if c.lower() == "close":
            close = df[c]
            break
    if close is None:
        return None

    key = indicator_name.upper()
    try:
        if key in ("RSI", "RSX", "STOCHRSI"):
            if indicator_output is None:
                return None
            if isinstance(indicator_output, pd.DataFrame):
                ind = indicator_output.iloc[:, 0]
            else:
                ind = indicator_output
            signal = (ind < 30).astype(float)

        elif key == "MACD":
            if indicator_output is None or not isinstance(indicator_output, pd.DataFrame):
                return None
            hist_cols = [c for c in indicator_output.columns if "h" in c.lower()]
            if not hist_cols:
                return None
            hist = indicator_output[hist_cols[0]]
            signal = (hist > 0).astype(float)

        elif key in ("SMA", "EMA", "WMA", "HMA", "DEMA", "TEMA", "KAMA", "ALMA", "VWMA"):
            if indicator_output is None:
                return None
            signal = (close > indicator_output).astype(float)

        elif key == "CCI":
            if indicator_output is None:
                return None
            signal = (indicator_output < -100).astype(float)

        elif key in ("MOM", "ROC"):
            if indicator_output is None:
                return None
            signal = (indicator_output > 0).astype(float)

        elif key in ("BBANDS", "BB"):
            if indicator_output is None or not isinstance(indicator_output, pd.DataFrame):
                return None
            lower_cols = [c for c in indicator_output.columns if "l" in c.lower()]
            if not lower_cols:
                return None
            lower = indicator_output[lower_cols[0]]
            signal = (close < lower).astype(float)

        elif key in ("ADX",):
            if indicator_output is None or not isinstance(indicator_output, pd.DataFrame):
                return None
            adx_cols = [c for c in indicator_output.columns if "adx" in c.lower()]
            if not adx_cols:
                return None
            adx = indicator_output[adx_cols[0]]
            signal = (adx > 25).astype(float)

        elif key in ("OBV", "CMF"):
            if indicator_output is None:
                return None
            signal = (indicator_output > 0).astype(float)

        elif key == "MFI":
            if indicator_output is None:
                return None
            signal = (indicator_output < 20).astype(float)

        else:
            # Generic: random benchmark for unmapped indicators
            np.random.seed(42)
            signal = pd.Series(
                np.random.choice([0.0, 1.0], size=len(close), p=[0.5, 0.5]),
                index=close.index,
            )

        # Convert signal to returns: long bar = close[i+1]/close[i] - 1, else 0
        bar_returns = close.pct_change().shift(-1)
        strategy_returns = (signal * bar_returns).dropna()
        return strategy_returns

    except Exception:
        return None
