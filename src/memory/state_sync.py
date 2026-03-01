"""
State sync: flush agent state to Neon every 60s (OpenClaw-style, Paradigms).
Optional; does not break if DATABASE_URL is missing or table absent.
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_LAST_STATE: Dict[str, Any] = {}
_LAST_FLUSH_TIME: float = 0.0
_FLUSH_INTERVAL_SEC = 60.0


def update_agent_state(agent_name: str, state: Dict[str, Any]) -> None:
    """Update in-memory agent state (orchestrator/agents call this)."""
    global _LAST_STATE
    _LAST_STATE[agent_name] = {"state": state, "updated": time.monotonic()}


async def flush_state_to_db() -> bool:
    """
    Flush _LAST_STATE to Neon if DATABASE_URL is set and agent_state table exists.
    Returns True if flush succeeded, False otherwise (no-op if no DB).
    """
    global _LAST_FLUSH_TIME
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or not _LAST_STATE:
        return False
    try:
        from src.db.db_handler import DBHandler
        db = DBHandler(db_url)
        await db.connect()
        try:
            # Log state as agent_audit_logs entries (existing table) to avoid schema change
            for agent_name, data in _LAST_STATE.items():
                await db.log_agent_action(
                    agent_name=agent_name,
                    action_type="state_sync",
                    action_details=data.get("state", {}),
                    result="ok",
                )
            _LAST_FLUSH_TIME = time.monotonic()
            return True
        finally:
            await db.close()
    except Exception as e:
        logger.debug("state_sync flush skipped: %s", e)
        return False


async def state_sync_loop(interval_sec: float = 60.0) -> None:
    """Background loop: every interval_sec call flush_state_to_db(). Run as task."""
    while True:
        await asyncio.sleep(interval_sec)
        await flush_state_to_db()
