"""
connectors_tester/src/agents/autonomous_connectors_agent.py
=============================================================
Autonomous Agent for the Connectors Tester.

BROKER AWARENESS:
  The agent knows which broker is currently selected (alpaca_1, alpaca_2, mt5)
  and only exposes tools relevant to that broker.  The broker is passed as a
  parameter from the Streamlit session state.

TWO MODES (same pattern as main project):
  Chat Mode  — read-only: get account, positions, orders, history, price levels.
  Agent Mode — can also execute orders, modify SL/TP, close positions.
               Always asks for explicit confirmation before executing.

DEBUG OUTPUT (every LLM call and broker API call):
  === CONNECTORS_TESTER AGENT PROMPT ===
  === CONNECTORS_TESTER AGENT RESPONSE ===
  (Broker calls print their own === ALPACA/MT5 REQUEST/RESPONSE === blocks
   in alpaca_tester.py / mt5_tester.py)

TOOL PROTOCOL:
  Same text-based TOOL_CALL: {…} protocol as the main autonomous agent.
  Model-agnostic: works with Gemini (default) or any backend.

DATA LAYER (AgentDatabase):
  The agent also has access to the local file-based database (strategies,
  positions, trades) from the autonomous_agent package, so it can answer
  questions like "what strategies do we have in production?" even in the
  tester context.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("connectors_tester.agent")

# ── Path bootstrap ────────────────────────────────────────────────────────────
# The tester is a standalone project.  We add the parent directory (the main
# project root) to sys.path so we can reuse llm_client.py and the database.
# This avoids copying those files; they are imported directly.
_THIS_DIR    = Path(__file__).resolve().parent          # connectors_tester/src/agents/
_TESTER_ROOT = _THIS_DIR.parent.parent                  # connectors_tester/
_MAIN_ROOT   = _TESTER_ROOT.parent                      # project root (claude/)
if str(_MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_MAIN_ROOT))                 # gives access to src.tools.llm_client

MAX_TOOL_ITERATIONS: int = 5   # safety cap on tool-call loop
HISTORY_WINDOW:      int = 10  # last N turns injected into the prompt


# ─────────────────────────────────────────────────────────────────────────────
# System-context builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_context(broker: str) -> str:
    """
    Collect live data from the selected broker and the local database,
    then render a compact text block for the LLM system prompt.
    """
    lines = [f"=== CONNECTORS TESTER CONTEXT [{broker.upper()}] ==="]

    # ── Alpaca account snapshot ────────────────────────────────────────────────
    if broker in ("alpaca_1", "alpaca_2"):
        try:
            from src.connectors.alpaca_tester import get_account, get_positions
            acc_num = 1 if broker == "alpaca_1" else 2
            acc     = get_account(account=acc_num)
            pos     = get_positions(account=acc_num)
            if "error" not in acc:
                lines.append(
                    f"Alpaca {broker}: equity={acc.get('equity', 0):.2f} "
                    f"cash={acc.get('cash', 0):.2f} "
                    f"buying_power={acc.get('buying_power', 0):.2f} "
                    f"unrealised_pl={acc.get('unrealized_pl', 0):.2f}"
                )
            lines.append(f"Open positions: {len(pos)}")
            for p in pos[:3]:                           # first 3 positions inline
                lines.append(
                    f"  {p['symbol']} {p['side']} {p['qty']} "
                    f"@ {p['avg_entry_price']} | P&L {p['unrealized_pl']:.2f}"
                )
        except Exception as exc:
            lines.append(f"Alpaca context error: {exc}")

    # ── MT5 account snapshot ───────────────────────────────────────────────────
    elif broker == "mt5":
        try:
            from src.connectors.mt5_tester import get_account, get_positions
            acc = get_account()
            pos = get_positions()
            if "error" not in acc:
                lines.append(
                    f"MT5: balance={acc.get('balance', 0):.2f} "
                    f"equity={acc.get('equity', 0):.2f} "
                    f"profit={acc.get('profit', 0):.2f} "
                    f"margin_level={acc.get('margin_level', 0):.1f}%"
                )
            lines.append(f"Open positions: {len([p for p in pos if 'error' not in p])}")
        except Exception as exc:
            lines.append(f"MT5 context error: {exc}")

    # ── Local database summary ─────────────────────────────────────────────────
    try:
        # AgentDatabase path resolves from CWD (connectors_tester/ when running)
        import os
        os.chdir(str(_TESTER_ROOT))    # ensure CWD = connectors_tester/ for DB path resolution
        sys.path.insert(0, str(_MAIN_ROOT))
        from src.autonomous_agent.database import AgentDatabase
        db  = AgentDatabase()
        s   = db.full_summary()
        ss  = s.get("strategies", {})
        ps  = s.get("positions",  {})
        ts  = s.get("trades",     {})
        lines.append(
            f"LocalDB: strategies={ss.get('total',0)} "
            f"(prod={ss.get('production',0)}) "
            f"| open_positions={ps.get('open',0)} "
            f"| trades={ts.get('total',0)} "
            f"realised_pl={ts.get('total_realized_pl',0):.2f}"
        )
    except Exception as exc:
        lines.append(f"LocalDB context error: {exc}")

    lines.append("=== END CONTEXT ===")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Tool catalogues
# ─────────────────────────────────────────────────────────────────────────────

def _chat_tools(broker: str) -> str:
    """Build the read-only tool prompt section for the current broker."""
    from src.tools.order_types_handler import order_types_for_agent_prompt

    broker_section = ""
    if broker in ("alpaca_1", "alpaca_2"):
        acc = broker[-1]   # "1" or "2"
        broker_section = f"""\
