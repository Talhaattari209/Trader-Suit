"""
Dashboard configuration settings.
"""

# FastAPI backend URL (change if running on a different host/port)
API_BASE_URL = "http://localhost:8000"

# Streamlit auto-refresh interval in seconds
REFRESH_INTERVAL_SECONDS = 5

# Risk thresholds for colour coding
VAR_WARNING_THRESHOLD = 2.0      # % — above this → orange
VAR_DANGER_THRESHOLD  = 3.0      # % — above this → red

DRAWDOWN_WARNING_PCT  = 0.70     # 70 % of max limit → orange
DRAWDOWN_DANGER_PCT   = 0.90     # 90 % of max limit → red
