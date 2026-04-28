"""
src/autonomous_agent/tools.py
==============================
Tool catalogue and executor for the Autonomous Agent.

ARCHITECTURE RATIONALE:
  The LLM cannot directly call Python functions — it generates text.
  We use a text-based protocol where the model writes:
      TOOL_CALL: {"tool": "<name>", "args": {…}}
  and we parse + execute it here.  This pattern (sometimes called "ReAct")
  keeps the LLM stateless and lets us audit every action in the log.

TWO PERMISSION LEVELS:
  Chat Mode  → only _READ_TOOLS are callable.  No side effects.  Safe for
               any user to run without confirmation dialogs.
  Agent Mode → _READ_TOOLS + _ACTION_TOOLS.  Side effects (orders, file moves,
               workflow triggers).  Each action tool must confirm before executing.

WHY NOT use function-calling / tool_use APIs?
  Gemini 1.5-flash's function-calling API adds a JSON schema layer that complicates
  streaming and costs more tokens per call.  The text-based TOOL_CALL protocol is
  model-agnostic (works identically with Gemini, Claude, GPT) and easier to debug.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("autonomous_agent.tools")

# ─────────────────────────────────────────────────────────────────────────────
# Tool catalogues (injected verbatim into the system prompt)
# ─────────────────────────────────────────────────────────────────────────────

# Tools available in BOTH modes (read-only, no side-effects)
CHAT_TOOLS_PROMPT = """\
=== AVAILABLE TOOLS (Chat Mode — read-only) ===
Call a tool by writing EXACTLY this on one line, then stop and wait for TOOL_RESULT:
  TOOL_CALL: {"tool": "<name>", "args": {<key>: <value>}}

── ALPACA (live broker data) ──────────────────────────────────────────────────
  get_positions(account)              — open positions from Alpaca account 1 or 2
  get_account_info(account)           — equity, cash, buying power for account 1 or 2
  get_orders(account, limit)          — recent order history (default limit=20)
  get_portfolio_history(account, days)— daily P&L history (default days=30)

── SYSTEM / VAULT ─────────────────────────────────────────────────────────────
  get_alphas(limit)                   — alpha ideas in DataStore (default limit=20)
  get_vault_file(folder, filename)    — read any vault file (folder=Plans|Logs|etc.)
  get_metrics()                       — live performance metrics from FastAPI
  get_price_levels()                  — US30 liquidity zones, FVG, session H/L/M
  get_workflow_state()                — current workflow pipeline step + alpha id
  get_mc_results(strategy_id)         — Monte Carlo / performance metrics for a strategy

── DATABASE — STRATEGIES ──────────────────────────────────────────────────────
  db_list_strategies(status, symbol, regime)  — list strategies (all fields optional)
  db_get_strategy(strategy_id)                — get full strategy record by ID

── DATABASE — POSITIONS ───────────────────────────────────────────────────────
  db_list_positions(status, broker, symbol)   — list positions (status: open|closed|all)
  db_get_position(position_id)                — get full position record by ID

── DATABASE — TRADES ──────────────────────────────────────────────────────────
  db_list_trades(symbol, broker, strategy_id, status, limit) — list trade log
  db_get_trade(trade_id)                      — get full trade record by ID
  db_pnl_summary(symbol, broker, strategy_id)— aggregated P&L stats from trade log
"""

# Additional tools available ONLY in Agent Mode (have side-effects)
AGENT_TOOLS_PROMPT = """\
=== ADDITIONAL TOOLS (Agent Mode — executes real actions) ===
⚠  Describe what you are about to do and ask for user confirmation before calling.

── WORKFLOW ACTIONS ───────────────────────────────────────────────────────────
  start_workflow(idea)                                      — submit new alpha idea into pipeline
  run_monte_carlo(strategy_id, iterations)                  — run MC validation (default 5000)
  workflow_decision(workflow_id, strategy_id, decision)     — approve|discard|retest a strategy
  move_to_approved(strategy_id)                             — place strategy in Approved/ (HITL)