── ALPACA (account {acc}) ──────────────────────────────────────────────────────
  get_account()                               — equity, cash, buying_power
  get_positions()                             — all open positions
  get_orders(status)                          — status: open|closed|all
  get_portfolio_history(days)                 — daily P&L history (default 30)
  get_trade_history(limit)                    — filled orders (default 50)
  get_latest_quote(symbol)                    — live bid/ask/mid
  get_bars(symbol, timeframe, limit)          — OHLCV bars (timeframe: 1min|1hour|1day)"""
    elif broker == "mt5":
        broker_section = """\
── MT5 ──────────────────────────────────────────────────────────────────────────
  mt5_get_account()                           — balance, equity, margin, profit
  mt5_get_positions(symbol)                   — open positions (optional symbol filter)
  mt5_get_orders(symbol)                      — pending orders
  mt5_get_history(from_date, to_date, limit)  — closed deals history
  mt5_get_bars(symbol, timeframe, count)      — OHLCV bars (timeframe: 1m|1h|1d|etc.)
  mt5_get_latest_tick(symbol)                 — live bid/ask/last"""

    order_types = order_types_for_agent_prompt(broker)

    return f"""\
=== AVAILABLE TOOLS (Chat Mode — read-only) ===
Call a tool by writing EXACTLY on one line:
  TOOL_CALL: {{"tool": "<name>", "args": {{<key>: <value>}}}}

{broker_section}

── DATABASE (local file store) ──────────────────────────────────────────────────
  db_list_strategies(status, symbol)          — list strategies (draft|production|graveyard)
  db_list_positions(status)                   — local position snapshots (open|closed|all)
  db_list_trades(symbol, broker, limit)       — trade log
  db_pnl_summary(symbol, broker)              — aggregated realized P&L stats

── ORDER TYPES REFERENCE ────────────────────────────────────────────────────────
{order_types}
"""


def _agent_tools(broker: str) -> str:
    """Build the action tool section (Agent Mode only)."""
    if broker in ("alpaca_1", "alpaca_2"):
        action_section = """\
