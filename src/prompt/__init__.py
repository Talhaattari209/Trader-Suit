"""
User instruction entry point: route prompt to Needs_Action and edge_type.
See Different_Edges/IMPLEMENTATION_PLAN.md.
"""
from .instruction_router import run_instruction, write_instruction_to_vault

__all__ = ["run_instruction", "write_instruction_to_vault"]
