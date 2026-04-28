"""
Autonomous Agent — powers the floating chat widget on all dashboard pages.

Chat Mode  : read-only Q&A about the system (positions, strategies, vault, etc.)
Agent Mode : can also trigger real actions (workflows, Monte Carlo, approvals).

Memory     : session-local only (no cross-session persistence per requirement).
Debug      : every LLM call prints === AUTONOMOUS AGENT PROMPT === /
             === AUTONOMOUS AGENT RESPONSE === to the console (same style as
             existing LLM/MCP debug in llm_client.py).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Logger (console + DataStore/debug.log) ────────────────────────────────────
logger = logging.getLogger("autonomous_agent")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.DEBUG)
    logger.addHandler(_sh)

# ═══════════════════════════════════════════════════════════════════════════════
# System-context builder — collects live state for the LLM prompt
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system_context() -> dict[str, Any]:
    """Collect current system state.  Fast; errors are swallowed gracefully."""
    ctx: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies": [],
        "alphas": [],
        "workflow_state": {},
        "vault_summary": {},
        "price_levels": {},
    }

    try:
        from src.persistence.filesystem_store import FilesystemStore
        store = FilesystemStore()
        ctx["strategies"] = store.load_strategies() or []
        ctx["alphas"] = store.load_alphas() or []
        ctx["workflow_state"] = store.get_workflow_state() or {}
    except Exception as e:
        logger.debug(f"[AutonomousAgent] store read error: {e}")

    try:
        vault = Path(os.environ.get("VAULT_PATH", "AI_Employee_Vault"))
        summary: dict[str, list[str]] = {}
        for folder in ["Needs_Action", "Plans", "Approved", "Reports", "Logs", "Graveyard"]:
            fp = vault / folder
            if fp.exists():
                summary[folder] = [f.name for f in sorted(fp.iterdir()) if f.is_file()]
        ctx["vault_summary"] = summary
    except Exception as e:
        logger.debug(f"[AutonomousAgent] vault scan error: {e}")

    try:
        from src.tools.price_level_detector import detect_all_price_levels
        import pandas as pd
        csv_path = os.environ.get("US30_CSV_PATH", "")
        if csv_path and Path(csv_path).exists():
            df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
            ctx["price_levels"] = detect_all_price_levels(df)
    except Exception as e:
        logger.debug(f"[AutonomousAgent] price levels error: {e}")

    return ctx


def _context_to_text(ctx: dict[str, Any]) -> str:
    strategies = ctx.get("strategies", [])
    alphas = ctx.get("alphas", [])
    wf = ctx.get("workflow_state", {})
    vault = ctx.get("vault_summary", {})
    pl = ctx.get("price_levels", {})

    lines = [
        f"=== LIVE SYSTEM CONTEXT [{ctx['timestamp']}] ===",
        f"Strategies: {len(strategies)} | Alphas: {len(alphas)} | Workflow step: {wf.get('step','idle')}",
    ]
    if strategies:
        rows = [f"  {s.get('strategy_id','?')}({s.get('status','?')})" for s in strategies[:8]]
        lines.append("Strategies: " + " | ".join(rows))
    if alphas:
        lines.append(f"Recent alpha ideas: {[a.get('hypothesis','')[:60] for a in alphas[:3]]}")

    lines.append("Vault:")
    for folder, files in vault.items():
        preview = ", ".join(files[:4]) + ("…" if len(files) > 4 else "")
        lines.append(f"  {folder}/: {len(files)} files [{preview}]")

    if pl:
        lines.append(f"Price levels keys: {list(pl.keys())}")

    if wf.get("circuit_breaker_active"):
        lines.append("⛔  CIRCUIT BREAKER ACTIVE — consecutive loss limit hit.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool catalogue (text injected into the system prompt)
# ═══════════════════════════════════════════════════════════════════════════════

_CHAT_TOOLS = """\
Available tools (Chat Mode — read-only):
  get_positions                     — open positions from Alpaca
  get_strategies(status)            — list strategies (status: draft|production|graveyard|all)
  get_alphas                        — list alpha ideas in DataStore
  get_vault_file(folder, filename)  — read a vault file
  get_metrics                       — current performance metrics
  get_price_levels                  — detected US30 price levels
  get_workflow_state                — current workflow pipeline state
  get_mc_results(strategy_id)       — Monte Carlo / performance metrics for a strategy

To call a tool write exactly on one line:
  TOOL_CALL: {"tool": "<name>", "args": {<key>:<value>, ...}}