── ALPACA ACTIONS ──────────────────────────────────────────────────────────────
  place_order(symbol, side, qty, order_type, limit_price, stop_price,
              trail_price, trail_percent, time_in_force, take_profit, stop_loss)
  cancel_order(order_id)
  close_position(symbol, qty)                 — qty=None closes entire position
  modify_stop_loss(order_id, new_stop)"""
    elif broker == "mt5":
        action_section = """\
── MT5 ACTIONS ─────────────────────────────────────────────────────────────────
  mt5_place_order(symbol, order_type, volume, price, sl, tp,
                  price_stoplimit, comment, magic)
  mt5_cancel_order(ticket)
  mt5_close_position(ticket, volume)          — volume=None closes entirely
  mt5_modify_sl_tp(ticket, sl, tp)"""
    else:
        action_section = "No action tools available for this broker."

    return f"""\
=== ADDITIONAL TOOLS (Agent Mode — executes real actions) ===
⚠  ALWAYS describe the action and ask for confirmation before calling.

{action_section}

── DATABASE WRITE ────────────────────────────────────────────────────────────────
  db_log_trade(data_dict)                     — record a trade manually
  db_upsert_position(data_dict)               — sync a position snapshot
  db_update_strategy_status(strategy_id, new_status)
"""


# ─────────────────────────────────────────────────────────────────────────────
# Tool executor
# ─────────────────────────────────────────────────────────────────────────────

_ACTION_TOOLS: frozenset[str] = frozenset({
    "place_order", "cancel_order", "close_position", "modify_stop_loss",
    "mt5_place_order", "mt5_cancel_order", "mt5_close_position", "mt5_modify_sl_tp",
    "db_log_trade", "db_upsert_position", "db_update_strategy_status",
})


def _execute_tool(tool_name: str, args: dict, mode: str, broker: str) -> str:
    """
    Dispatch a TOOL_CALL to the appropriate connector or database.

    Returns a string (plain text or JSON) so the LLM can incorporate it
    into the next response without further processing.
    """
    acc_num = 2 if broker == "alpaca_2" else 1   # integer account number for Alpaca helpers

    if mode == "chat" and tool_name in _ACTION_TOOLS:
        return f"⛔ '{tool_name}' is an action tool.  Switch to Agent Mode to execute it."

    try:
        # ── Alpaca read tools ─────────────────────────────────────────────────
        if tool_name == "get_account":
            from src.connectors.alpaca_tester import get_account
            return json.dumps(get_account(account=acc_num), indent=2, default=str)

        if tool_name == "get_positions":
            from src.connectors.alpaca_tester import get_positions
            return json.dumps(get_positions(account=acc_num), indent=2, default=str)

        if tool_name == "get_orders":
            from src.connectors.alpaca_tester import get_orders
            status = str(args.get("status", "all"))
            limit  = int(args.get("limit", 50))
            return json.dumps(get_orders(account=acc_num, status=status, limit=limit), indent=2, default=str)

        if tool_name == "get_portfolio_history":
            from src.connectors.alpaca_tester import get_portfolio_history
            days = int(args.get("days", 30))
            return json.dumps(get_portfolio_history(account=acc_num, days=days), indent=2, default=str)

        if tool_name == "get_trade_history":
            from src.connectors.alpaca_tester import get_trade_history
            limit = int(args.get("limit", 50))
            return json.dumps(get_trade_history(account=acc_num, limit=limit), indent=2, default=str)

        if tool_name == "get_latest_quote":
            from src.connectors.alpaca_tester import get_latest_quote
            symbol = str(args.get("symbol", "SPY"))
            return json.dumps(get_latest_quote(symbol=symbol, account=acc_num), indent=2, default=str)

        if tool_name == "get_bars":
            from src.connectors.alpaca_tester import get_bars
            return json.dumps(
                get_bars(
                    symbol=str(args.get("symbol", "SPY")),
                    timeframe=str(args.get("timeframe", "1day")),
                    limit=int(args.get("limit", 50)),
                    account=acc_num,
                ),
                indent=2, default=str,
            )

        # ── MT5 read tools ────────────────────────────────────────────────────
        if tool_name == "mt5_get_account":
            from src.connectors.mt5_tester import get_account as mt5_acc
            return json.dumps(mt5_acc(), indent=2, default=str)

        if tool_name == "mt5_get_positions":
            from src.connectors.mt5_tester import get_positions as mt5_pos
            sym = args.get("symbol") or None
            return json.dumps(mt5_pos(symbol=sym), indent=2, default=str)

        if tool_name == "mt5_get_orders":
            from src.connectors.mt5_tester import get_orders as mt5_ord
            sym = args.get("symbol") or None
            return json.dumps(mt5_ord(symbol=sym), indent=2, default=str)

        if tool_name == "mt5_get_history":
            from src.connectors.mt5_tester import get_history as mt5_hist
            return json.dumps(
                mt5_hist(
                    from_date=args.get("from_date"),
                    to_date=args.get("to_date"),
                    limit=int(args.get("limit", 100)),
                ),
                indent=2, default=str,
            )

        if tool_name == "mt5_get_bars":
            from src.connectors.mt5_tester import get_bars as mt5_bars
            return json.dumps(
                mt5_bars(
                    symbol=str(args.get("symbol", "US30")),
                    timeframe=str(args.get("timeframe", "1h")),
                    count=int(args.get("count", 50)),
                ),
                indent=2, default=str,
            )

        if tool_name == "mt5_get_latest_tick":
            from src.connectors.mt5_tester import get_latest_tick
            return json.dumps(get_latest_tick(str(args.get("symbol", "US30"))), indent=2, default=str)

        # ── Database read tools ───────────────────────────────────────────────
        if tool_name == "db_list_strategies":
            from src.autonomous_agent.database import AgentDatabase
            db = AgentDatabase()
            rows = db.list_strategies(status=args.get("status"), symbol=args.get("symbol"))
            return json.dumps(rows, indent=2, default=str) if rows else "No strategies found."

        if tool_name == "db_list_positions":
            from src.autonomous_agent.database import AgentDatabase
            db = AgentDatabase()
            rows = db.list_positions(status=str(args.get("status", "open")))
            return json.dumps(rows, indent=2, default=str) if rows else "No positions found."

        if tool_name == "db_list_trades":
            from src.autonomous_agent.database import AgentDatabase
            db = AgentDatabase()
            rows = db.list_trades(
                symbol=args.get("symbol"),
                broker=args.get("broker"),
                limit=int(args.get("limit", 50)),
            )
            return json.dumps(rows, indent=2, default=str) if rows else "No trades found."

        if tool_name == "db_pnl_summary":
            from src.autonomous_agent.database import AgentDatabase
            db = AgentDatabase()
            return json.dumps(db.pnl_summary(symbol=args.get("symbol"), broker=args.get("broker")), indent=2)

        # ── Alpaca action tools ───────────────────────────────────────────────
        if tool_name == "place_order":
            from src.connectors.alpaca_tester import place_order
            from src.tools.order_types_handler import validate_order
            validate_order(broker, str(args.get("order_type", "market")), args)
            return json.dumps(
                place_order(
                    symbol=str(args["symbol"]),
                    side=str(args["side"]),
                    qty=float(args["qty"]),
                    order_type=str(args.get("order_type", "market")),
                    limit_price=args.get("limit_price"),
                    stop_price=args.get("stop_price"),
                    trail_price=args.get("trail_price"),
                    trail_percent=args.get("trail_percent"),
                    time_in_force=str(args.get("time_in_force", "day")),
                    take_profit=args.get("take_profit"),
                    stop_loss=args.get("stop_loss"),
                    account=acc_num,
                ),
                indent=2, default=str,
            )

        if tool_name == "cancel_order":
            from src.connectors.alpaca_tester import cancel_order
            return json.dumps(cancel_order(str(args["order_id"]), account=acc_num), indent=2, default=str)

        if tool_name == "close_position":
            from src.connectors.alpaca_tester import close_position
            return json.dumps(
                close_position(str(args["symbol"]), qty=args.get("qty"), account=acc_num),
                indent=2, default=str,
            )

        if tool_name == "modify_stop_loss":
            from src.connectors.alpaca_tester import modify_stop_loss
            return json.dumps(
                modify_stop_loss(str(args["order_id"]), float(args["new_stop"]), account=acc_num),
                indent=2, default=str,
            )

        # ── MT5 action tools ──────────────────────────────────────────────────
        if tool_name == "mt5_place_order":
            from src.connectors.mt5_tester import place_order as mt5_order
            from src.tools.order_types_handler import validate_order
            validate_order("mt5", str(args.get("order_type", "buy")), args)
            return json.dumps(
                mt5_order(
                    symbol=str(args["symbol"]),
                    order_type=str(args.get("order_type", "buy")),
                    volume=float(args["volume"]),
                    price=args.get("price"),
                    sl=args.get("sl"),
                    tp=args.get("tp"),
                    price_stoplimit=args.get("price_stoplimit"),
                    comment=str(args.get("comment", "ConnectorsTester")),
                    magic=int(args.get("magic", 12345)),
                ),
                indent=2, default=str,
            )

        if tool_name == "mt5_cancel_order":
            from src.connectors.mt5_tester import cancel_order as mt5_cancel
            return json.dumps(mt5_cancel(int(args["ticket"])), indent=2, default=str)

        if tool_name == "mt5_close_position":
            from src.connectors.mt5_tester import close_position as mt5_close
            return json.dumps(
                mt5_close(int(args["ticket"]), volume=args.get("volume")),
                indent=2, default=str,
            )

        if tool_name == "mt5_modify_sl_tp":
            from src.connectors.mt5_tester import modify_sl_tp
            return json.dumps(
                modify_sl_tp(int(args["ticket"]), sl=args.get("sl"), tp=args.get("tp")),
                indent=2, default=str,
            )

        # ── Database write tools ──────────────────────────────────────────────
        if tool_name == "db_log_trade":
            from src.autonomous_agent.database import AgentDatabase
            return f"Trade logged: {AgentDatabase().log_trade(args)}"

        if tool_name == "db_upsert_position":
            from src.autonomous_agent.database import AgentDatabase
            return f"Position upserted: {AgentDatabase().upsert_position(args)}"

        if tool_name == "db_update_strategy_status":
            from src.autonomous_agent.database import AgentDatabase
            ok = AgentDatabase().update_strategy_status(str(args["strategy_id"]), str(args["new_status"]))
            return "✅ Updated." if ok else "Strategy not found."

        return f"Unknown tool: '{tool_name}'."

    except Exception as exc:
        logger.error("[Agent tool '%s'] %s", tool_name, exc)
        return f"Tool error [{tool_name}]: {exc}"


def _parse_tool_call(text: str) -> dict | None:
    """Extract first TOOL_CALL JSON from LLM text (brace-counting parser)."""
    marker = "TOOL_CALL:"
    if marker not in text:
        return None
    try:
        start   = text.index(marker) + len(marker)
        snippet = text[start:].lstrip()
        depth, end = 0, 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        payload = json.loads(snippet[:end])
        return payload if "tool" in payload else None
    except (ValueError, json.JSONDecodeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main async entry point
# ─────────────────────────────────────────────────────────────────────────────

async def process_message(
    message:  str,
    history:  list[dict[str, Any]],
    mode:     str  = "chat",
    broker:   str  = "alpaca_1",
) -> str:
    """
    Process a user message and return the agent's response.

    Args:
        message : new user input
        history : list of {"role": "user"|"assistant", "content": "..."}
        mode    : "chat" (read-only) or "agent" (can trade)
        broker  : "alpaca_1" | "alpaca_2" | "mt5"

    Returns:
        Agent response as a plain string (may contain markdown).
    """
    # Import llm_client from main project (added to sys.path at module load)
    from src.tools.llm_client import get_default_llm_client
    llm = get_default_llm_client()   # GeminiLLMClient by default

    # ── Build system prompt ────────────────────────────────────────────────────
    context_text = _build_context(broker)
    mode_decl = (
        "You are in AGENT MODE — you may read data AND execute real broker actions.\n"
        "⚠  Always describe the action and ask for user confirmation before executing."
        if mode == "agent"
        else
        "You are in CHAT MODE — read-only.  Use tools to fetch data; never execute trades."
    )
    tools_block = _chat_tools(broker) + ("\n" + _agent_tools(broker) if mode == "agent" else "")

    system_prompt = f"""\
