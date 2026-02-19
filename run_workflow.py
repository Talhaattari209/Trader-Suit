"""
Run the full Alpha Research workflow with database logging.

  Watchers (optional) -> Librarian -> Strategist -> Killer -> Risk Architect (optional)
  All agent outcomes are logged to Neon (agent_audit_logs). Killer REJECTs are
  recorded in strategy_graveyard.

Requires .env with:
  DATABASE_URL=postgresql://...
  VAULT_PATH=AI_Employee_Vault
  US30_CSV_PATH=path/to/us30.csv   # optional, for Killer
  ANTHROPIC_API_KEY=...            # for Librarian / Strategist

Usage (from project root):
  python run_workflow.py              # one cycle with DB
  python run_workflow.py --once       # same (explicit)
  python run_workflow.py --loop       # run every N seconds (default 60)
  python run_workflow.py --loop --interval 120
  python run_workflow.py --skip-db   # run pipeline without DB
  python run_workflow.py --skip-watchers
"""
import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Load .env before reading env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agents import KillerAgent, LibrarianAgent, RiskArchitectAgent, StrategistAgent
from src.db.db_handler import DBHandler
from src.watchers import DataIngestionWatcher, ResearchWatcher


def ensure_vault_dirs(vault_path: Path) -> None:
    (vault_path / "Needs_Action").mkdir(parents=True, exist_ok=True)
    (vault_path / "Plans").mkdir(parents=True, exist_ok=True)
    (vault_path / "Logs").mkdir(parents=True, exist_ok=True)
    (vault_path / "Research_Data").mkdir(parents=True, exist_ok=True)
    (vault_path / "Needs_Action" / "ResearchInput").mkdir(parents=True, exist_ok=True)
    (vault_path / "Needs_Action" / "DataSource").mkdir(parents=True, exist_ok=True)


def run_watchers(vault_path: str) -> int:
    """One cycle: ingest from ResearchInput/DataSource into Needs_Action. Returns count of items created."""
    total = 0
    research_input = os.environ.get("RESEARCH_INPUT_PATH", str(Path(vault_path) / "Needs_Action" / "ResearchInput"))
    data_source = os.environ.get("DATA_SOURCE_PATH", str(Path(vault_path) / "Needs_Action" / "DataSource"))
    if Path(research_input).exists():
        w = ResearchWatcher(vault_path=vault_path, research_input_path=research_input)
        total += w.run_once()
    if Path(data_source).exists():
        w = DataIngestionWatcher(vault_path=vault_path, data_source_path=data_source)
        total += w.run_once()
    return total