── TRADING ────────────────────────────────────────────────────────────────────
  place_paper_order(symbol, qty, side, account)             — paper trade via Alpaca (side=buy|sell)

── DATABASE — STRATEGIES (write) ──────────────────────────────────────────────
  db_add_strategy(name, status, symbol, timeframe, regime, params, performance, notes)
  db_update_strategy(strategy_id, updates_dict)             — merge fields into a strategy
  db_update_strategy_status(strategy_id, new_status)        — draft|production|graveyard
  db_delete_strategy(strategy_id)                           — permanent delete (prefer graveyard)

── DATABASE — POSITIONS (write) ───────────────────────────────────────────────
  db_upsert_position(data_dict)                             — create or sync a position snapshot
  db_close_position(position_id, close_price, realized_pl)  — mark position as closed
  db_update_sl_tp(position_id, sl, tp)                      — update stop-loss / take-profit

── DATABASE — TRADES (write) ──────────────────────────────────────────────────
  db_log_trade(data_dict)                                   — append a trade to the trade log
  db_update_trade(trade_id, updates_dict)                   — update trade fields (e.g. realized_pl)
"""

# Tools that mutate state — used by the executor to enforce mode restrictions.
# ANY tool not in this set is considered read-only and safe in Chat Mode.
_ACTION_TOOLS: frozenset[str] = frozenset({
    # Workflow actions
    "start_workflow",
    "run_monte_carlo",
    "workflow_decision",
    "move_to_approved",
    # Trading
    "place_paper_order",
    # Database — write operations (strategies)
    "db_add_strategy",
    "db_update_strategy",
    "db_update_strategy_status",
    "db_delete_strategy",
    # Database — write operations (positions)
    "db_upsert_position",
    "db_close_position",
    "db_update_sl_tp",
    # Database — write operations (trades)
    "db_log_trade",
    "db_update_trade",
})

# ─────────────────────────────────────────────────────────────────────────────
# TOOL_CALL parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_tool_call(text: str) -> dict[str, Any] | None:
    """
    Extract the first TOOL_CALL JSON block from an LLM response.

    We use brace-counting instead of a regex to handle nested JSON objects
    robustly.  A regex approach would fail on values like {"a": {"b": 1}}.

    Returns None if no TOOL_CALL marker is present (normal final response).
    Logs a warning if the marker is present but the JSON is malformed (model
    hallucination / truncation) so we can improve the prompt if this recurs.
    """
    marker = "TOOL_CALL:"
    if marker not in text:
        return None                             # clean final answer — no tool call

    try:
        start   = text.index(marker) + len(marker)
        snippet = text[start:].lstrip()         # skip whitespace after the colon

        # Walk character-by-character to find the matching closing brace
        depth, end = 0, 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1                      # entering a JSON object
            elif ch == "}":
                depth -= 1
                if depth == 0:                  # found the outermost closing brace
                    end = i + 1
                    break

        payload = json.loads(snippet[:end])
        if "tool" not in payload:
            logger.warning("[Tools] TOOL_CALL missing 'tool' key: %s", payload)
            return None
        return payload
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("[Tools] Failed to parse TOOL_CALL JSON: %s — raw: %s", exc, text[:200])
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Tool executor
# ─────────────────────────────────────────────────────────────────────────────

def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    mode: str,                # "chat" | "agent"
    api_base_url: str,        # FastAPI base URL for endpoints we proxy
) -> str:
    """
    Dispatch a tool call and return the result as plain text.

    Design decisions:
      - Returns a STRING (not a dict) so the result can be appended verbatim
        to the prompt without an extra json.dumps() call in the hot path.
      - Never raises — exceptions become error strings the LLM can reason about.
      - Mode check happens HERE (not in the router) so the protection applies
        regardless of how this function is called.
    """
    import httpx
    # 15-second timeout for read tools; action tools get 120 seconds (MC runs slow)
    read_timeout   = httpx.Timeout(15.0)
    action_timeout = httpx.Timeout(120.0)

    # ── Mode gate: block action tools in Chat Mode ────────────────────────────
    if mode == "chat" and tool_name in _ACTION_TOOLS:
        return (
            f"⛔ '{tool_name}' is an action tool and cannot run in Chat Mode. "
            "Switch to Agent Mode to execute real actions."
        )

    try:
        # ──────────────────────────────────────────────────────────────────────
        # READ TOOLS
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "get_positions":
            # Delegates to our dedicated alpaca_client (bypasses FastAPI layer)
            from src.autonomous_agent.alpaca_client import get_open_positions
            account = int(args.get("account", 1))     # default account 1
            positions = get_open_positions(account=account)
            return json.dumps(positions, indent=2) if positions else "No open positions."

        if tool_name == "get_account_info":
            from src.autonomous_agent.alpaca_client import get_account_info
            account = int(args.get("account", 1))
            info = get_account_info(account=account)
            return json.dumps(info, indent=2)

        if tool_name == "get_orders":
            from src.autonomous_agent.alpaca_client import get_recent_orders
            account = int(args.get("account", 1))
            limit   = int(args.get("limit", 20))
            orders  = get_recent_orders(account=account, limit=limit)
            return json.dumps(orders, indent=2) if orders else "No orders found."

        if tool_name == "get_portfolio_history":
            from src.autonomous_agent.alpaca_client import get_portfolio_history
            account = int(args.get("account", 1))
            days    = int(args.get("days", 30))
            history = get_portfolio_history(account=account, days=days)
            return json.dumps(history, indent=2) if history else "No history available."

        if tool_name == "get_strategies":
            # Fetch from our own FastAPI endpoint — centralised data layer
            status = args.get("status", "all")
            r = httpx.get(
                f"{api_base_url}/data/strategies",
                params={"status": status},
                timeout=read_timeout,
            )
            data = r.json()
            return json.dumps(data[:15], indent=2) if data else "No strategies found."

        if tool_name == "get_alphas":
            limit = int(args.get("limit", 20))
            r = httpx.get(
                f"{api_base_url}/data/alphas",
                params={"limit": limit},
                timeout=read_timeout,
            )
            data = r.json()
            return json.dumps(data[:15], indent=2) if data else "No alpha ideas found."

        if tool_name == "get_vault_file":
            folder   = str(args.get("folder", ""))
            filename = str(args.get("filename", ""))
            if not folder or not filename:
                return "Error: both 'folder' and 'filename' are required."
            r = httpx.get(
                f"{api_base_url}/vault/{folder}/{filename}",
                timeout=read_timeout,
            )
            if r.status_code == 404:
                return f"File not found: {folder}/{filename}"
            content = r.json().get("content", "")
            # Cap at 3 000 chars to avoid flooding the context window
            return content[:3000] + ("\n[… truncated …]" if len(content) > 3000 else "")

        if tool_name == "get_metrics":
            r = httpx.get(f"{api_base_url}/metrics", timeout=read_timeout)
            return json.dumps(r.json(), indent=2)

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE READ TOOLS — strategies
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_list_strategies":
            from src.autonomous_agent.database import AgentDatabase
            db     = AgentDatabase()
            status = args.get("status")    or None   # None = all statuses
            symbol = args.get("symbol")    or None
            regime = args.get("regime")    or None
            rows   = db.list_strategies(status=status, symbol=symbol, regime=regime)
            if not rows:
                return f"No strategies found (filter: status={status}, symbol={symbol}, regime={regime})."
            return json.dumps(rows, indent=2, default=str)

        if tool_name == "db_get_strategy":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            sid = str(args.get("strategy_id", ""))
            if not sid:
                return "Error: 'strategy_id' is required."
            row = db.get_strategy(sid)
            return json.dumps(row, indent=2, default=str) if row else f"Strategy '{sid}' not found."

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE READ TOOLS — positions
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_list_positions":
            from src.autonomous_agent.database import AgentDatabase
            db     = AgentDatabase()
            status = str(args.get("status", "open"))   # default: open positions only
            broker = args.get("broker") or None
            symbol = args.get("symbol") or None
            rows   = db.list_positions(status=status, broker=broker, symbol=symbol)
            if not rows:
                return f"No positions found (status={status}, broker={broker}, symbol={symbol})."
            return json.dumps(rows, indent=2, default=str)

        if tool_name == "db_get_position":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            pid = str(args.get("position_id", ""))
            if not pid:
                return "Error: 'position_id' is required."
            row = db.get_position(pid)
            return json.dumps(row, indent=2, default=str) if row else f"Position '{pid}' not found."

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE READ TOOLS — trades
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_list_trades":
            from src.autonomous_agent.database import AgentDatabase
            db          = AgentDatabase()
            symbol      = args.get("symbol")      or None
            broker      = args.get("broker")      or None
            strategy_id = args.get("strategy_id") or None
            status      = args.get("status")      or None
            limit       = int(args.get("limit", 50))
            rows = db.list_trades(
                symbol=symbol, broker=broker,
                strategy_id=strategy_id, status=status, limit=limit,
            )
            if not rows:
                return "No trades found matching the given filters."
            return json.dumps(rows, indent=2, default=str)

        if tool_name == "db_get_trade":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            tid = str(args.get("trade_id", ""))
            if not tid:
                return "Error: 'trade_id' is required."
            row = db.get_trade(tid)
            return json.dumps(row, indent=2, default=str) if row else f"Trade '{tid}' not found."

        if tool_name == "db_pnl_summary":
            from src.autonomous_agent.database import AgentDatabase
            db          = AgentDatabase()
            symbol      = args.get("symbol")      or None
            broker      = args.get("broker")      or None
            strategy_id = args.get("strategy_id") or None
            summary = db.pnl_summary(symbol=symbol, broker=broker, strategy_id=strategy_id)
            return json.dumps(summary, indent=2)

        if tool_name == "get_price_levels":
            # Compute locally — no HTTP round-trip; data stays in process
            from src.tools.price_level_detector import detect_all_price_levels
            import pandas as pd
            csv_path = os.environ.get("US30_CSV_PATH", "")
            if not csv_path or not Path(csv_path).exists():
                return "No US30 CSV path configured or file not found."
            df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
            df = df.iloc[-5000:] if len(df) > 5000 else df   # limit for speed
            levels = detect_all_price_levels(df)
            return json.dumps(levels, indent=2, default=str)

        if tool_name == "get_workflow_state":
            r = httpx.get(f"{api_base_url}/workflow/state", timeout=read_timeout)
            return json.dumps(r.json(), indent=2)

        if tool_name == "get_mc_results":
            strategy_id = str(args.get("strategy_id", ""))
            if not strategy_id:
                return "Error: 'strategy_id' is required."
            r = httpx.get(
                f"{api_base_url}/performance/metrics/{strategy_id}",
                timeout=read_timeout,
            )
            return json.dumps(r.json(), indent=2)

        # ──────────────────────────────────────────────────────────────────────
        # ACTION TOOLS (Agent Mode only — already gated above)
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "start_workflow":
            idea = str(args.get("idea", "")).strip()
            if not idea:
                return "Error: 'idea' text is required."
            r = httpx.post(
                f"{api_base_url}/workflow/start",
                json={"idea": idea},
                timeout=action_timeout,
            )
            return json.dumps(r.json(), indent=2)

        if tool_name == "run_monte_carlo":
            strategy_id = str(args.get("strategy_id", ""))
            iterations  = int(args.get("iterations", 5000))
            if not strategy_id:
                return "Error: 'strategy_id' is required."
            r = httpx.post(
                f"{api_base_url}/montecarlo/run",
                json={"strategy_id": strategy_id, "iterations": iterations},
                timeout=action_timeout,
            )
            result = r.json()
            # Strip raw distribution arrays — they are huge and not useful in chat
            stripped = {k: v for k, v in result.items() if k not in ("ending_values", "max_dd_dist")}
            return json.dumps(stripped, indent=2)

        if tool_name == "workflow_decision":
            r = httpx.post(
                f"{api_base_url}/workflow/decision",
                json=args,
                timeout=read_timeout,
            )
            return json.dumps(r.json(), indent=2)

        if tool_name == "move_to_approved":
            strategy_id = str(args.get("strategy_id", ""))
            if not strategy_id:
                return "Error: 'strategy_id' is required."
            vault    = Path(os.environ.get("VAULT_PATH", "AI_Employee_Vault"))
            approved = vault / "Approved"
            approved.mkdir(parents=True, exist_ok=True)      # create folder if absent
            ts_str  = datetime.now(timezone.utc).isoformat()
            approval_file = approved / f"{strategy_id}_approval.md"
            # Write a human-readable approval request for the HITL reviewer
            approval_file.write_text(
                f"# Approval Request: {strategy_id}\n\n"
                f"**Requested by:** Autonomous Agent (Agent Mode)\n"
                f"**Timestamp:** {ts_str}\n\n"
                "## Status\n"
                "Awaiting Human-In-The-Loop (HITL) sign-off.\n\n"
                "## Instructions\n"
                "Review strategy metrics in DataStore/strategies/.  "
                "Delete this file to discard or move to Approved/ manually.\n",
                encoding="utf-8",
            )
            return (
                f"✅ Approval request written → Approved/{strategy_id}_approval.md\n"
                "Awaiting HITL sign-off."
            )

        if tool_name == "place_paper_order":
            symbol  = str(args.get("symbol", "")).upper().strip()
            qty     = float(args.get("qty", 0))
            side    = str(args.get("side", "buy")).lower()
            account = int(args.get("account", 1))

            if not symbol:
                return "Error: 'symbol' is required."
            if qty <= 0:
                return "Error: 'qty' must be > 0."
            if side not in ("buy", "sell"):
                return "Error: 'side' must be 'buy' or 'sell'."

            from src.autonomous_agent.alpaca_client import place_paper_order
            result = place_paper_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type="market",              # only market orders via agent (safety)
                account=account,
            )
            return json.dumps(result, indent=2)

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE WRITE TOOLS — strategies (Agent Mode only)
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_add_strategy":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            # Build a strategy dict from whatever the LLM supplied in args
            data: dict = {
                "name":        str(args.get("name", "Unnamed Strategy")),
                "status":      str(args.get("status", "draft")),
                "symbol":      str(args.get("symbol", "")),
                "timeframe":   str(args.get("timeframe", "")),
                "regime":      str(args.get("regime", "all")),
                "params":      args.get("params", {}),       # dict of hyperparameters
                "performance": args.get("performance", {}),  # dict of metrics
                "code_path":   str(args.get("code_path", "")),
                "notes":       str(args.get("notes", "")),
            }
            sid = db.add_strategy(data)
            return f"✅ Strategy added with ID: {sid}"

        if tool_name == "db_update_strategy":
            from src.autonomous_agent.database import AgentDatabase
            db      = AgentDatabase()
            sid     = str(args.get("strategy_id", ""))
            updates = args.get("updates_dict", {})           # dict of fields to merge
            if not sid:
                return "Error: 'strategy_id' is required."
            if not isinstance(updates, dict) or not updates:
                return "Error: 'updates_dict' must be a non-empty dict of fields to update."
            ok = db.update_strategy(sid, updates)
            return f"✅ Strategy '{sid}' updated." if ok else f"Strategy '{sid}' not found."

        if tool_name == "db_update_strategy_status":
            from src.autonomous_agent.database import AgentDatabase
            db         = AgentDatabase()
            sid        = str(args.get("strategy_id", ""))
            new_status = str(args.get("new_status", ""))
            if not sid or not new_status:
                return "Error: 'strategy_id' and 'new_status' are required."
            if new_status not in ("draft", "production", "graveyard"):
                return "Error: 'new_status' must be one of: draft, production, graveyard."
            ok = db.update_strategy_status(sid, new_status)
            return f"✅ Strategy '{sid}' status → {new_status}." if ok else f"Strategy '{sid}' not found."

        if tool_name == "db_delete_strategy":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            sid = str(args.get("strategy_id", ""))
            if not sid:
                return "Error: 'strategy_id' is required."
            ok = db.delete_strategy(sid)
            return (
                f"✅ Strategy '{sid}' permanently deleted."
                if ok
                else f"Strategy '{sid}' not found."
            )

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE WRITE TOOLS — positions (Agent Mode only)
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_upsert_position":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            # Validate required fields before writing
            if not args.get("symbol"):
                return "Error: 'symbol' is required in data_dict."
            pid = db.upsert_position(args)
            return f"✅ Position upserted with ID: {pid}"

        if tool_name == "db_close_position":
            from src.autonomous_agent.database import AgentDatabase
            db          = AgentDatabase()
            pid         = str(args.get("position_id", ""))
            close_price = float(args.get("close_price", 0))
            realized_pl = args.get("realized_pl")        # may be None
            if not pid:
                return "Error: 'position_id' is required."
            if close_price <= 0:
                return "Error: 'close_price' must be > 0."
            ok = db.close_position(
                pid,
                close_price,
                float(realized_pl) if realized_pl is not None else None,
            )
            return (
                f"✅ Position '{pid}' marked as closed at {close_price}."
                if ok
                else f"Position '{pid}' not found."
            )

        if tool_name == "db_update_sl_tp":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            pid = str(args.get("position_id", ""))
            sl  = args.get("sl")    # may be None → leave unchanged
            tp  = args.get("tp")
            if not pid:
                return "Error: 'position_id' is required."
            ok = db.update_sl_tp(
                pid,
                sl=float(sl) if sl is not None else None,
                tp=float(tp) if tp is not None else None,
            )
            return (
                f"✅ SL/TP updated on position '{pid}'."
                if ok
                else f"Position '{pid}' not found."
            )

        # ──────────────────────────────────────────────────────────────────────
        # DATABASE WRITE TOOLS — trades (Agent Mode only)
        # ──────────────────────────────────────────────────────────────────────

        if tool_name == "db_log_trade":
            from src.autonomous_agent.database import AgentDatabase
            db  = AgentDatabase()
            # Validate required fields
            if not args.get("symbol"):
                return "Error: 'symbol' is required in data_dict."
            if not args.get("side"):
                return "Error: 'side' (buy|sell) is required in data_dict."
            tid = db.log_trade(args)
            return f"✅ Trade logged with ID: {tid}"

        if tool_name == "db_update_trade":
            from src.autonomous_agent.database import AgentDatabase
            db      = AgentDatabase()
            tid     = str(args.get("trade_id", ""))
            updates = args.get("updates_dict", {})
            if not tid:
                return "Error: 'trade_id' is required."
            if not isinstance(updates, dict) or not updates:
                return "Error: 'updates_dict' must be a non-empty dict."
            ok = db.update_trade(tid, updates)
            return f"✅ Trade '{tid}' updated." if ok else f"Trade '{tid}' not found."

        # ── Fallback: unknown tool name ───────────────────────────────────────
        return f"Unknown tool: '{tool_name}'. Check the tool catalogue in the system prompt."

    except Exception as exc:
        # Return the error as text so the LLM can acknowledge it gracefully
        logger.error("[Tools] execute_tool('%s') raised: %s", tool_name, exc)
        return f"Tool execution error [{tool_name}]: {exc}"
