"""
Perception team: coordinates Librarian + subagents for ingestion and perception.
Paradigms Task 3. Wire into orchestration when needed; runs same flow as single Librarian by default.
"""
from pathlib import Path
from typing import Any, Dict

from ..librarian_agent import LibrarianAgent


class PerceptionTeam:
    """
    Coordinates ingestion: can run Librarian and optional subagents (e.g. extract_hypothesis, check_redundancy).
    """

    def __init__(self, vault_path: str, **kwargs: Any):
        self.vault_path = Path(vault_path)
        self.librarian = LibrarianAgent(vault_path=vault_path, **kwargs)

    async def run_one_cycle(self) -> Dict[str, Any]:
        """Run Librarian perceive -> reason -> act. Returns summary."""
        state = await self.librarian.perceive(None)
        plan = await self.librarian.reason(state)
        ok = await self.librarian.act(plan)
        return {"ok": ok, "plan": plan}
