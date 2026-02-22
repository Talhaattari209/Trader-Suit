"""LLM-based pattern hypothesis (optional)."""
from typing import Optional

try:
    from src.tools.llm_client import BaseLLMClient, AnthropicLLMClient
    import os
    HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))
except ImportError:
    HAS_LLM = False


def generate_pattern_hypothesis(pattern_type: str = "head_and_shoulders") -> str:
    if not HAS_LLM:
        return f"Hypothesis: {pattern_type} patterns predict reversals. Entry on neckline break."
    return f"Hypothesis: {pattern_type} patterns predict reversals. Entry on neckline break."


def generate_strategy_code(refined_hyp: str) -> str:
    return f"# Strategy from: {refined_hyp}\n# Implement entry/exit/risk in BaseStrategy."
