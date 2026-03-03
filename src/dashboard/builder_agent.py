"""
Builder Agent: manages bidirectional sync between Code and Specs in the No-Code Strategy Builder.
- On code submit: re-evaluates code + previous steps → updates specs and returns "what your code is doing".
- On specs change: generates/updates code from specs (specs → code).
Designed to be wired to an LLM/Strategist API later; runs with local heuristics when API is unavailable.
"""

from __future__ import annotations

from typing import List, Tuple


def code_to_specs(
    code: str,
    previous_blocks_specs: List[str],
    step_name: str = "Step",
) -> Tuple[str, str]:
    """
    Re-evaluate code and previous steps to produce specs and a plain-English explanation.
    Returns (specs_text, agent_comment).
    """
    code = (code or "").strip()
    context = " → ".join(previous_blocks_specs) if previous_blocks_specs else ""

    # Heuristic: infer intent from code patterns (stub until LLM/API)
    specs_parts = []
    comment_parts = []

    if "entry" in code.lower() and "state" in code.lower():
        specs_parts.append("Entry logic: signal from state (OHLCV/indicators).")
        if "return True" in code or "return True" in code.replace(" ", ""):
            comment_parts.append("This step defines when to enter a trade based on current state.")
    if "exit" in code.lower() and "state" in code.lower():
        specs_parts.append("Exit logic: close position based on state.")
        comment_parts.append("This step defines when to exit the position.")
    if "risk" in code.lower():
        specs_parts.append("Risk sizing: position size or fraction from state.")
        comment_parts.append("This step sets position size or risk per bar.")
    if "BaseStrategy" in code or "base_strategy" in code.lower():
        specs_parts.append("Implements BaseStrategy (entry, exit, risk).")
        comment_parts.append("Your code implements the strategy interface: entry(), exit(), risk().")
    if "np.mean" in code or "mean(" in code or "sma" in code.lower() or "ema" in code.lower():
        specs_parts.append("Uses moving average (SMA/EMA) for signals.")
        comment_parts.append("This step uses a moving average for trend or signal generation.")
    if "rsi" in code.lower() or "RSI" in code:
        specs_parts.append("Uses RSI indicator (e.g. overbought/oversold).")
        comment_parts.append("This step uses RSI for entry/exit conditions.")
    if "atr" in code.lower() or "ATR" in code:
        specs_parts.append("Uses ATR for volatility or stop distance.")
        comment_parts.append("This step uses ATR for stops or position sizing.")
    if "LSTM" in code or "CNN" in code or "torch" in code.lower():
        specs_parts.append("Uses neural model (LSTM/CNN) for signals.")
        comment_parts.append("This step uses a deep learning model; run on Colab for training.")

    if not specs_parts:
        specs_parts.append("Custom logic (edit specs to describe).")
        comment_parts.append("Describe in specs what this block should do; the agent will keep code and specs in sync.")

    specs_text = " ".join(specs_parts)
    if context:
        specs_text = f"[Previous: {context}] {specs_text}"

    agent_comment = " ".join(comment_parts) if comment_parts else "Code received. Specs updated from code analysis."
    return specs_text, agent_comment


def specs_to_code(
    specs: str,
    previous_blocks_code: List[str],
    step_name: str = "Step",
) -> str:
    """
    Generate or update code from specs (and optional previous block code).
    Returns generated code string.
    """
    specs = (specs or "").strip().lower()
    if not specs:
        return "# Add specs (e.g. 'Entry on RSI<30, exit ATR*2') and click Generate Code"

    # Stub: produce a template that matches common phrases (real impl would call Strategist/LLM)
    lines = ["from src.models.base_strategy import BaseStrategy", ""]

    if "entry" in specs or "rsi" in specs or "atr" in specs:
        lines.extend([
            "class GeneratedStrategy(BaseStrategy):",
            "    def __init__(self):",
            "        pass",
            "",
            "    def entry(self, state: dict) -> bool:",
            "        # TODO: implement from specs",
            "        return False",
            "",
            "    def exit(self, state: dict) -> bool:",
            "        return False",
            "",
            "    def risk(self, state: dict) -> float:",
            "        return 0.01",
        ])
    else:
        lines.extend([
            "# Strategy from specs – implement entry/exit/risk",
            "class GeneratedStrategy(BaseStrategy):",
            "    def entry(self, state): return False",
            "    def exit(self, state): return False",
            "    def risk(self, state): return 0.01",
        ])

    return "\n".join(lines)
