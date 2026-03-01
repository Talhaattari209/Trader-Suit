"""
Validation team: coordinates Killer + Risk Architect in a loop (validate -> risk check -> re-validate).
Paradigms Task 3. Wire into orchestration when needed.
"""
from pathlib import Path
from typing import Any, Dict

from ..killer_agent import KillerAgent
from ..risk_architect import RiskArchitectAgent


class ValidationTeam:
    """
    Runs Killer then Risk Architect; can be extended to loop (e.g. risk check then re-validate).
    """

    def __init__(self, vault_path: str, csv_path: str | None = None, **kwargs: Any):
        self.vault_path = Path(vault_path)
        self.killer = KillerAgent(vault_path=vault_path, csv_path=csv_path, **kwargs)
        self.risk = RiskArchitectAgent(vault_path=vault_path, **kwargs)

    async def run_one_cycle(self) -> Dict[str, Any]:
        """Run Killer then Risk. Returns combined summary."""
        state = await self.killer.perceive(self.killer.csv_path)
        plan = await self.killer.reason(state)
        ok_k = await self.killer.act(plan)
        risk_state = await self.risk.perceive({})
        risk_plan = await self.risk.reason(risk_state)
        ok_r = await self.risk.act(risk_plan)
        return {
            "killer": {"ok": ok_k, "decision": plan.get("decision"), "reason": plan.get("reason")},
            "risk_architect": {"ok": ok_r, "position_fraction": risk_plan.get("position_fraction")},
        }
