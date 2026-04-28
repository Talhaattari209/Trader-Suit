"""
src/autonomous_agent/database.py
==================================
File-based database for the Autonomous Agent.

THREE COLLECTIONS (each stored as a JSON array in its own file):

  strategies.json  — strategy registry (draft / production / graveyard)
  positions.json   — position snapshots (open & closed, from Alpaca or MT5)
  trades.json      — executed trade log (every fill ever recorded)

DESIGN CHOICES:

  Why JSON files instead of SQLite?
    • The rest of the project uses JSON files exclusively (FilesystemStore).
      Consistency lowers the "where is the data?" cognitive overhead.
    • JSON files are human-readable → a technical client can open them in any
      editor and verify the data without a DB browser.
    • SQLite would be faster at scale but for a trading system with <10 000
      records over its lifetime, file I/O is entirely adequate.
    • Zero extra dependency — `json` is in the Python standard library.

  Why NOT reuse FilesystemStore?
    • FilesystemStore is tightly coupled to the main project's DataStore/ path
      and config layer.  This package must be self-contained and deployable
      without the main project present.
    • We want full control over schema evolution here.

  Thread-safety:
    • Single-process Streamlit usage is assumed (one Python process, one thread
      per user request).  All reads are full-file loads; all writes are
      full-file atomic overrides (write-to-temp then rename would be the next
      step if concurrent writes become a concern).

  Storage path:
    • Default: DataStore/autonomous_agent/  (relative to CWD).
    • Override via env var AGENT_DATASTORE_PATH.
    • The path is created automatically on first write.

RECORD SCHEMAS (fields the agent and UI can rely on):

  Strategy:
    strategy_id   : str   (auto-generated if not supplied)
    name          : str
    status        : "draft" | "production" | "graveyard"
    regime        : "trending" | "ranging" | "all"   (market condition filter)
    symbol        : str   (e.g. "US30", "EURUSD")
    timeframe     : str   (e.g. "H1", "M15")
    params        : dict  (strategy hyperparameters)
    performance   : dict  (sharpe, max_dd, hit_rate, sortino, e_ratio)
    code_path     : str   (relative path to strategy Python file)
    notes         : str
    created_at    : ISO-8601 str
    updated_at    : ISO-8601 str

  Position:
    position_id   : str   (auto-generated)
    symbol        : str
    side          : "long" | "short"
    qty           : float
    entry_price   : float
    current_price : float
    unrealized_pl : float
    unrealized_plpc: float  (percentage)
    sl            : float | None   (stop-loss price)
    tp            : float | None   (take-profit price)
    broker        : "alpaca_1" | "alpaca_2" | "mt5"
    broker_pos_id : str   (broker's own position identifier)
    strategy_id   : str | None
    status        : "open" | "closed"
    opened_at     : ISO-8601 str
    closed_at     : ISO-8601 str | None
    last_updated  : ISO-8601 str

  Trade:
    trade_id        : str   (auto-generated)
    symbol          : str
    side            : "buy" | "sell"
    qty             : float
    order_type      : "market" | "limit" | "stop" | "stop_limit" | "trailing_stop"
    fill_price      : float
    commission      : float
    realized_pl     : float | None   (None for open legs; set when position closes)
    broker          : "alpaca_1" | "alpaca_2" | "mt5"
    broker_order_id : str   (broker's order / deal ID)
    strategy_id     : str | None
    sl              : float | None
    tp              : float | None
    status          : "filled" | "cancelled" | "rejected" | "partial"
    executed_at     : ISO-8601 str
    notes           : str
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utcnow() -> str:
    """Return current UTC time as ISO-8601 string.  Used for all timestamps."""
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    """
    Generate a short, human-readable unique ID.

    Format: <prefix>_<YYYYMMDD_HHMMSS>_<4-char hex>
    Example: trade_20260402_143022_a3f9

    WHY NOT uuid4()?
      A date-prefix makes IDs chronologically sortable by eye — useful when
      a technical client reads the raw JSON files directly.
    """
    ts  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:4]                  # 4 hex chars = 65 536 combinations per second
    return f"{prefix}_{ts}_{uid}"


def _load(path: Path, default: list | dict) -> list | dict:
    """
    Load JSON from *path*.  Returns *default* if file is absent or empty.

    We always validate that the returned type matches *default*'s type so a
    corrupted file (e.g. a stray "{}" in a list file) doesn't propagate silently.
    """
    if not path.exists():
        return default
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return default
        data = json.loads(text)
        # Type safety: if the file somehow contains the wrong root type, fall back
        if type(data) is not type(default):
            return default
        return data
    except (json.JSONDecodeError, OSError):
        return default     # corrupted file → start fresh; do NOT crash the agent


def _save(path: Path, data: Any) -> None:
    """
    Persist *data* to *path* as pretty-printed JSON.

    indent=2 keeps the files human-readable.
    default=str handles datetime objects that slipped through as raw values.
    """
    path.parent.mkdir(parents=True, exist_ok=True)   # create DataStore/ if first run
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
# AgentDatabase
# ─────────────────────────────────────────────────────────────────────────────

class AgentDatabase:
    """
    File-based database with three JSON collections.

    Usage (from tools.py or anywhere in the package):
        db = AgentDatabase()
        db.add_trade({...})
        trades = db.list_trades(symbol="US30", limit=20)
    """

    def __init__(self, datastore_path: str | None = None) -> None:
        """
        Initialise the database.

        Resolves the storage path in this priority order:
          1. *datastore_path* argument (explicit, for tests)
          2. AGENT_DATASTORE_PATH environment variable
          3. DataStore/autonomous_agent/ relative to CWD
        """
        root_str = (
            datastore_path
            or os.environ.get("AGENT_DATASTORE_PATH", "")
            or "DataStore/autonomous_agent"
        )
        self.root = Path(root_str)
        self.root.mkdir(parents=True, exist_ok=True)   # idempotent

        # One file per collection — simple and auditable
        self._strategies_path = self.root / "strategies.json"
        self._positions_path  = self.root / "positions.json"
        self._trades_path     = self.root / "trades.json"

    # ═════════════════════════════════════════════════════════════════════════
    # STRATEGIES
    # ═════════════════════════════════════════════════════════════════════════

    def _load_strategies(self) -> list[dict]:
        return _load(self._strategies_path, [])          # type: ignore[return-value]

    def list_strategies(
        self,
        status: str | None = None,
        symbol: str | None = None,
        regime: str | None = None,
    ) -> list[dict]:
        """
        Return strategies filtered by optional criteria.

        Args:
            status : "draft" | "production" | "graveyard" | None (all)
            symbol : e.g. "US30"  — None means all symbols
            regime : "trending" | "ranging" | "all" | None (all)

        Sorted newest-first so the agent shows the most recent work first.
        """
        rows = self._load_strategies()
        if status:
            rows = [r for r in rows if r.get("status") == status]
        if symbol:
            rows = [r for r in rows if r.get("symbol", "").upper() == symbol.upper()]
        if regime:
            rows = [r for r in rows if r.get("regime") in (regime, "all")]
        # Sort descending by created_at (ISO strings sort lexicographically = chronologically)
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return rows

    def get_strategy(self, strategy_id: str) -> dict | None:
        """Return a single strategy record by ID, or None if not found."""
        for row in self._load_strategies():
            if row.get("strategy_id") == strategy_id:
                return row
        return None

    def add_strategy(self, data: dict) -> str:
        """
        Add a new strategy record.  Returns the strategy_id.

        If *data* already contains a strategy_id it is used as-is (idempotent
        upsert: existing record is overwritten).  Otherwise a new ID is minted.
        """
        rows = self._load_strategies()
        sid  = data.get("strategy_id") or _new_id("strat")

        # Build the canonical record — fill missing fields with safe defaults
        record: dict = {
            "strategy_id":  sid,
            "name":         data.get("name", "Unnamed Strategy"),
            "status":       data.get("status", "draft"),
            "regime":       data.get("regime", "all"),
            "symbol":       data.get("symbol", ""),
            "timeframe":    data.get("timeframe", ""),
            "params":       data.get("params", {}),
            "performance":  data.get("performance", {}),
            "code_path":    data.get("code_path", ""),
            "notes":        data.get("notes", ""),
            "created_at":   data.get("created_at", _utcnow()),
            "updated_at":   _utcnow(),
        }

        # Upsert: replace if exists, append if new
        for i, row in enumerate(rows):
            if row.get("strategy_id") == sid:
                rows[i] = record
                _save(self._strategies_path, rows)
                return sid

        rows.append(record)
        _save(self._strategies_path, rows)
        return sid

    def update_strategy(self, strategy_id: str, updates: dict) -> bool:
        """
        Merge *updates* into an existing strategy record.

        Returns True if the strategy was found and updated, False otherwise.
        The updated_at timestamp is always refreshed automatically.
        """
        rows = self._load_strategies()
        for i, row in enumerate(rows):
            if row.get("strategy_id") == strategy_id:
                rows[i] = {**row, **updates, "strategy_id": strategy_id, "updated_at": _utcnow()}
                _save(self._strategies_path, rows)
                return True
        return False                            # strategy_id not found

    def update_strategy_status(self, strategy_id: str, new_status: str) -> bool:
        """
        Shortcut for the most common update: changing a strategy's lifecycle status.

        Valid transitions: draft → production, draft → graveyard, production → graveyard.
        No guard here — the LLM prompt enforces this; we just write the file.
        """
        return self.update_strategy(strategy_id, {"status": new_status})

    def delete_strategy(self, strategy_id: str) -> bool:
        """
        Permanently remove a strategy record.

        In production use, prefer update_strategy_status(..., "graveyard") to
        preserve audit history.  Hard delete is available for test clean-up.
        """
        rows = self._load_strategies()
        before = len(rows)
        rows   = [r for r in rows if r.get("strategy_id") != strategy_id]
        if len(rows) == before:
            return False                        # not found
        _save(self._strategies_path, rows)
        return True

    def strategy_summary(self) -> dict:
        """
        Return counts per status — used in the context snapshot.

        Example: {"total": 12, "draft": 5, "production": 4, "graveyard": 3}
        """
        rows = self._load_strategies()
        summary: dict[str, int] = {"total": len(rows), "draft": 0, "production": 0, "graveyard": 0}
        for r in rows:
            s = r.get("status", "draft")
            if s in summary:
                summary[s] += 1
        return summary

    # ═════════════════════════════════════════════════════════════════════════
    # POSITIONS
    # ═════════════════════════════════════════════════════════════════════════

    def _load_positions(self) -> list[dict]:
        return _load(self._positions_path, [])           # type: ignore[return-value]

    def list_positions(
        self,
        status: str = "open",        # "open" | "closed" | "all"
        broker: str | None = None,
        symbol: str | None = None,
    ) -> list[dict]:
        """
        Return positions filtered by status, broker, and/or symbol.

        Default status="open" because that's what 90% of agent queries ask for.
        """
        rows = self._load_positions()
        if status != "all":
            rows = [r for r in rows if r.get("status") == status]
        if broker:
            rows = [r for r in rows if r.get("broker") == broker]
        if symbol:
            rows = [r for r in rows if r.get("symbol", "").upper() == symbol.upper()]
        rows.sort(key=lambda r: r.get("opened_at", ""), reverse=True)
        return rows

    def get_position(self, position_id: str) -> dict | None:
        """Return a single position by ID, or None."""
        for row in self._load_positions():
            if row.get("position_id") == position_id:
                return row
        return None

    def upsert_position(self, data: dict) -> str:
        """
        Create or update a position snapshot.

        WHY upsert (not separate add/update)?
          Alpaca's get_all_positions() returns the full current state every
          time.  We sync the local snapshot by matching on broker_pos_id.
          If found, we overwrite (update price, P&L, SL, TP).  If not found,
          we create a new record.

        Returns the position_id.
        """
        rows   = self._load_positions()
        pid    = data.get("position_id") or _new_id("pos")
        bpid   = data.get("broker_pos_id", "")            # broker's own ID for matching

        record: dict = {
            "position_id":    pid,
            "symbol":         data.get("symbol", ""),
            "side":           data.get("side", "long"),
            "qty":            float(data.get("qty", 0)),
            "entry_price":    float(data.get("entry_price", 0)),
            "current_price":  float(data.get("current_price", 0)),
            "unrealized_pl":  float(data.get("unrealized_pl", 0)),
            "unrealized_plpc":float(data.get("unrealized_plpc", 0)),
            "sl":             data.get("sl"),               # None if not set
            "tp":             data.get("tp"),
            "broker":         data.get("broker", "alpaca_1"),
            "broker_pos_id":  bpid,
            "strategy_id":    data.get("strategy_id"),
            "status":         data.get("status", "open"),
            "opened_at":      data.get("opened_at", _utcnow()),
            "closed_at":      data.get("closed_at"),
            "last_updated":   _utcnow(),
        }

        # Match on broker_pos_id for sync updates; fall back to position_id
        for i, row in enumerate(rows):
            if (bpid and row.get("broker_pos_id") == bpid) or row.get("position_id") == pid:
                record["position_id"] = row["position_id"]   # keep original ID
                rows[i] = record
                _save(self._positions_path, rows)
                return record["position_id"]

        rows.append(record)
        _save(self._positions_path, rows)
        return pid

    def close_position(
        self,
        position_id: str,
        close_price: float,
        realized_pl: float | None = None,
    ) -> bool:
        """
        Mark a position as closed and record its close price.

        realized_pl is optional: if not supplied it is estimated from the last
        known unrealized_pl (approximate — sufficient for the agent to report).
        """
        rows = self._load_positions()
        for i, row in enumerate(rows):
            if row.get("position_id") == position_id:
                rows[i] = {
                    **row,
                    "status":       "closed",
                    "current_price": close_price,
                    "realized_pl":   realized_pl if realized_pl is not None else row.get("unrealized_pl"),
                    "unrealized_pl": 0.0,         # no unrealized P&L once closed
                    "closed_at":    _utcnow(),
                    "last_updated": _utcnow(),
                }
                _save(self._positions_path, rows)
                return True
        return False

    def update_sl_tp(
        self,
        position_id: str,
        sl: float | None = None,
        tp: float | None = None,
    ) -> bool:
        """
        Update stop-loss and/or take-profit levels on a position record.

        Only the fields explicitly passed are updated (pass None to leave
        the existing value unchanged).
        """
        rows = self._load_positions()
        for i, row in enumerate(rows):
            if row.get("position_id") == position_id:
                if sl is not None:
                    rows[i]["sl"] = sl
                if tp is not None:
                    rows[i]["tp"] = tp
                rows[i]["last_updated"] = _utcnow()
                _save(self._positions_path, rows)
                return True
        return False

    def position_summary(self) -> dict:
        """
        Return a quick summary of open positions for the context snapshot.

        Example: {"open": 3, "closed": 17, "total_unrealized_pl": 245.50}
        """
        rows = self._load_positions()
        open_rows   = [r for r in rows if r.get("status") == "open"]
        closed_rows = [r for r in rows if r.get("status") == "closed"]
        return {
            "open":               len(open_rows),
            "closed":             len(closed_rows),
            "total_unrealized_pl": round(sum(r.get("unrealized_pl", 0) for r in open_rows), 2),
        }

    # ═════════════════════════════════════════════════════════════════════════
    # TRADES
    # ═════════════════════════════════════════════════════════════════════════

    def _load_trades(self) -> list[dict]:
        return _load(self._trades_path, [])              # type: ignore[return-value]

    def list_trades(
        self,
        symbol: str | None = None,
        broker: str | None = None,
        strategy_id: str | None = None,
        status: str | None = None,        # "filled" | "cancelled" | "rejected" | None (all)
        limit: int = 50,
    ) -> list[dict]:
        """
        Return trades, most-recent first, with optional filters.

        limit defaults to 50 — enough for a meaningful P&L summary without
        flooding the LLM context window.
        """
        rows = self._load_trades()
        if symbol:
            rows = [r for r in rows if r.get("symbol", "").upper() == symbol.upper()]
        if broker:
            rows = [r for r in rows if r.get("broker") == broker]
        if strategy_id:
            rows = [r for r in rows if r.get("strategy_id") == strategy_id]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        rows.sort(key=lambda r: r.get("executed_at", ""), reverse=True)
        return rows[:limit]

    def get_trade(self, trade_id: str) -> dict | None:
        """Return a single trade by ID, or None."""
        for row in self._load_trades():
            if row.get("trade_id") == trade_id:
                return row
        return None

    def log_trade(self, data: dict) -> str:
        """
        Append a new trade record to the trade log.

        Called automatically by the agent's place_paper_order tool after a
        successful Alpaca fill, and can also be called manually for MT5 trades.

        Returns the trade_id.
        """
        rows = self._load_trades()
        tid  = data.get("trade_id") or _new_id("trade")

        record: dict = {
            "trade_id":        tid,
            "symbol":          data.get("symbol", ""),
            "side":            data.get("side", "buy"),
            "qty":             float(data.get("qty", 0)),
            "order_type":      data.get("order_type", "market"),
            "fill_price":      float(data.get("fill_price", 0)),
            "commission":      float(data.get("commission", 0)),
            "realized_pl":     data.get("realized_pl"),     # None until position closes
            "broker":          data.get("broker", "alpaca_1"),
            "broker_order_id": data.get("broker_order_id", ""),
            "strategy_id":     data.get("strategy_id"),
            "sl":              data.get("sl"),
            "tp":              data.get("tp"),
            "status":          data.get("status", "filled"),
            "executed_at":     data.get("executed_at", _utcnow()),
            "notes":           data.get("notes", ""),
        }

        rows.append(record)
        _save(self._trades_path, rows)
        return tid

    def update_trade(self, trade_id: str, updates: dict) -> bool:
        """
        Update fields on an existing trade (e.g. set realized_pl after close).
        Returns True if found and updated.
        """
        rows = self._load_trades()
        for i, row in enumerate(rows):
            if row.get("trade_id") == trade_id:
                rows[i] = {**row, **updates, "trade_id": trade_id}
                _save(self._trades_path, rows)
                return True
        return False

    def pnl_summary(
        self,
        symbol: str | None = None,
        broker: str | None = None,
        strategy_id: str | None = None,
    ) -> dict:
        """
        Compute aggregated P&L statistics across the trade log.

        WHY compute here instead of in the LLM?
          The LLM is unreliable at arithmetic over large lists.  We compute
          the numbers in Python and hand the LLM a clean summary dict.

        Returns:
            total_trades    : int
            winning_trades  : int   (realized_pl > 0)
            losing_trades   : int
            total_realized_pl: float
            avg_pl_per_trade : float
            hit_rate        : float (0.0–1.0)
            largest_win     : float
            largest_loss    : float
        """
        rows = self.list_trades(
            symbol=symbol,
            broker=broker,
            strategy_id=strategy_id,
            status="filled",        # only count filled trades
            limit=10_000,           # all records for P&L aggregate
        )
        # Filter to trades where realized_pl is known (position closed)
        closed = [r for r in rows if r.get("realized_pl") is not None]
        pls    = [float(r["realized_pl"]) for r in closed]

        if not pls:
            return {
                "total_trades": len(rows),
                "trades_with_pl": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_realized_pl": 0.0,
                "avg_pl_per_trade": 0.0,
                "hit_rate": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }

        wins   = [p for p in pls if p > 0]
        losses = [p for p in pls if p <= 0]

        return {
            "total_trades":       len(rows),
            "trades_with_pl":     len(pls),
            "winning_trades":     len(wins),
            "losing_trades":      len(losses),
            "total_realized_pl":  round(sum(pls), 2),
            "avg_pl_per_trade":   round(sum(pls) / len(pls), 2),
            "hit_rate":           round(len(wins) / len(pls), 4) if pls else 0.0,
            "largest_win":        round(max(pls), 2),
            "largest_loss":       round(min(pls), 2),
        }

    def trade_summary(self) -> dict:
        """
        Quick summary for the context snapshot (not the full P&L report).

        Example: {"total": 48, "filled": 42, "cancelled": 6, "total_realized_pl": 1230.50}
        """
        rows   = self._load_trades()
        filled = [r for r in rows if r.get("status") == "filled"]
        pls    = [float(r["realized_pl"]) for r in filled if r.get("realized_pl") is not None]
        return {
            "total":            len(rows),
            "filled":           len(filled),
            "cancelled":        sum(1 for r in rows if r.get("status") == "cancelled"),
            "rejected":         sum(1 for r in rows if r.get("status") == "rejected"),
            "total_realized_pl": round(sum(pls), 2) if pls else 0.0,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # FULL DATABASE SUMMARY (for context snapshot)
    # ═════════════════════════════════════════════════════════════════════════

    def full_summary(self) -> dict:
        """
        Return a single dict with summary stats for all three collections.

        This is called by context_builder.py and injected into every LLM prompt
        so the agent always knows the current state of the database at a glance.
        """
        return {
            "strategies": self.strategy_summary(),
            "positions":  self.position_summary(),
            "trades":     self.trade_summary(),
        }
