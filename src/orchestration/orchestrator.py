"""
Orchestrator: chains Librarian -> Strategist -> Monte Carlo (Killer) -> Risk Architect.
Implements the flow from Status-Feb-18.md section 4 (Orchestration Logic Review).
Run without Docker for testing (e.g. uv run python -m src.orchestration.orchestrator).

Optional: use_bootstrap_and_skills=True loads AGENTS.md, SOUL.md, TOOLS.md, etc.
and per-agent SKILL.md from src/skills/ and injects them into agent context (ARCHITECTURE_ADJUSTMENT_PLAN).
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


def _load_context(vault_path: str, use_bootstrap_and_skills: bool):
    """Load bootstrap and per-agent skill context. Returns (bootstrap_str, skill_getter)."""
    if not use_bootstrap_and_skills:
        return "", lambda _: ""
    try:
        from src.memory.bootstrap_loader import load_bootstrap
        from src.skills.loader import load_skill_for_agent
        root = Path(vault_path).resolve().parent
        bootstrap = load_bootstrap(workspace_root=root)
        def skill_getter(agent_key: str) -> str:
            return load_skill_for_agent(agent_key, workspace_root=root)
        return bootstrap, skill_getter
    except Exception as e:
        logger.warning("Bootstrap/skill loading skipped: %s", e)
        return "", lambda _: ""


async def run_one_cycle(
    vault_path: str,
    csv_path: str | None = None,
    *,
    run_librarian: bool = True,
    run_strategist: bool = True,
    run_killer: bool = True,
    run_risk: bool = True,
    use_bootstrap_and_skills: bool = False,
) -> dict:
    """
    One full cycle: Librarian -> Strategist -> Killer (Monte Carlo) -> Risk Architect.
    Returns a summary dict with per-agent results (e.g. plan created, decision, risk_config).

    If use_bootstrap_and_skills=True, loads bootstrap files (AGENTS.md, SOUL.md, etc.) and
    per-agent SKILL.md and passes them into agents (optional context; no change when False).
    """
    vault = Path(vault_path)
    csv_path = csv_path or os.environ.get("US30_CSV_PATH")
    summary = {}

    bootstrap, skill_getter = _load_context(vault_path, use_bootstrap_and_skills)
    def _ctx(agent_key: str):
        return bootstrap, skill_getter(agent_key)

    # 1. Librarian: Needs_Action -> Plans (research plans)
    if run_librarian:
        try:
            b, s = _ctx("librarian")
            librarian = LibrarianAgent(vault_path=vault_path, bootstrap_context=b, skill_context=s)
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
            b, s = _ctx("strategist")
            strategist = StrategistAgent(vault_path=vault_path, bootstrap_context=b, skill_context=s)
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
            b, s = _ctx("killer")
            killer = KillerAgent(vault_path=vault_path, csv_path=csv_path, bootstrap_context=b, skill_context=s)
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
            b, s = _ctx("risk_architect")
            risk = RiskArchitectAgent(vault_path=vault_path, bootstrap_context=b, skill_context=s)
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
