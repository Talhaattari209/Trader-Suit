"""
Orchestration: chains Librarian -> Strategist -> Monte Carlo (Killer) -> Risk Architect.
"""
from .orchestrator import run_one_cycle

__all__ = ["run_one_cycle"]
