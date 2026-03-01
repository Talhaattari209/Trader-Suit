"""
DB handlers for agents: check_redundancy (Librarian) vs institutional memory.
Uses Neon; optional pgvector for similarity. If pgvector or DB unavailable, returns (False, []) so callers don't block.
"""
import os
from typing import List, Tuple

# Optional: from pgvector.psycopg import Vector  # when schema has embedding column


def _jaccard_sim(a: str, b: str) -> float:
    """Simple word-set Jaccard similarity (no embedding)."""
    if not a or not b:
        return 0.0
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


async def async_check_redundancy(
    hypo_text: str,
    threshold: float = 0.8,
    database_url: str | None = None,
) -> Tuple[bool, List[dict]]:
    """Async: compare hypothesis against alphas/graveyard. Use from async agents (e.g. Librarian)."""
    url = database_url or os.environ.get("DATABASE_URL")
    if not url or not hypo_text or not hypo_text.strip():
        return False, []
    try:
        import asyncpg
    except ImportError:
        return False, []
    try:
        pool = await asyncpg.create_pool(dsn=url)
        try:
            async with pool.acquire() as conn:
                similar = []
                hypo_lower = hypo_text.lower()
                try:
                    rows = await conn.fetch("SELECT id, name, description FROM alphas LIMIT 50")
                    for r in rows:
                        desc = (r.get("description") or "") or (r.get("name") or "")
                        if hypo_lower in desc or desc.lower() in hypo_lower or _jaccard_sim(hypo_text, desc) >= threshold:
                            similar.append({"id": r["id"], "source": "alphas", "text": (desc or "")[:200]})
                except Exception:
                    pass
                try:
                    g = await conn.fetch("SELECT id, hypothesis FROM strategy_graveyard LIMIT 50")
                    for r in g:
                        h = (r.get("hypothesis") or "")[:1000]
                        if hypo_lower in h or _jaccard_sim(hypo_text, h) >= threshold:
                            similar.append({"id": r["id"], "source": "graveyard", "text": h[:200]})
                except Exception:
                    pass
                return (len(similar) > 0, similar)
        finally:
            await pool.close()
    except Exception:
        return False, []


def check_redundancy(
    hypo_text: str,
    threshold: float = 0.8,
    database_url: str | None = None,
) -> Tuple[bool, List[dict]]:
    """
    Compare hypothesis text against institutional memory (alphas/graveyard) via vector similarity.
    Returns (is_redundant, list of similar entries). If DB or pgvector not available, returns (False, []).

    hypo_text: New hypothesis to check.
    threshold: Cosine similarity threshold (0-1); above = redundant.
    database_url: Override; default os.environ.get("DATABASE_URL").
    """
    url = database_url or os.environ.get("DATABASE_URL")
    if not url or not hypo_text or not hypo_text.strip():
        return False, []

    try:
        import asyncio
        try:
            import asyncpg
        except ImportError:
            return False, []
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return False, []
        return loop.run_until_complete(async_check_redundancy(hypo_text, threshold, url))
    except Exception:
        return False, []