async def run_one_cycle(
    vault_path: str,
    csv_path: str | None,
    db: DBHandler | None,
    *,
    run_watchers_step: bool = True,
    run_librarian: bool = True,
    run_strategist: bool = True,
    run_killer: bool = True,
    run_risk: bool = True,
) -> dict:
    """One full workflow cycle. If db is set, logs each agent action and Killer REJECTs to graveyard."""
    summary = {}

    # 0. Watchers: world -> Needs_Action
    if run_watchers_step:
        created = run_watchers(vault_path)
        summary["watchers"] = {"created": created}
        if db:
            await db.log_agent_action("Watchers", "ingestion_cycle", {"created": created}, "success")

    # 1. Librarian: Needs_Action -> Plans
    if run_librarian:
        try:
            librarian = LibrarianAgent(vault_path=vault_path)
            state = await librarian.perceive(None)
            plan = await librarian.reason(state)
            ok = await librarian.act(plan)
            summary["librarian"] = {"ok": ok, "plans_count": len(plan.get("plans") or [])}
            if db:
                await db.log_agent_action(
                    "LibrarianAgent", "research_plan", {"plans_count": summary["librarian"]["plans_count"]}, "success" if ok else "failure"
                )
        except Exception as e:
            logging.exception("Librarian failed: %s", e)
            summary["librarian"] = {"ok": False, "error": str(e)}
            if db:
                await db.log_agent_action("LibrarianAgent", "research_plan", {"error": str(e)}, "failure")

    # 2. Strategist: Plans -> drafts
    if run_strategist:
        try:
            strategist = StrategistAgent(vault_path=vault_path)
            state = await strategist.perceive(None)
            plan = await strategist.reason(state)
            ok = await strategist.act(plan)
            summary["strategist"] = {"ok": ok, "plan": plan}
            if db:
                await db.log_agent_action("StrategistAgent", "strategy_generation", {"ok": ok}, "success" if ok else "failure")
        except Exception as e:
            logging.exception("Strategist failed: %s", e)
            summary["strategist"] = {"ok": False, "error": str(e)}
            if db:
                await db.log_agent_action("StrategistAgent", "strategy_generation", {"error": str(e)}, "failure")

    # 3. Killer: Monte Carlo validation -> Risk Audit in Logs
    if run_killer:
        try:
            killer = KillerAgent(vault_path=vault_path, csv_path=csv_path)
            state = await killer.perceive(csv_path)
            plan = await killer.reason(state)
            ok = await killer.act(plan)
            decision = plan.get("decision") if isinstance(plan, dict) else None
            reason = plan.get("reason") if isinstance(plan, dict) else None
            summary["killer"] = {"ok": ok, "decision": decision, "reason": reason}
            if db:
                await db.log_agent_action(
                    "KillerAgent", "monte_carlo_validation",
                    {"decision": decision, "reason": reason, "prob_of_ruin": plan.get("prob_of_ruin")},
                    "success" if ok else "failure",
                )
                if decision == "REJECT" and reason:
                    await db.add_to_graveyard(
                        hypothesis="Strategy failed Killer Agent validation",
                        reason_for_failure=reason,
                        context={"decision": decision, "prob_of_ruin": plan.get("prob_of_ruin")},
                    )
        except Exception as e:
            logging.exception("Killer failed: %s", e)
            summary["killer"] = {"ok": False, "error": str(e)}
            if db:
                await db.log_agent_action("KillerAgent", "monte_carlo_validation", {"error": str(e)}, "failure")

    # 4. Risk Architect (optional)
    if run_risk:
        try:
            risk = RiskArchitectAgent(vault_path=vault_path)
            state = await risk.perceive({})
            plan = await risk.reason(state)
            ok = await risk.act(plan)
            summary["risk_architect"] = {"ok": ok, "position_fraction": plan.get("position_fraction")}
            if db:
                await db.log_agent_action("RiskArchitectAgent", "risk_config", {"ok": ok}, "success" if ok else "failure")
        except Exception as e:
            logging.exception("Risk Architect failed: %s", e)
            summary["risk_architect"] = {"ok": False, "error": str(e)}
            if db:
                await db.log_agent_action("RiskArchitectAgent", "risk_config", {"error": str(e)}, "failure")

    return summary


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Run Alpha Research workflow with optional DB logging")
    parser.add_argument("--once", action="store_true", help="Run a single cycle (default if not --loop)")
    parser.add_argument("--loop", action="store_true", help="Run forever, sleeping between cycles")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between cycles when using --loop (default 60)")
    parser.add_argument("--skip-db", action="store_true", help="Do not connect to DB or log agent actions")
    parser.add_argument("--skip-watchers", action="store_true", help="Do not run watchers (ingestion)")
    parser.add_argument("--vault", default=None, help="Override VAULT_PATH")
    parser.add_argument("--csv", default=None, help="Override US30_CSV_PATH")
    args = parser.parse_args()

    vault_path = args.vault or os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    csv_path = args.csv or os.environ.get("US30_CSV_PATH")
    use_db = not args.skip_db
    run_watchers_step = not args.skip_watchers

    ensure_vault_dirs(Path(vault_path))

    db: DBHandler | None = None
    if use_db:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.warning("DATABASE_URL not set; run without DB (use --skip-db to suppress this)")
            use_db = False
        else:
            db = DBHandler(database_url=database_url)

    async def one_cycle():
        if db:
            await db.connect()
        try:
            return await run_one_cycle(
                vault_path,
                csv_path,
                db if use_db else None,
                run_watchers_step=run_watchers_step,
                run_librarian=True,
                run_strategist=True,
                run_killer=True,
                run_risk=True,
            )
        finally:
            if db:
                await db.close()

    if args.loop:
        logger.info("Workflow loop: Watchers -> Librarian -> Strategist -> Killer -> Risk. Ctrl+C to stop. DB=%s", use_db)
        while True:
            try:
                summary = asyncio.run(one_cycle())
                logger.info("Cycle summary: %s", summary)
            except KeyboardInterrupt:
                logger.info("Stopped.")
                break
            except Exception as e:
                logger.exception("Cycle error: %s", e)
            if summary.get("killer", {}).get("decision") == "APPROVE":
                logger.info("🎉 FOUND STRATEGY MEETING CRITERIA! STOPPING LOOP.")
                logger.info(f"Reason: {summary['killer'].get('reason')}")
                break

            logger.info("Sleeping %ds...", args.interval)
            time.sleep(args.interval)
    else:
        summary = asyncio.run(one_cycle())
        print("Workflow summary:", summary)
        return summary


if __name__ == "__main__":
    main()
