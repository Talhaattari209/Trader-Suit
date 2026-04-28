"""
src/autonomous_agent/context_builder.py
========================================
Builds the live system-state snapshot that is injected into every LLM prompt.

WHY a separate module?
  The context snapshot is expensive (touches filesystem, Alpaca API, CSV files).
  Isolating it here lets us:
    1. Cache it per-request (TTL logic, if needed later).
    2. Unit-test the context snapshot independently of the LLM.
    3. Expose it directly via GET /agent/context for dashboard debugging.

Design principles:
  • Every data-collection step is wrapped in try/except — a missing file or
    network error must NEVER crash the agent; we return partial context instead.
  • We intentionally keep the text representation compact: LLMs have context
    windows and billing is per-token.  Summaries, not dumps.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("autonomous_agent.context")


# ─────────────────────────────────────────────────────────────────────────────
# Raw context collector
# ─────────────────────────────────────────────────────────────────────────────

def build_context() -> dict[str, Any]:
    """
    Collect live system state from all data sources.

    Returns a plain dict that is both machine-readable (for the /agent/context
    endpoint) and easily convertible to the LLM text block (see to_text()).

    Sources queried:
      - AgentDatabase    : strategies, positions, trades (file-based JSON)
      - FilesystemStore  : alpha ideas, workflow state (main project DataStore)
      - Vault filesystem : file listings in all standard folders
      - Price-level detector : key US30 liquidity zones / session levels
      - Alpaca accounts  : equity, cash, open positions (both accounts)
    """
    ctx: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),   # ISO-8601 for unambiguous timestamping
        # AgentDatabase summaries (always present — zero-cost if DB is empty)
        "db_summary":      {"strategies": {}, "positions": {}, "trades": {}},
        # Main project DataStore
        "strategies":      [],    # from FilesystemStore (legacy / main project)
        "alphas":          [],
        "workflow_state":  {},
        "vault_summary":   {},
        "price_levels":    {},
        # Alpaca live data
        "alpaca_account1": {},
        "alpaca_account2": {},
        "open_positions1": [],
        "open_positions2": [],
    }

    # ── AgentDatabase summary (strategies, positions, trades) ─────────────────
    # This is the primary data layer for the autonomous agent package.
    # We call full_summary() which reads all three JSON files and returns
    # counts + key aggregates — fast, no network required.
    try:
        from src.autonomous_agent.database import AgentDatabase
        db = AgentDatabase()
        ctx["db_summary"] = db.full_summary()
    except Exception as exc:
        logger.debug("[ContextBuilder] AgentDatabase error: %s", exc)

    # ── Main project persistence layer (alphas + workflow) ────────────────────
    # We also pull from the main project's FilesystemStore so the agent can
    # answer questions about the research pipeline and alpha ideas, which are
    # managed there (not in AgentDatabase).
    try:
        from src.persistence.filesystem_store import FilesystemStore
        store = FilesystemStore()                         # read-only operations here
        ctx["strategies"]     = store.load_strategies() or []   # main project strategies
        ctx["alphas"]         = store.load_alphas()      or []
        ctx["workflow_state"] = store.get_workflow_state() or {}
    except Exception as exc:
        logger.debug("[ContextBuilder] FilesystemStore error: %s", exc)
        # Partial context is acceptable — the agent will note "data unavailable"

    # ── Vault file listing ────────────────────────────────────────────────────
    try:
        vault_root = Path(os.environ.get("VAULT_PATH", "AI_Employee_Vault"))
        summary: dict[str, list[str]] = {}
        # These are the canonical vault folders from AGENTS.md
        for folder in ["Needs_Action", "Plans", "Approved", "Reports", "Logs", "Graveyard"]:
            folder_path = vault_root / folder
            if folder_path.exists() and folder_path.is_dir():
                # Collect only filenames (not full paths) — shorter for LLM context
                summary[folder] = sorted(f.name for f in folder_path.iterdir() if f.is_file())
        ctx["vault_summary"] = summary
    except Exception as exc:
        logger.debug("[ContextBuilder] Vault scan error: %s", exc)

    # ── Price levels (US30 liquidity zones, FVG, session levels) ─────────────
    try:
        from src.tools.price_level_detector import detect_all_price_levels
        import pandas as pd
        csv_path = os.environ.get("US30_CSV_PATH", "")
        if csv_path and Path(csv_path).exists():
            # Limit to last 5 000 bars for speed — enough for daily/weekly structure
            df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
            df = df.iloc[-5000:] if len(df) > 5000 else df
            ctx["price_levels"] = detect_all_price_levels(df)
    except Exception as exc:
        logger.debug("[ContextBuilder] Price levels error: %s", exc)

    # ── Alpaca account snapshots (both paper accounts from .env) ──────────────
    try:
        from src.autonomous_agent.alpaca_client import get_account_info, get_open_positions
        ctx["alpaca_account1"] = get_account_info(account=1)    # ALPACA_API_KEY
        ctx["open_positions1"] = get_open_positions(account=1)
    except Exception as exc:
        logger.debug("[ContextBuilder] Alpaca account 1 error: %s", exc)

    try:
        from src.autonomous_agent.alpaca_client import get_account_info, get_open_positions
        ctx["alpaca_account2"] = get_account_info(account=2)    # ALPACA_API_KEY_2
        ctx["open_positions2"] = get_open_positions(account=2)
    except Exception as exc:
        logger.debug("[ContextBuilder] Alpaca account 2 error: %s", exc)

    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# Text renderer — converts the raw dict to a compact LLM-readable block
# ─────────────────────────────────────────────────────────────────────────────

def to_text(ctx: dict[str, Any]) -> str:
    """
    Render the context snapshot as a compact text block for LLM injection.

    Format rules:
      - Max ~1 200 tokens.  The system prompt + tool descriptions already use
        ~400 tokens; we leave the rest for the conversation history.
      - Use | separators for rows of numbers (traders read these fast).
      - Truncate lists with "…" rather than emitting everything.
    """
    lines: list[str] = [
        f"=== LIVE SYSTEM CONTEXT  [{ctx['timestamp']}] ===",
    ]

    # ── Agent Database summary (strategies / positions / trades) ───────────────
    db = ctx.get("db_summary", {})
    strat_s = db.get("strategies", {})
    pos_s   = db.get("positions",  {})
    trade_s = db.get("trades",     {})

    if strat_s or pos_s or trade_s:
        lines.append(
            f"AgentDB | Strategies: {strat_s.get('total',0)} total "
            f"(draft={strat_s.get('draft',0)} prod={strat_s.get('production',0)} "
            f"grave={strat_s.get('graveyard',0)}) "
            f"| Positions open={pos_s.get('open',0)} closed={pos_s.get('closed',0)} "
            f"unrealised_pl={pos_s.get('total_unrealized_pl',0):.2f} "
            f"| Trades total={trade_s.get('total',0)} "
            f"realised_pl={trade_s.get('total_realized_pl',0):.2f}"
        )

    # ── Workflow state ─────────────────────────────────────────────────────────
    wf = ctx.get("workflow_state", {})
    step = wf.get("step", "idle")
    alpha_id = wf.get("alpha_id") or wf.get("context", {}).get("alpha_id", "")
    cb_active = wf.get("circuit_breaker_active", False)

    lines.append(
        f"Workflow: step={step}"
        + (f" | alpha={alpha_id}" if alpha_id else "")
        + (" | ⛔ CIRCUIT_BREAKER_ACTIVE" if cb_active else "")
    )

    # ── Strategy summary ───────────────────────────────────────────────────────
    strategies = ctx.get("strategies", [])
    lines.append(f"Strategies total: {len(strategies)}")
    if strategies:
        # Show up to 6 strategies inline; more are retrievable via get_strategies tool
        rows = [
            f"  {s.get('strategy_id', '?')}({s.get('status', '?')})"
            for s in strategies[:6]
        ]
        lines.append("  " + " | ".join(rows) + ("  …" if len(strategies) > 6 else ""))

    # ── Alpha ideas ────────────────────────────────────────────────────────────
    alphas = ctx.get("alphas", [])
    lines.append(f"Alpha ideas in DataStore: {len(alphas)}")
    if alphas:
        for a in alphas[:3]:                    # first 3 for LLM context brevity
            hyp = a.get("hypothesis", "")[:70]  # cap at 70 chars to save tokens
            lines.append(f"  • {hyp}")

    # ── Vault file counts ──────────────────────────────────────────────────────
    vault = ctx.get("vault_summary", {})
    if vault:
        lines.append("Vault:")
        for folder, files in vault.items():
            preview = ", ".join(files[:3]) + ("…" if len(files) > 3 else "")
            lines.append(f"  {folder}/: {len(files)} files [{preview}]")

    # ── Price levels summary ───────────────────────────────────────────────────
    pl = ctx.get("price_levels", {})
    if pl:
        # Just list the key names; full values available via get_price_levels tool
        lines.append(f"Price level types detected: {list(pl.keys())}")

    # ── Alpaca account 1 (primary paper) ──────────────────────────────────────
    acc1 = ctx.get("alpaca_account1", {})
    if acc1 and "error" not in acc1:
        lines.append(
            f"Alpaca #1 (paper): equity={acc1.get('equity', 0):.2f} "
            f"| cash={acc1.get('cash', 0):.2f} "
            f"| unrealised_pl={acc1.get('unrealized_pl', 0):.2f}"
        )
    pos1 = ctx.get("open_positions1", [])
    if pos1 and "error" not in (pos1[0] if pos1 else {}):
        lines.append(f"  Open positions (acct 1): {len(pos1)}")
        for p in pos1[:4]:                      # show up to 4 positions inline
            lines.append(
                f"    {p['symbol']} {p['side']} {p['qty']} @ {p['avg_entry_price']} "
                f"| P&L {p['unrealized_pl']:.2f}"
            )

    # ── Alpaca account 2 (secondary paper) ────────────────────────────────────
    acc2 = ctx.get("alpaca_account2", {})
    if acc2 and "error" not in acc2:
        lines.append(
            f"Alpaca #2 (paper): equity={acc2.get('equity', 0):.2f} "
            f"| cash={acc2.get('cash', 0):.2f} "
            f"| unrealised_pl={acc2.get('unrealized_pl', 0):.2f}"
        )

    lines.append("=== END CONTEXT ===")
    return "\n".join(lines)
