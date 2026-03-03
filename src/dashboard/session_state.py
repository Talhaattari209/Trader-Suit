"""
Session state for Trader-Suit UI.
Initializes and provides cross-page persistence (selected strategy, date range, filters).
Call init_session_state() once at app startup (e.g. in app.py).
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Any
from src.dashboard.config import DASHBOARD_DEFAULT_DAYS


def init_session_state() -> None:
    """Initialize default keys in st.session_state if not present."""
    defaults = {
        # Navigation / selection
        "selected_strategy_id": None,
        "selected_strategy_name": None,
        "selected_vault_folder": "Needs_Action",
        "selected_file_path": None,
        # Dashboard filters
        "date_range_start": datetime.utcnow().date() - timedelta(days=DASHBOARD_DEFAULT_DAYS),
        "date_range_end": datetime.utcnow().date(),
        "regime_filters": [],
        "session_filters": [],
        # Alpha Idea Lab
        "alpha_prompt": "",
        "alpha_template": None,
        "alpha_data_sources": [],
        "research_plan_preview": None,
        "proceed_to_builder": False,
        "alpha_chat_messages": [],  # list of {"role": "user"|"assistant", "content": str}
        "alpha_iteration_count": 0,
        "alpha_uploaded_file": None,
        # Backtester
        "backtest_strategy_id": None,
        "backtest_iterations": 5000,
        "backtest_stress_tests": [],
        # Execution / Cockpit
        "auto_refresh": True,
        "refresh_interval_sec": 5,
        # No-Code Builder: blocks for Specs-Driven mode [{"code", "specs", "agent_comment"}, ...]
        "builder_blocks": [],
        "builder_specs_input": "",  # global specs text area (e.g. "Entry on RSI<30, exit ATR*2")
        "builder_colab_triggered": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_date_range():
    """Return (start_date, end_date) from session state."""
    return (
        st.session_state.get("date_range_start"),
        st.session_state.get("date_range_end"),
    )


def set_date_range(start: Any, end: Any) -> None:
    """Update session state date range."""
    st.session_state["date_range_start"] = start
    st.session_state["date_range_end"] = end


def get_selected_strategy():
    """Return (id, name) of selected strategy or (None, None)."""
    return (
        st.session_state.get("selected_strategy_id"),
        st.session_state.get("selected_strategy_name"),
    )


def set_selected_strategy(strategy_id: str | None, name: str | None) -> None:
    """Set selected strategy for use on Backtester, Library detail, etc."""
    st.session_state["selected_strategy_id"] = strategy_id
    st.session_state["selected_strategy_name"] = name
