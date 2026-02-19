"""
Ralph Wiggum Loop: Intelligence Layer orchestration.

  [World] -> Watchers -> [Needs_Action] -> Librarian -> [Plans] -> Strategist -> [Drafts] -> Killer Agent -> [Logs/Done]

Usage (from project root):
  set VAULT_PATH=AI_Employee_Vault
  set US30_CSV_PATH=path\to\us30.csv
  set ANTHROPIC_API_KEY=sk-...
  python run_ralph.py

Optional: RESEARCH_INPUT_PATH, DATA_SOURCE_PATH for watchers (default: vault/Needs_Action/ResearchInput, vault/Needs_Action/DataSource).
"""
import asyncio
import os
import sys
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agents import KillerAgent, LibrarianAgent, StrategistAgent
from src.watchers import ResearchWatcher, DataIngestionWatcher


def ensure_vault_dirs(vault_path: Path):
    (vault_path / "Needs_Action").mkdir(parents=True, exist_ok=True)
    (vault_path / "Plans").mkdir(parents=True, exist_ok=True)
    (vault_path / "Logs").mkdir(parents=True, exist_ok=True)
    (vault_path / "Research_Data").mkdir(parents=True, exist_ok=True)
    # Optional input dirs for watchers (so iterdir doesn't fail)
    (vault_path / "Needs_Action" / "ResearchInput").mkdir(parents=True, exist_ok=True)
    (vault_path / "Needs_Action" / "DataSource").mkdir(parents=True, exist_ok=True)


def run_watchers(vault_path: str) -> int:
    """One cycle: ingest from world into Needs_Action. Returns total items created."""
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


async def run_librarian(vault_path: str) -> bool:
    librarian = LibrarianAgent(vault_path=vault_path)
    state = await librarian.perceive(None)
    plan = await librarian.reason(state)
    return await librarian.act(plan)


async def run_strategist(vault_path: str) -> bool:
    strategist = StrategistAgent(vault_path=vault_path)
    state = await strategist.perceive(None)
    plan = await strategist.reason(state)
    return await strategist.act(plan)


async def run_killer(vault_path: str, csv_path: str | None = None) -> bool:
    agent = KillerAgent(vault_path=vault_path, csv_path=csv_path)
    state = await agent.perceive(csv_path)
    plan = await agent.reason(state)
    return await agent.act(plan)


async def one_cycle(vault_path: str, csv_path: str | None):
    run_watchers(vault_path)
    await run_librarian(vault_path)
    await run_strategist(vault_path)
    await run_killer(vault_path, csv_path)


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

    vault = os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    csv_path = os.environ.get("US30_CSV_PATH")
    vault_path = Path(vault)
    ensure_vault_dirs(vault_path)

    print("Ralph Wiggum loop: Watchers -> Librarian -> Strategist -> Killer. Ctrl+C to stop.")
    while True:
        try:
            asyncio.run(one_cycle(vault, csv_path))
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            logging.exception("Cycle error: %s", e)
        print("Sleeping 60s...")
        import time
        time.sleep(60)


if __name__ == "__main__":
    main()
