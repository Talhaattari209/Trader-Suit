"""
Instruction Router: turns a user prompt into a Needs_Action research request.
Uses edge_registry to suggest edge_type(s); optionally uses LLM to refine the request.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from src.edges.edge_registry import (
    EDGE_REGISTRY,
    match_instruction_to_edges,
    get_edge_info,
    EdgeInfo,
)
import os


SYSTEM_INSTRUCTION_ROUTER = """You are a research coordinator. Given a user's trading/quant idea, you produce a short research request that will be read by a Librarian Agent.

Output:
1. A one-paragraph "research request" that captures the user's intent (what edge or strategy they want).
2. A single recommended edge_type from this list: statistical, pattern_based, volume_based, market_structure, tokenized_assets, geopolitical, prediction_event, ai_enhanced.
3. One-line title (slug) for the task.

Format your response exactly as:
EDGE_TYPE: <edge_type>
TITLE: <short title>
---
<research request paragraph>"""


async def _refine_with_llm(instruction: str, llm: Optional[Any] = None) -> str:
    """Use LLM to produce a structured research request and edge_type."""
    if llm is None:
        try:
            if os.environ.get("ANTHROPIC_API_KEY"):
                from src.tools.llm_client import AnthropicLLMClient
                llm = AnthropicLLMClient()
            elif os.environ.get("GEMINI_API_KEY"):
                from src.tools.llm_client import GeminiLLMClient
                llm = GeminiLLMClient()
            else:
                from src.tools.llm_client import AnthropicLLMClient
                llm = AnthropicLLMClient()
        except Exception:
            raise
    prompt = f"User instruction:\n{instruction}\n\nProduce the research request and edge type as specified."
    out = await llm.complete(prompt, system=SYSTEM_INSTRUCTION_ROUTER)
    return out.strip()


def _fallback_research_request(instruction: str, matched: List[EdgeInfo]) -> str:
    """Build a research request without LLM using keyword-matched edges."""
    edge_type = matched[0].edge_type if matched else "statistical"
    return f"EDGE_TYPE: {edge_type}\nTITLE: User instruction\n---\nImplement or research the following idea: {instruction}"


def write_instruction_to_vault(
    vault_path: str,
    research_request_content: str,
    *,
    filename_prefix: str = "instruction",
    write_to_needs_action: bool = True,
) -> Path:
    """
    Write the research request so the Librarian will pick it up.
    If write_to_needs_action is True (default), write directly to Needs_Action
    so the Librarian sees the full content (EDGE_TYPE + request). Otherwise
    write to Needs_Action/ResearchInput for the Watcher to process.
    """
    vault = Path(vault_path)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if write_to_needs_action:
        needs = vault / "Needs_Action"
        needs.mkdir(parents=True, exist_ok=True)
        path = needs / f"{filename_prefix}_{timestamp}.md"
    else:
        input_dir = vault / "Needs_Action" / "ResearchInput"
        input_dir.mkdir(parents=True, exist_ok=True)
        path = input_dir / f"{filename_prefix}_{timestamp}.md"
    path.write_text(research_request_content, encoding="utf-8")
    return path


def _parse_edge_type_from_content(content: str) -> Optional[str]:
    """Extract EDGE_TYPE: <value> from first lines of content."""
    for line in content.splitlines():
        line = line.strip()
        if line.upper().startswith("EDGE_TYPE:"):
            return line.split(":", 1)[1].strip().lower()
    return None


async def run_instruction(
    user_instruction: str,
    vault_path: str,
    *,
    use_llm: bool = True,
    llm: Optional[Any] = None,
) -> tuple[Path, List[EdgeInfo]]:
    """
    Route user instruction to the vault.
    1. If use_llm, call LLM to get EDGE_TYPE + research request; else use keyword match.
    2. Write result to vault_path/Needs_Action/ResearchInput/instruction_<timestamp>.md.
    Returns (path_written, list of matched EdgeInfo).
    """
    if use_llm and (llm is not None or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        try:
            content = await _refine_with_llm(user_instruction, llm)
        except Exception:
            matched = match_instruction_to_edges(user_instruction)
            content = _fallback_research_request(user_instruction, matched)
    else:
        matched = match_instruction_to_edges(user_instruction)
        content = _fallback_research_request(user_instruction, matched)
    path = write_instruction_to_vault(vault_path, content)
    edge_type = _parse_edge_type_from_content(content)
    info = get_edge_info(edge_type) if edge_type else None
    matched = [info] if info else match_instruction_to_edges(user_instruction)
    return path, matched
