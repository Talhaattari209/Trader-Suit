"""
src/autonomous_agent/agent_core.py
====================================
Core LLM orchestration for the Autonomous Agent.

FLOW PER USER MESSAGE:
  1. Build live system context (context_builder.py).
  2. Assemble system prompt  (mode block + context + tool catalogue).
  3. Build conversation prompt from history + new user message.
  4. Debug-print the full prompt  (=== AUTONOMOUS AGENT PROMPT ===).
  5. Call the LLM (GeminiLLMClient by default — no Anthropic key needed).
  6. Parse for TOOL_CALL markers; execute each tool; feed result back to LLM.
     Repeat up to MAX_TOOL_ITERATIONS to prevent infinite loops.
  7. Debug-print each response   (=== AUTONOMOUS AGENT RESPONSE ===).
  8. Return the final response string to the caller.

MULTI-TURN MEMORY:
  The caller passes in the full history list.  We keep only the last
  HISTORY_WINDOW turns before injecting into the prompt to manage token budget.
  History is stored in the Streamlit session (or the JS sessionStorage for the
  widget) — not in a database — because it is ephemeral trading-session context.

DEBUG LOGGING:
  Every LLM call and tool call is printed with === delimiters matching the
  existing style in src/tools/llm_client.py so all debug output looks uniform.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger("autonomous_agent.core")

# Keep only the last N conversation turns in the prompt.
# 10 turns × ~100 tokens/turn = ~1 000 tokens — leaves room for context + tools.
HISTORY_WINDOW: int = 10

# Safety cap: stop the tool-call loop after this many iterations.
# Prevents runaway loops if the LLM keeps generating TOOL_CALL lines.
MAX_TOOL_ITERATIONS: int = 5


# ─────────────────────────────────────────────────────────────────────────────
# System prompt assembler
# ─────────────────────────────────────────────────────────────────────────────

def _build_system_prompt(context_text: str, mode: str) -> str:
    """
    Assemble the full system prompt for a single inference call.

    Sections (in order):
      1. Role + mode declaration  — the LLM needs to know who it is *first*
      2. Live system context      — what's actually in the system right now
      3. Tool catalogue           — what actions the LLM is allowed to take
      4. Behavioural guidelines   — formatting + safety rules

    WHY rebuild every call?
      The context block contains live data (equity, positions, workflow state).
      Caching a stale system prompt would give the user outdated information
      with no indication it's stale — worse than no data at all.
    """
    from src.autonomous_agent.tools import CHAT_TOOLS_PROMPT, AGENT_TOOLS_PROMPT

    # Mode declaration — must come before context so the LLM is oriented first
    if mode == "agent":
        mode_declaration = (
            "You are in AGENT MODE.\n"
            "You may read data AND execute real actions (workflows, orders, approvals).\n"
            "⚠  ALWAYS describe what you are about to do and ask for user confirmation "
            "before calling any action tool.  Never execute without consent.\n"
        )
        # In agent mode, expose both read and action tools
        tools_block = CHAT_TOOLS_PROMPT + "\n" + AGENT_TOOLS_PROMPT
    else:
        # Default: Chat Mode — safe for all users, no side effects
        mode_declaration = (
            "You are in CHAT MODE.\n"
            "Answer questions using the live context and read-only tools only.\n"
            "You CANNOT execute actions that change system state.\n"
        )
        tools_block = CHAT_TOOLS_PROMPT                    # action tools omitted entirely

    return f"""\
You are the Trader-Suit Autonomous AI Agent — an embedded Copilot for a professional
algorithmic trading platform.  You have full read access to the entire system:
positions, strategies, vault, price levels, Monte Carlo results, and more.

{mode_declaration}
{context_text}

{tools_block}

=== BEHAVIOURAL GUIDELINES ===
• Be concise and precise.  Traders need fast, actionable answers — not essays.
• Format metrics on one line:  Sharpe 1.45 | Max DD -8.2% | Hit-rate 58%.
• When a user asks for data not in the context, call the appropriate read tool.
• After a TOOL_RESULT, synthesise the result into a human-readable answer.
• Never fabricate data.  If something is unavailable, say so and explain why.
• In Agent Mode: confirm the action in plain English before writing TOOL_CALL.
• Multi-turn: use the conversation history to avoid repeating yourself.
• If a tool returns an error, acknowledge it and suggest the next step.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Conversation prompt assembler
# ─────────────────────────────────────────────────────────────────────────────

def _build_conversation_prompt(history: list[dict[str, Any]], user_message: str) -> str:
    """
    Format the conversation history + new user message into a prompt string.

    We use a plain-text format (ROLE: content) rather than the OpenAI
    messages-array format because:
      1. GeminiLLMClient's complete() accepts a single string prompt.
      2. The plain-text format is transparent — easy to inspect in debug logs.
      3. It works identically with any LLM backend we might swap in later.
    """
    lines: list[str] = []
    # Limit history to avoid exceeding context window
    for turn in history[-HISTORY_WINDOW:]:
        role    = turn.get("role", "user").upper()       # "USER" or "ASSISTANT"
        content = turn.get("content", "").strip()
        lines.append(f"{role}: {content}")

    lines.append(f"USER: {user_message}")
    lines.append("ASSISTANT:")                           # signal the model to continue here
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main async entry point
# ─────────────────────────────────────────────────────────────────────────────

