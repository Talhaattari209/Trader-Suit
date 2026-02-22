"""
Run the Ralph Wiggum loop from a user prompt.

  User instruction → Instruction Router → Needs_Action → (optional) one cycle

Usage (from project root):
  set VAULT_PATH=AI_Employee_Vault
  set ANTHROPIC_API_KEY=...
  python run_from_prompt.py "Implement pairs trading with cointegration"
  python run_from_prompt.py "Add pattern-based head-and-shoulders edge" --no-llm
  python run_from_prompt.py "Volume spike strategy" --cycle   # run one full cycle after routing
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.prompt.instruction_router import run_instruction
from src.edges.edge_registry import EdgeInfo


async def _run_cycle():
    """Run one orchestration cycle (Librarian -> Strategist -> Killer -> Risk Architect)."""
    from src.orchestration.orchestrator import run_one_cycle
    vault = os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    csv_path = os.environ.get("US30_CSV_PATH")
    return await run_one_cycle(vault, csv_path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Route user instruction to vault and optionally run one cycle.")
    parser.add_argument("instruction", nargs="?", default=None, help="User idea/instruction (e.g. 'Add pairs trading edge')")
    parser.add_argument("--no-llm", action="store_true", help="Use keyword match only, no LLM for research request")
    parser.add_argument("--cycle", action="store_true", help="Run one full orchestration cycle after writing to vault")
    parser.add_argument("--vault", default=None, help="Vault path (default: VAULT_PATH env or AI_Employee_Vault)")
    args = parser.parse_args()

    vault_path = args.vault or os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    Path(vault_path).mkdir(parents=True, exist_ok=True)
    (Path(vault_path) / "Needs_Action" / "ResearchInput").mkdir(parents=True, exist_ok=True)

    instruction = args.instruction
    if not instruction:
        print("Enter your instruction (one line): ", end="")
        instruction = sys.stdin.readline().strip()
    if not instruction:
        print("No instruction provided. Exiting.")
        sys.exit(1)

    path, matched = asyncio.run(run_instruction(instruction, vault_path, use_llm=not args.no_llm))
    print(f"Wrote research request to: {path}")
    if matched:
        print("Matched edge(s):", [e.edge_type for e in matched])
        if matched[0].workflow_module:
            print("Workflow module:", matched[0].workflow_module)

    if args.cycle:
        print("Running one orchestration cycle...")
        summary = asyncio.run(_run_cycle())
        print("Cycle summary:", summary)


if __name__ == "__main__":
    main()
