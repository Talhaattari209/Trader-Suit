"""
Dashboard configuration — Trader-Suit UI.
Single source of truth for layout, theme, API, and metric thresholds.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# API & Backend
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("TRADER_API_URL", "http://localhost:8000")
REFRESH_INTERVAL_SECONDS = int(os.environ.get("DASHBOARD_REFRESH_SEC", "5"))
VAULT_PATH = os.environ.get("VAULT_PATH", "AI_Employee_Vault")

# ---------------------------------------------------------------------------
# Layout ratios (sidebar : main). Use with st.columns([s, m]) so s/(s+m) = ratio.
# Spec: most pages 1:4; some 1:5 or 1:3.
# Streamlit columns take integer weights: [1, 4] => 1:4.
# ---------------------------------------------------------------------------
LAYOUT_SIDEBAR_MAIN = (1, 4)   # default 1:4
LAYOUT_SIDEBAR_MAIN_NARROW = (1, 3)   # sidebar heavier: Alpha Lab, Backtester, Execution
LAYOUT_SIDEBAR_MAIN_WIDE = (1, 5)     # sidebar lighter: Dashboard, No-Code Builder
LAYOUT_MAIN_SPLIT_2_1 = (2, 1)        # main area two columns 2:1
LAYOUT_MAIN_SPLIT_1_1 = (1, 1)       # main area two columns 1:1

# ---------------------------------------------------------------------------
# Risk thresholds (existing)
# ---------------------------------------------------------------------------
VAR_WARNING_THRESHOLD = 2.0      # % — above this → orange
VAR_DANGER_THRESHOLD = 3.0       # % — above this → red
DRAWDOWN_WARNING_PCT = 0.70      # 70% of max limit → orange
DRAWDOWN_DANGER_PCT = 0.90       # 90% of max limit → red

# ---------------------------------------------------------------------------
# Metric thresholds for color-coding (green = good, red = bad)
# Used in metric cards across Dashboard, Strategy Library, Backtester.
# ---------------------------------------------------------------------------
# Sharpe: target > 1
SHARPE_TARGET_MIN = 1.0
# Sortino: target > 1.5
SORTINO_TARGET_MIN = 1.5
# Max drawdown: target < 20%
MAX_DD_TARGET_PCT = 20.0
# Hit rate: target > 55%
HIT_RATE_TARGET_MIN = 0.55
# e-ratio: target > 1.5
E_RATIO_TARGET_MIN = 1.5

# ---------------------------------------------------------------------------
# Theme (dark default — trading vibe)
# ---------------------------------------------------------------------------
THEME = {
    "background": "#0d1117",
    "surface": "#161b22",
    "border": "#30363d",
    "text": "#e6edf3",
    "text_muted": "#8b949e",
    "accent": "#58a6ff",
    "success": "#3fb950",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#58a6ff",
}

# ---------------------------------------------------------------------------
# Vault folder names (for Vault Explorer)
# ---------------------------------------------------------------------------
VAULT_FOLDERS = ("Needs_Action", "Plans", "Approved", "Reports", "Logs")

# ---------------------------------------------------------------------------
# Alpha Idea Lab templates
# ---------------------------------------------------------------------------
ALPHA_TEMPLATES = [
    "Momentum Breakout",
    "Pattern Failure",
    "Mean-Reversion Post-News",
    "Trend Following (Hurst > 0.5)",
    "Session-Based (London/NY)",
]

# ---------------------------------------------------------------------------
# Colab execution (no-code builder, optimization lab, Monte Carlo)
# ---------------------------------------------------------------------------
# URL to open Colab notebook for running model code. Use {params} for query string if needed.
COLAB_NOTEBOOK_URL = os.environ.get(
    "COLAB_NOTEBOOK_URL",
    "https://colab.research.google.com/github/your-org/claude/blob/main/colab/run_rl_dl_ml_colab.ipynb",
)
# Optional: path on Drive where builder writes generated strategy for Colab to pick up.
COLAB_DRIVE_STRATEGY_PATH = os.environ.get(
    "COLAB_DRIVE_STRATEGY_PATH",
    "Alpha_FTE_Project/generated_strategy.py",
)

# ---------------------------------------------------------------------------
# No-Code Builder: default workflow step names (8 steps)
# ---------------------------------------------------------------------------
BUILDER_STEP_NAMES = [
    "Data & Source",
    "Features & Indicators",
    "Model Architecture",
    "Entry Logic",
    "Exit Logic",
    "Risk Sizing",
    "Filters & Regime",
    "Output & Export",
]

# ---------------------------------------------------------------------------
# Dashboard Defaults
# ---------------------------------------------------------------------------
DASHBOARD_DEFAULT_DAYS = 30