Wait for TOOL_RESULT before continuing.
"""

_AGENT_TOOLS = """\
Additional tools (Agent Mode — executes real actions):
  start_workflow(idea)                                          — submit new alpha idea
  run_monte_carlo(strategy_id, iterations)                      — run MC validation
  workflow_decision(workflow_id, strategy_id, decision, tweaks) — approve|discard|retest
  move_to_approved(strategy_id)                                 — trigger HITL approval

⚠  Always describe the action and ask for confirmation before calling an action tool.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Tool executor — runs the named tool and returns a string result
# ═══════════════════════════════════════════════════════════════════════════════

_ACTION_TOOLS = {"start_workflow", "run_monte_carlo", "workflow_decision", "move_to_approved"}


def _execute_tool(tool_name: str, args: dict, mode: str, api_base_url: str) -> str:
    """Execute a single tool call.  Returns result as plain text."""
    import httpx
    timeout = httpx.Timeout(15.0)

    if mode == "chat" and tool_name in _ACTION_TOOLS:
        return "⛔ Action tools are not available in Chat Mode. Switch to Agent Mode to execute actions."

    try:
        if tool_name == "get_positions":
            r = httpx.get(f"{api_base_url}/positions", timeout=timeout)
            data = r.json()
            return json.dumps(data, indent=2) if data else "No open positions."

        if tool_name == "get_strategies":
            status = args.get("status", "all")
            r = httpx.get(f"{api_base_url}/data/strategies?status={status}", timeout=timeout)
            data = r.json()
            return json.dumps(data[:10], indent=2) if data else "No strategies found."

        if tool_name == "get_alphas":
            r = httpx.get(f"{api_base_url}/data/alphas?limit=20", timeout=timeout)
            data = r.json()
            return json.dumps(data[:10], indent=2) if data else "No alpha ideas found."

        if tool_name == "get_vault_file":
            folder = args.get("folder", "")
            filename = args.get("filename", "")
            if not folder or not filename:
                return "Error: folder and filename are required."
            r = httpx.get(f"{api_base_url}/vault/{folder}/{filename}", timeout=timeout)
            if r.status_code == 404:
                return f"File not found: {folder}/{filename}"
            return r.json().get("content", "")[:3000]

        if tool_name == "get_metrics":
            r = httpx.get(f"{api_base_url}/metrics", timeout=timeout)
            return json.dumps(r.json(), indent=2)

        if tool_name == "get_price_levels":
            try:
                from src.tools.price_level_detector import detect_all_price_levels
                import pandas as pd
                csv_path = os.environ.get("US30_CSV_PATH", "")
                if csv_path and Path(csv_path).exists():
                    df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
                    pl = detect_all_price_levels(df)
                    return json.dumps(pl, indent=2, default=str)
            except Exception as e:
                return f"Error fetching price levels: {e}"
            return "No US30 price data available."

        if tool_name == "get_workflow_state":
            r = httpx.get(f"{api_base_url}/workflow/state", timeout=timeout)
            return json.dumps(r.json(), indent=2)

        if tool_name == "get_mc_results":
            strategy_id = args.get("strategy_id", "")
            r = httpx.get(
                f"{api_base_url}/performance/metrics/{strategy_id}", timeout=timeout
            )
            return json.dumps(r.json(), indent=2)

        # ── Agent Mode actions ─────────────────────────────────────────────────

        if tool_name == "start_workflow":
            idea = args.get("idea", "")
            if not idea:
                return "Error: idea text is required."
            r = httpx.post(
                f"{api_base_url}/workflow/start",
                json={"idea": idea},
                timeout=httpx.Timeout(30.0),
            )
            return json.dumps(r.json(), indent=2)

        if tool_name == "run_monte_carlo":
            strategy_id = args.get("strategy_id", "")
            iterations = int(args.get("iterations", 5000))
            r = httpx.post(
                f"{api_base_url}/montecarlo/run",
                json={"strategy_id": strategy_id, "iterations": iterations},
                timeout=httpx.Timeout(120.0),
            )
            result = r.json()
            return json.dumps(
                {k: v for k, v in result.items() if k not in ("ending_values", "max_dd_dist")},
                indent=2,
            )

        if tool_name == "workflow_decision":
            r = httpx.post(
                f"{api_base_url}/workflow/decision",
                json=args,
                timeout=timeout,
            )
            return json.dumps(r.json(), indent=2)

        if tool_name == "move_to_approved":
            strategy_id = args.get("strategy_id", "")
            vault = Path(os.environ.get("VAULT_PATH", "AI_Employee_Vault"))
            approved = vault / "Approved"
            approved.mkdir(parents=True, exist_ok=True)
            approval_file = approved / f"{strategy_id}_approval.md"
            approval_file.write_text(
                f"# Approval Request: {strategy_id}\n\n"
                f"Requested by: Autonomous Agent\n"
                f"Time: {datetime.now(timezone.utc).isoformat()}\n\n"
                "Awaiting HITL review.\n",
                encoding="utf-8",
            )
            return f"✅ Strategy {strategy_id} moved to Approved/ — awaiting HITL sign-off."

        return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Tool execution error [{tool_name}]: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Tool-call parser
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_tool_call(text: str) -> dict | None:
    """Extract the first TOOL_CALL JSON from an LLM response, or None."""
    marker = "TOOL_CALL:"
    if marker not in text:
        return None
    try:
        start = text.index(marker) + len(marker)
        snippet = text[start:].lstrip()
        depth = 0
        end = 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return json.loads(snippet[:end])
    except (ValueError, json.JSONDecodeError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Main async entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def process_message(
    message: str,
    history: list[dict],
    mode: str = "chat",
    api_base_url: str = "http://localhost:8000",
) -> str:
    """
    Process a user message and return the agent's response.

    Args:
        message     : User's input text.
        history     : Conversation so far — list of {"role": "user"|"assistant",
                      "content": "..."}.  Session-local; not persisted.
        mode        : "chat" (read-only) or "agent" (can execute actions).
        api_base_url: FastAPI backend URL.

    Returns:
        Assistant response string.
    """
    from src.tools.llm_client import get_default_llm_client

    llm = get_default_llm_client()

    # ── Build system context ─────────────────────────────────────────────────
    ctx = _build_system_context()
    context_text = _context_to_text(ctx)

    mode_block = (
        "You are in CHAT MODE. Answer questions using context + read-only tools only. "
        "Never execute actions that change system state.\n"
        if mode == "chat"
        else
        "You are in AGENT MODE. You may read data AND execute actions. "
        "Always confirm with the user before calling an action tool.\n"
    )

    tools_block = _CHAT_TOOLS + (_AGENT_TOOLS if mode == "agent" else "")

    system_prompt = f"""\
You are the Trader-Suit Autonomous AI Agent — an embedded copilot for a professional algorithmic trading platform.

{mode_block}
{context_text}

{tools_block}
Guidelines:
• Be concise and precise.  Traders need fast, actionable answers.
• Format metrics clearly: Sharpe 1.45 | Max DD -8.2% | Hit-rate 58%.
• When data is not in context, call the appropriate tool to fetch it.
• In Agent Mode, describe what you are about to do before executing.
• Multi-turn: remember the conversation history provided below.
• If a tool returns an error, explain it and suggest an alternative.
"""

    # ── Build conversation prompt ────────────────────────────────────────────
    history_text = ""
    for msg in history[-10:]:   # keep last 10 turns for context-window economy
        role = msg.get("role", "user").upper()
        content = msg.get("content", "").strip()
        history_text += f"\n{role}: {content}"

    prompt = f"{history_text}\nUSER: {message}\n\nASSISTANT:"

    # ── Debug print ──────────────────────────────────────────────────────────
    print("=" * 60)
    print("=== AUTONOMOUS AGENT PROMPT ===")
    print(f"Mode: {mode} | History turns: {len(history)}")
    print(f"System (first 400 chars): {system_prompt[:400]}")
    print(f"User message: {message}")

    t0 = time.time()
    response = await llm.complete(prompt, system=system_prompt)

    print("=== AUTONOMOUS AGENT RESPONSE ===")
    print(f"Response (first 500 chars): {response[:500]}")
    print(f"Elapsed: {time.time() - t0:.2f}s")

    # ── Tool-call loop (max 4 iterations) ───────────────────────────────────
    for iteration in range(4):
        tc = _parse_tool_call(response)
        if tc is None:
            break

        tool_name = tc.get("tool", "")
        tool_args = tc.get("args", {})

        print(f"[AutonomousAgent] tool call #{iteration + 1}: {tool_name}({tool_args})")
        result = _execute_tool(tool_name, tool_args, mode, api_base_url)
        print(f"[AutonomousAgent] tool result (first 200): {result[:200]}")

        # Strip the TOOL_CALL line from the response so we don't repeat it
        before_tc = response[: response.index("TOOL_CALL:")].rstrip()

        follow_up = (
            f"{prompt}\n{before_tc}\nTOOL_CALL: {json.dumps({'tool': tool_name, 'args': tool_args})}"
            f"\nTOOL_RESULT: {result}\n\nASSISTANT:"
        )

        t1 = time.time()
        response = await llm.complete(follow_up, system=system_prompt)

        print(f"=== AUTONOMOUS AGENT TOOL RESPONSE (iter {iteration + 1}) ===")
        print(f"Response (first 500 chars): {response[:500]}")
        print(f"Elapsed: {time.time() - t1:.2f}s")

    return response.strip()
