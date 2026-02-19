"""
Run the Killer Agent on the default US30 dataset.
Usage (from project root):
  python run_killer_agent.py
Or with custom paths:
  set US30_CSV_PATH=C:\path\to\your\backtest.csv
  set VAULT_PATH=AI_Employee_Vault
  python run_killer_agent.py
"""
import asyncio
import os
from pathlib import Path

# Ensure project root is on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agents.killer_agent import KillerAgent


def main():
    vault = os.environ.get("VAULT_PATH", "AI_Employee_Vault")
    csv_path = os.environ.get(
        "US30_CSV_PATH",
        r"C:\Users\User\Downloads\claude\Dataset-Testing-US30\usa30idxusd-m5-bid-2025-10-09-2025-11-29.csv",
    )
    agent = KillerAgent(vault_path=vault, csv_path=csv_path)

    async def run():
        state = await agent.perceive(csv_path)
        plan = await agent.reason(state)
        success = await agent.act(plan)
        print(f"Decision: {plan.get('decision')} — {plan.get('reason')}")
        return success

    asyncio.run(run())


if __name__ == "__main__":
    main()
