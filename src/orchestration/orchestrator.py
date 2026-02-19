"""
Orchestrator: chains Librarian -> Strategist -> Monte Carlo (Killer) -> Risk Architect.
Implements the flow from Status-Feb-18.md section 4 (Orchestration Logic Review).
Run without Docker for testing (e.g. uv run python -m src.orchestration.orchestrator).
"""
import asyncio
import logging
import os
from pathlib import Path

# Allow running as script from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.agents import KillerAgent, LibrarianAgent, RiskArchitectAgent, StrategistAgent


logger = logging.getLogger(__name__)


async def run_one_cycle(
    vault_path: str,
    csv_path: str | None = None,
    *,
    run_librarian: bool = True,
    run_strategist: bool = True,
    run_killer: bool = True,
    run_risk: bool = True,
) -> dict:
    """
    One full cycle: Librarian -> Strategist -> Killer (Monte Carlo) -> Risk Architect.
    Returns a summary dict with per-agent results (e.g. plan created, decision, risk_config).
    """
    vault = Path(vault_path)
    csv_path = csv_path or os.environ.get("US30_CSV_PATH")
    summary = {}

    # 1. Librarian: Needs_Action -> Plans (research plans)
    if run_librarian:
        try:
            librarian = LibrarianAgent(vault_path=vault_path)
            state = await librarian.perceive(None)
            plan = await librarian.reason(state)
            ok = await librarian.act(plan)
            summary["librarian"] = {"ok": ok, "plan": plan}
        except Exception as e:
            logger.exception("Librarian failed: %s", e)
            summary["librarian"] = {"ok": False, "error": str(e)}

    # 2. Strategist: Plans -> drafts (strategy code)
    if run_strategist:
        try:
            strategist = StrategistAgent(vault_path=vault_path)
            state = await strategist.perceive(None)
            plan = await strategist.reason(state)
            ok = await strategist.act(plan)
            summary["strategist"] = {"ok": ok, "plan": plan}
        except Exception as e:
            logger.exception("Strategist failed: %s", e)
            summary["strategist"] = {"ok": False, "error": str(e)}

    # 3. Killer (Monte Carlo): CSV backtest validation -> Risk Audit in Logs
    if run_killer:
        try:
            killer = KillerAgent(vault_path=vault_path, csv_path=csv_path)
            state = await killer.perceive(csv_path)
            plan = await killer.reason(state)
            ok = await killer.act(plan)
            summary["killer"] = {
                "ok": ok,
                "decision": plan.get("decision") if isinstance(plan, dict) else None,
                "reason": plan.get("reason") if isinstance(plan, dict) else None,
            }
        except Exception as e:
            logger.exception("Killer failed: %s", e)
            summary["killer"] = {"ok": False, "error": str(e)}

    # 4. Risk Architect: optional risk config from current state (equity, returns, etc.)
    if run_risk:
        try:
            risk_state = {}
            risk = RiskArchitectAgent(vault_path=vault_path)
            state = await risk.perceive(risk_state)
            plan = await risk.reason(state)
            ok = await risk.act(plan)
            summary["risk_architect"] = {"ok": ok, "position_fraction": plan.get("position_fraction")}
        except Exception as e:
            logger.exception("Risk Architect failed: %s", e)
            summary["risk_architect"] = {"ok": False, "error": str(e)}

    return summary


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
    vault = os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    csv_path = os.environ.get("US30_CSV_PATH")
    Path(vault).mkdir(parents=True, exist_ok=True)
    summary = asyncio.run(run_one_cycle(vault, csv_path))
    print("Orchestrator cycle summary:", summary)
    return summary


if __name__ == "__main__":
    main()