You are the Trader-Suit Connectors Tester AI Agent.
You have full access to {broker.upper()} broker operations and the local trade database.

{mode_decl}

{context_text}

{tools_block}

BEHAVIOURAL GUIDELINES:
• Be concise. Traders need fast, actionable information.
• Format numbers clearly: equity=42 350.00 | P&L=+235.50 | positions=3.
• After a TOOL_RESULT, synthesise it into a human-readable answer.
• Never fabricate data — if unavailable, say so.
• In Agent Mode: state exactly what you are about to do BEFORE writing TOOL_CALL.
• If a tool returns an error, explain it and suggest the corrective action.
"""

    # ── Build conversation prompt ──────────────────────────────────────────────
    history_text = ""
    for turn in history[-HISTORY_WINDOW:]:
        role    = turn.get("role", "user").upper()
        content = turn.get("content", "").strip()
        history_text += f"\n{role}: {content}"

    prompt = f"{history_text}\nUSER: {message}\n\nASSISTANT:"

    # ── Debug print ────────────────────────────────────────────────────────────
    print("=" * 60)
    print("=== CONNECTORS_TESTER AGENT PROMPT ===")
    print(f"Broker: {broker}  Mode: {mode}  History: {len(history)} turns")
    print(f"System (first 400): {system_prompt[:400]}")
    print(f"User: {message}")

    # ── First LLM call ─────────────────────────────────────────────────────────
    t0       = time.time()
    response = await llm.complete(prompt, system=system_prompt)
    elapsed  = time.time() - t0

    print("=== CONNECTORS_TESTER AGENT RESPONSE ===")
    print(f"Response (first 500): {response[:500]}")
    print(f"Elapsed: {elapsed:.2f}s")

    # ── Tool-call loop ─────────────────────────────────────────────────────────
    for iteration in range(MAX_TOOL_ITERATIONS):
        tc = _parse_tool_call(response)
        if tc is None:
            break

        tool_name = tc.get("tool", "")
        tool_args = tc.get("args", {})
        print(f"[CTAgent] tool #{iteration+1}: {tool_name}({json.dumps(tool_args)[:120]})")

        tool_result = _execute_tool(tool_name, tool_args, mode, broker)
        print(f"[CTAgent] result (first 200): {tool_result[:200]}")

        tc_start = response.index("TOOL_CALL:")
        follow_up = (
            f"{prompt}\n{response[:tc_start].rstrip()}\n"
            f"TOOL_CALL: {json.dumps({'tool': tool_name, 'args': tool_args})}\n"
            f"TOOL_RESULT: {tool_result}\n\nASSISTANT:"
        )

        t1       = time.time()
        response = await llm.complete(follow_up, system=system_prompt)
        print(f"=== CONNECTORS_TESTER AGENT TOOL RESPONSE (iter {iteration+1}) ===")
        print(f"Response: {response[:500]}  Elapsed: {time.time()-t1:.2f}s")

    return response.strip()
