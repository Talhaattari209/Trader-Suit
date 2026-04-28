"""
src/autonomous_agent/__init__.py
================================
Public API for the Autonomous Agent package.

This package is intentionally self-contained so it can be developed,
tested, and reviewed independently of the rest of the Trader-Suit system.
Every cross-module import goes through this file, giving us a single
point to refactor if folder structure changes.

Exports (imported by FastAPI routes and the Streamlit widget):
  - process_message   : async entry point for the LLM agent loop
  - render_widget     : injects the floating chat widget into a Streamlit page
"""

# Re-export the two public surfaces — one for the backend, one for the frontend.
# Using explicit imports (not star-imports) so static analysis tools can trace them.
from src.autonomous_agent.agent_core import process_message      # noqa: F401  (re-exported)
from src.autonomous_agent.widget import render_autonomous_agent_widget as render_widget  # noqa: F401

__all__ = ["process_message", "render_widget"]
