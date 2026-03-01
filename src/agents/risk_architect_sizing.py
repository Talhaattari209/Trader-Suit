"""
Position sizing for Risk Architect (Agent_skill: apply_kelly_sizing).
Fractional Kelly and volatility targeting; can be used by execution layer.
"""
from typing import Optional

from .risk_architect import kelly_fraction, volatility_target_position_size


def apply_kelly_sizing(
    exp_return: float,
    vol_target: float = 0.10,
    risk_tol: float = 0.01,
    fractional: float = 0.5,
) -> float:
    """
    Compute fractional Kelly position size from expected return and volatility target.
    Agent_skill: apply_kelly_sizing for risk-adjusted allocation.

    exp_return: Expected return (e.g. from validation, e.g. 0.10 for 10%).
    vol_target: Volatility target (e.g. 0.10 for 10%).
    risk_tol: Risk tolerance as fraction of capital per trade (e.g. 0.01 = 1%).
    fractional: Fraction of full Kelly (e.g. 0.5 = half-Kelly).

    Returns position size as fraction of capital (capped 0..1).
    """
    if vol_target <= 0:
        return 0.0
    # Kelly-style: f* = mu / sigma^2 for log-wealth; approximate with exp_return/vol_target^2
    kelly = exp_return / (vol_target ** 2)
    kelly = max(0.0, min(kelly, 2.0))  # cap
    return fractional * kelly * risk_tol if risk_tol > 0 else 0.0


def apply_kelly_sizing_from_win_loss(
    win_rate: float,
    win_loss_ratio: float,
    fractional: float = 0.5,
) -> float:
    """Thin wrapper around risk_architect.kelly_fraction for skill compatibility."""
    return kelly_fraction(win_rate, win_loss_ratio, fractional=fractional)


__all__ = [
    "apply_kelly_sizing",
    "apply_kelly_sizing_from_win_loss",
    "volatility_target_position_size",
]
