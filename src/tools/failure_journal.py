"""
Structured failure journal entries for strategy graveyard (Paradigms Task 1).
Builds journal dict for Neon strategy_graveyard.context: failure_mode, alpha_decay_reason, metrics_json, etc.
"""
from datetime import datetime
from typing import Any, Dict, Optional


FAILURE_MODES = (
    "overfitting",
    "alpha_decay",
    "regime_shift",
    "insufficient_edge",
    "parameter_instability",
    "other",
)


def build_journal_entry(
    strategy_id: str,
    reason: str,
    decision: str,
    metrics_pre: Optional[Dict[str, Any]] = None,
    metrics_post: Optional[Dict[str, Any]] = None,
    failure_mode: Optional[str] = None,
    alpha_decay_reason: Optional[str] = None,
    description: Optional[str] = None,
    limitations: Optional[str] = None,
    mitigation: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a structured journal entry for the graveyard (Paradigms Task 1).

    strategy_id: e.g. strategy class name or draft filename.
    reason: Killer decision reason string.
    decision: REJECT | FLAG.
    metrics_pre/post: optional dicts (e.g. in_sample_sharpe, out_of_sample_sharpe).
    failure_mode: one of FAILURE_MODES; inferred from reason if not set.
    alpha_decay_reason: optional (e.g. volume, volatility, regime_change, timeframe).
    """
    if failure_mode is None:
        failure_mode = _infer_failure_mode(reason, decision)
    metrics_json = {
        "pre": metrics_pre or {},
        "post": metrics_post or {},
    }
    entry = {
        "date": datetime.utcnow().isoformat() + "Z",
        "strategy_id": strategy_id,
        "failure_mode": failure_mode,
        "alpha_decay_reason": alpha_decay_reason,
        "metrics_json": metrics_json,
        "description": description or reason,
        "limitations": limitations,
        "mitigation": mitigation,
        "decision": decision,
    }
    return entry


def _infer_failure_mode(reason: str, decision: str) -> str:
    r = (reason or "").lower()
    if "overfit" in r or "parameter stability" in r or "nudge" in r:
        return "overfitting"
    if "prob_of_ruin" in r or "drawdown" in r or "dd" in r:
        return "insufficient_edge"
    if "regime" in r:
        return "regime_shift"
    if "decay" in r or "crowd" in r:
        return "alpha_decay"
    if "return" in r and ("10%" in r or "target" in r):
        return "insufficient_edge"
    return "other"
