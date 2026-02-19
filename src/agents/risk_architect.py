"""
Risk Architect Agent: position sizing, behavioral guardrails, and SL/TP optimization.
Provides logic used by execution layer for live trading safeguards.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent


# --- Position Sizing ---

def kelly_fraction(
    win_rate: float,
    win_loss_ratio: float,
    fractional: float = 0.5,
) -> float:
    """
    Fractional Kelly Criterion for position sizing.
    win_rate: P(win), win_loss_ratio: avg_win / avg_loss.
    fractional=0.5 -> half-Kelly (common for safety). Returns 0 if invalid.
    """
    if win_loss_ratio <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    # Kelly % = W - (1-W)/R, W=win_rate, R=win_loss_ratio
    kelly = win_rate - (1 - win_rate) / win_loss_ratio
    kelly = max(0.0, min(kelly, 1.0))
    return kelly * fractional


def volatility_target_position_size(
    current_vol_annual: float,
    target_daily_vol_pct: float = 0.05,
    capital: float = 1.0,
) -> float:
    """
    Scale position so that portfolio daily vol ≈ target_daily_vol_pct.
    current_vol_annual: annualized vol of the strategy or asset (e.g. 0.15 for 15%).
    target_daily_vol_pct: e.g. 0.05 for 5% daily vol target.
    capital: 1.0 for fraction of capital, or actual capital for notional.
    Returns position size as fraction of capital (or notional if capital set).
    """
    if current_vol_annual <= 0:
        return 0.0
    # daily_vol_annual = annual_vol / sqrt(252)
    daily_vol = current_vol_annual / (252 ** 0.5)
    if daily_vol <= 0:
        return 0.0
    # scale so position_vol = target -> weight = target_daily_vol_pct / daily_vol
    weight = target_daily_vol_pct / daily_vol
    return min(weight, 2.0) * capital  # cap leverage at 2x


# --- Behavioral Guardrails ---

def cooldown_after_consecutive_losses(
    consecutive_losses: int,
    threshold: int = 3,
) -> bool:
    """
    Returns True if we are in "cool-down" (forced break) after X consecutive losses.
    Caller should block new entries when True.
    """
    return consecutive_losses >= threshold


def max_daily_drawdown_lockout(
    daily_equity: List[float],
    max_dd_pct: float = 0.05,
) -> bool:
    """
    daily_equity: list of equity values at each step today (or high-water marks per bar).
    Returns True if today's drawdown from today's high exceeds max_dd_pct (e.g. 0.05 = 5%).
    Caller should halt trading for the day when True.
    """
    if not daily_equity or max_dd_pct <= 0:
        return False
    arr = np.array(daily_equity)
    peak = np.maximum.accumulate(arr)
    dd = (peak - arr) / np.where(peak != 0, peak, 1)
    return bool(np.any(dd >= max_dd_pct))


# --- SL/TP Optimizer (ATR-based) ---

def atr_series(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range. high, low, close must be aligned (e.g. same index)."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def dynamic_stop_loss_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    atr_period: int = 14,
    atr_multiplier: float = 2.0,
    long_position: bool = True,
) -> pd.Series:
    """
    Dynamic stop-loss distance in price units (not pips).
    For long: stop = close - atr * multiplier. For short: stop = close + atr * multiplier.
    Returns a Series of stop prices (same index as close).
    """
    atr = atr_series(high, low, close, atr_period)
    if long_position:
        return close - atr * atr_multiplier
    return close + atr * atr_multiplier


def dynamic_take_profit_atr(
    close: pd.Series,
    atr: pd.Series,
    atr_multiplier: float = 2.0,
    long_position: bool = True,
) -> pd.Series:
    """Take-profit distance: atr * multiplier above (long) or below (short) entry."""
    if long_position:
        return close + atr * atr_multiplier
    return close - atr * atr_multiplier


# --- Agent (optional: outputs risk config / recommendations) ---

class RiskArchitectAgent(BaseAgent):
    """
    Agent interface for risk architecture. Can perceive current state (equity, params),
    reason about position size and guardrails, and act by writing Risk_Config or recommendations.
    """

    def __init__(
        self,
        vault_path: str,
        kelly_fractional: float = 0.5,
        target_daily_vol_pct: float = 0.05,
        cooldown_loss_threshold: int = 3,
        max_daily_dd_pct: float = 0.05,
        atr_period: int = 14,
        atr_sl_multiplier: float = 2.0,
    ):
        super().__init__("RiskArchitect")
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"
        self.kelly_fractional = kelly_fractional
        self.target_daily_vol_pct = target_daily_vol_pct
        self.cooldown_loss_threshold = cooldown_loss_threshold
        self.max_daily_dd_pct = max_daily_dd_pct
        self.atr_period = atr_period
        self.atr_sl_multiplier = atr_sl_multiplier

    async def perceive(self, input_data: Any) -> Any:
        """
        input_data: dict with optional keys:
          - equity_curve (list or Series), returns (Series), win_rate, win_loss_ratio,
          - daily_equity (list for today), consecutive_losses (int),
          - df (DataFrame with High, Low, Close for ATR).
        """
        return input_data or {}

    async def reason(self, state: Any) -> Dict[str, Any]:
        """Compute position size, guardrail flags, and ATR-based SL suggestion."""
        out = {
            "position_fraction": 0.0,
            "in_cooldown": False,
            "daily_dd_lockout": False,
            "atr_sl_multiplier": self.atr_sl_multiplier,
        }
        if not state:
            return out

        # Kelly
        wr = state.get("win_rate")
        wlr = state.get("win_loss_ratio")
        if wr is not None and wlr is not None:
            out["position_fraction"] = kelly_fraction(
                wr, wlr, fractional=self.kelly_fractional
            )
        # Vol targeting (if current_vol_annual provided)
        vol = state.get("current_vol_annual")
        if vol is not None:
            vol_frac = volatility_target_position_size(
                vol, self.target_daily_vol_pct, capital=1.0
            )
            if vol_frac > 0 and (out["position_fraction"] <= 0 or vol_frac < out["position_fraction"]):
                out["position_fraction"] = vol_frac

        out["in_cooldown"] = cooldown_after_consecutive_losses(
            state.get("consecutive_losses", 0), self.cooldown_loss_threshold
        )
        daily_eq = state.get("daily_equity")
        if daily_eq is not None:
            out["daily_dd_lockout"] = max_daily_drawdown_lockout(
                daily_eq, self.max_daily_dd_pct
            )

        df = state.get("df")
        if df is not None and isinstance(df, pd.DataFrame):
            for col in ["High", "Low", "Close"]:
                if col not in df.columns:
                    df = None
                    break
            if df is not None and len(df) > 0:
                row = df.iloc[-1]
                atr = atr_series(
                    df["High"], df["Low"], df["Close"], self.atr_period
                ).iloc[-1]
                out["last_atr"] = float(atr)
                out["suggested_sl_distance"] = float(atr * self.atr_sl_multiplier)

        return out

    async def act(self, plan: Dict[str, Any]) -> bool:
        """Optionally write Risk_Config to Logs (for audit trail)."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.logs_dir / f"Risk_Config_{ts}.md"
        body = f"""---
type: risk_config
timestamp: {datetime.now().isoformat()}
---

# Risk Architect Output

- Position fraction (Kelly/Vol): {plan.get('position_fraction', 0):.4f}
- In cooldown: {plan.get('in_cooldown', False)}
- Daily DD lockout: {plan.get('daily_dd_lockout', False)}
- ATR SL multiplier: {plan.get('atr_sl_multiplier', 2.0)}
- Suggested SL distance (last bar): {plan.get('suggested_sl_distance', 'N/A')}
"""
        path.write_text(body, encoding="utf-8")
        self.log_action("act", f"Wrote {path.name}")
        return True