async def process_message(
    message: str,
    history: list[dict[str, Any]],
    mode: str = "chat",
    api_base_url: str = "http://localhost:8000",
) -> str:
    """
    Process a user message through the full agent pipeline and return the response.

    Args:
        message      : The new user input text.
        history      : Conversation so far — list of {"role": str, "content": str}.
                       Caller is responsible for persisting this between requests.
        mode         : "chat" (read-only) or "agent" (can execute actions).
        api_base_url : FastAPI backend base URL (used by tool executor).

    Returns:
        The agent's final response as a plain string (may contain markdown).

    The function is async because GeminiLLMClient.complete() is async.
    The tool executor is synchronous (uses httpx.get/post, not async variants)
    because tool calls happen sequentially and blocking is acceptable here —
    they never run in a tight async loop.
    """
    from src.tools.llm_client import get_default_llm_client      # Gemini by default
    from src.autonomous_agent.context_builder import build_context, to_text
    from src.autonomous_agent.tools import parse_tool_call, execute_tool

    llm = get_default_llm_client()                               # GeminiLLMClient instance

    # ── Step 1: Build live system context ─────────────────────────────────────
    ctx          = build_context()                               # reads FS, Alpaca, CSV
    context_text = to_text(ctx)                                  # compact text representation

    # ── Step 2: Assemble system prompt ────────────────────────────────────────
    system_prompt = _build_system_prompt(context_text, mode)

    # ── Step 3: Build conversation prompt ─────────────────────────────────────
    conv_prompt = _build_conversation_prompt(history, message)

    # ── Step 4: Debug print (matches === style in llm_client.py) ──────────────
    print("=" * 60)
    print("=== AUTONOMOUS AGENT PROMPT ===")
    print(f"Mode: {mode}  |  History turns: {len(history)}  |  Model: {llm.__class__.__name__}")
    # Print first 500 chars of system prompt — full prompt may be thousands of chars
    print(f"System (first 500 chars):\n{system_prompt[:500]}")
    print(f"User message: {message}")

    # ── Step 5: First LLM call ────────────────────────────────────────────────
    t0       = time.time()
    response = await llm.complete(conv_prompt, system=system_prompt)
    elapsed  = time.time() - t0

    print("=== AUTONOMOUS AGENT RESPONSE ===")
    print(f"Response (first 500 chars): {response[:500]}")
    print(f"Elapsed: {elapsed:.2f}s")

    # ── Step 6: Tool-call loop ────────────────────────────────────────────────
    # After each tool call we re-inject the result and ask the LLM to continue.
    # The loop terminates when:
    #   (a) the LLM produces a response with no TOOL_CALL → natural end, or
    #   (b) we hit MAX_TOOL_ITERATIONS → safety brake.
    for iteration in range(MAX_TOOL_ITERATIONS):
        tool_call = parse_tool_call(response)     # returns None if no TOOL_CALL found
        if tool_call is None:
            break                                  # clean final answer; exit loop

        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {})

        print(f"[AutonomousAgent] tool call #{iteration + 1}: {tool_name}({json.dumps(tool_args)})")

        # Execute the tool (read or action, depending on mode)
        tool_result = execute_tool(
            tool_name    = tool_name,
            args         = tool_args,
            mode         = mode,
            api_base_url = api_base_url,
        )

        print(f"[AutonomousAgent] tool result (first 200): {tool_result[:200]}")

        # ── Construct follow-up prompt with tool result appended ───────────────
        # Strip the TOOL_CALL line from the response so it isn't echoed back
        tc_start = response.index("TOOL_CALL:")
        response_before_tc = response[:tc_start].rstrip()

        follow_up_prompt = (
            f"{conv_prompt}\n"
            f"{response_before_tc}\n"
            f"TOOL_CALL: {json.dumps({'tool': tool_name, 'args': tool_args})}\n"
            f"TOOL_RESULT: {tool_result}\n\n"
            "ASSISTANT:"
        )

        # ── Second LLM call: synthesise tool result into the response ──────────
        t1       = time.time()
        response = await llm.complete(follow_up_prompt, system=system_prompt)
        elapsed1 = time.time() - t1

        print(f"=== AUTONOMOUS AGENT TOOL RESPONSE (iter {iteration + 1}) ===")
        print(f"Response (first 500 chars): {response[:500]}")
        print(f"Elapsed: {elapsed1:.2f}s")

    # ── Step 7: Return cleaned final response ─────────────────────────────────
    return response.strip()
