"""
FastAPI Backend for the Trader's Workbench Dashboard.
Serves mock data for signals, risk metrics, and agent status.
In production, connect to the DB via DBHandler.
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Trader's Workbench API",
    description="Backend API for the Real-Time Trading Dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class Signal(BaseModel):
    id: str
    strategy_name: str
    symbol: str
    direction: str          # "LONG" | "SHORT"
    timeframe: str
    confidence: float       # 0.0 – 1.0
    candle_close_in_sec: int
    status: str             # "ACTIVE" | "PENDING"
    detected_at: str


class RiskMetrics(BaseModel):
    portfolio_var: float        # Value-at-Risk (%)
    current_drawdown: float     # Current drawdown (%)
    max_drawdown_limit: float   # Max allowed drawdown (%)
    exposure: Dict[str, float]  # Asset class → % exposure


class AgentStatus(BaseModel):
    name: str
    status: str             # "HEALTHY" | "WARNING" | "DOWN"
    last_heartbeat: str
    tasks_completed: int


class SystemStatus(BaseModel):
    agents: List[AgentStatus]
    uptime_seconds: int
    timestamp: str


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

SYMBOLS = ["US30", "EURUSD", "GBPUSD", "XAUUSD", "NAS100", "BTCUSD"]
STRATEGIES = [
    "RSI_Reversal_H1",
    "Breakout_Momentum_D1",
    "MA_Crossover_M15",
    "VWAP_Reversion_H4",
    "Regime_Trend_Follow",
]
TIMEFRAMES = ["M15", "H1", "H4", "D1"]
ASSET_CLASSES = ["Indices", "Forex", "Commodities", "Crypto"]


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _mock_signals(n: int = 5) -> List[Signal]:
    signals = []
    for i in range(n):
        signals.append(
            Signal(
                id=f"SIG-{1000 + i}",
                strategy_name=random.choice(STRATEGIES),
                symbol=random.choice(SYMBOLS),
                direction=random.choice(["LONG", "SHORT"]),
                timeframe=random.choice(TIMEFRAMES),
                confidence=round(random.uniform(0.55, 0.95), 2),
                candle_close_in_sec=random.randint(30, 3600),
                status=random.choice(["ACTIVE", "PENDING"]),
                detected_at=_now_str(),
            )
        )
    return signals


def _mock_risk() -> RiskMetrics:
    exposure = {cls: round(random.uniform(5, 40), 1) for cls in ASSET_CLASSES}
    # Normalise to 100 %
    total = sum(exposure.values())
    exposure = {k: round(v / total * 100, 1) for k, v in exposure.items()}
    return RiskMetrics(
        portfolio_var=round(random.uniform(0.5, 3.5), 2),
        current_drawdown=round(random.uniform(0.0, 8.0), 2),
        max_drawdown_limit=10.0,
        exposure=exposure,
    )


def _mock_agents() -> List[AgentStatus]:
    agents_cfg = [
        ("Watcher", "HEALTHY", random.randint(200, 1000)),
        ("Librarian", random.choice(["HEALTHY", "WARNING"]), random.randint(50, 500)),
        ("Strategist", random.choice(["HEALTHY", "WARNING", "DOWN"]), random.randint(10, 300)),
    ]
    result = []
    for name, status, tasks in agents_cfg:
        hb = datetime.utcnow() - timedelta(seconds=random.randint(5, 120))
        result.append(
            AgentStatus(
                name=name,
                status=status,
                last_heartbeat=hb.strftime("%Y-%m-%d %H:%M:%S UTC"),
                tasks_completed=tasks,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {"message": "Trader's Workbench API is running", "timestamp": _now_str()}


@app.get("/status", response_model=SystemStatus, tags=["Agents"])
def get_system_status():
    """Return health status of all agents."""
    return SystemStatus(
        agents=_mock_agents(),
        uptime_seconds=random.randint(3600, 86400),
        timestamp=_now_str(),
    )


@app.get("/signals", response_model=List[Signal], tags=["Signals"])
def get_signals(limit: int = 10):
    """Return active trading signals from Approved strategies."""
    return _mock_signals(n=min(limit, 20))


@app.get("/risk", response_model=RiskMetrics, tags=["Risk"])
def get_risk_metrics():
    """Return current portfolio risk metrics."""
    return _mock_risk()
