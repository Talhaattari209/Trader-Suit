"""
Performance Metrics Module — compute all strategy metrics from a pd.Series of trade returns.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


def _annualised_return(returns: pd.Series) -> float:
    """Compound annualised return (assumes daily returns, 252 trading days)."""
    total = (1 + returns).prod() - 1
    n     = len(returns)
    if n < 2:
        return float(total)
    return float((1 + total) ** (252 / n) - 1)


def _max_drawdown(returns: pd.Series) -> float:
    """Maximum drawdown as a negative percentage of peak equity."""
    equity = (1 + returns).cumprod()
    peak   = equity.cummax()
    dd     = (equity - peak) / peak
    return float(dd.min())


def _downside_std(returns: pd.Series, target: float = 0.0) -> float:
    neg = returns[returns < target] - target
    if len(neg) == 0:
        return 1e-9
    return float(np.sqrt((neg ** 2).mean()))


def _omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    gains  = (returns[returns > threshold] - threshold).sum()
    losses = abs((returns[returns < threshold] - threshold).sum())
    if losses == 0:
        return float("inf")
    return float(gains / losses)


def _stability_score_from_sharpes(sharpes: list[float]) -> float:
    """1 − normalised std of a list of sharpe values across walk-forward folds."""
    if not sharpes or len(sharpes) < 2:
        return 1.0
    std = float(np.std(sharpes))
    mean = abs(float(np.mean(sharpes))) + 1e-9
    return float(max(0.0, min(1.0, 1.0 - std / mean)))


def compute_full_metrics(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    regime_labels: pd.Series | None = None,
) -> dict:
    """
    Compute all performance metrics from a pd.Series of trade/bar returns.

    Args:
        returns: Series of per-trade or per-bar returns (decimal, e.g. 0.01 = 1%)
        risk_free_rate: annualised risk-free rate (default 0)
        regime_labels: optional Series with same index, values like 'trending'|'ranging'|'volatile'

    Returns full metrics dict.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return _empty_metrics()

    rf_daily = risk_free_rate / 252
    mean_r   = float(returns.mean())
    std_r    = float(returns.std()) or 1e-9

    sharpe  = float((mean_r - rf_daily) / std_r * math.sqrt(252))
    sortino = float((mean_r - rf_daily) / _downside_std(returns) * math.sqrt(252))
    max_dd  = _max_drawdown(returns)
    ann_ret = _annualised_return(returns)
    calmar  = float(ann_ret / abs(max_dd)) if max_dd != 0 else float("inf")

    pos = returns[returns > 0]
    neg = returns[returns < 0]
    win_rate      = float(len(pos) / len(returns)) if len(returns) else 0.0
    avg_win       = float(pos.mean()) if len(pos) else 0.0
    avg_loss      = float(abs(neg.mean())) if len(neg) else 0.0
    profit_factor = float(pos.sum() / abs(neg.sum())) if len(neg) and neg.sum() != 0 else float("inf")
    expectancy    = win_rate * avg_win - (1 - win_rate) * avg_loss
    e_ratio       = float(avg_win / avg_loss) if avg_loss > 0 else float("inf")
    omega         = _omega_ratio(returns)

    # Regime Sharpe breakdown
    regime_sharpe: dict[str, float] = {}
    if regime_labels is not None:
        aligned = returns.align(regime_labels, join="inner")
        ret_al, reg_al = aligned
        for regime in reg_al.unique():
            mask = reg_al == regime
            r_sub = ret_al[mask]
            if len(r_sub) > 1:
                s = float(r_sub.mean() / (r_sub.std() or 1e-9) * math.sqrt(252))
                regime_sharpe[str(regime)] = round(s, 4)

    return {
        "sharpe":           round(sharpe, 4),
        "sortino":          round(sortino, 4),
        "calmar":           round(calmar, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "annualised_return":round(ann_ret * 100, 4),
        "profit_factor":    round(profit_factor, 4),
        "win_rate":         round(win_rate, 4),
        "avg_win_pct":      round(avg_win * 100, 4),
        "avg_loss_pct":     round(avg_loss * 100, 4),
        "expectancy":       round(expectancy, 6),
        "e_ratio":          round(e_ratio, 4),
        "omega":            round(omega, 4),
        "total_trades":     len(returns),
        "regime_sharpe":    regime_sharpe,
        "stability_score":  None,   # populated externally (Phase 11)
        "overfit_cliff_flag": False,
    }


def _empty_metrics() -> dict:
    return {
        "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0,
        "max_drawdown_pct": 0.0, "annualised_return": 0.0,
        "profit_factor": 0.0, "win_rate": 0.0,
        "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
        "expectancy": 0.0, "e_ratio": 0.0, "omega": 0.0,
        "total_trades": 0, "regime_sharpe": {},
        "stability_score": None, "overfit_cliff_flag": False,
    }
