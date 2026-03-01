"""
FastAPI Backend for the Trader's Workbench Dashboard.
Uses Alpaca when ALPACA_API_KEY is set; otherwise mock data.
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from src.api.alpaca_service import (
        is_alpaca_available,
        get_account,
        get_positions,
        get_portfolio_history,
        get_last_quote,
    )
except ImportError:
    def is_alpaca_available(): return False
    def get_account(): return None
    def get_positions(): return []
    def get_portfolio_history(days=30): return None
    def get_last_quote(symbol=None): return None

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


class PerformanceMetrics(BaseModel):
    """Dashboard overview metrics (stub for Neon/backtester)."""
    pnl_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    hit_rate: float
    e_ratio: float
    active_strategies: int
    total_strategies: int
    delta_sharpe: float | None = None
    delta_sortino: float | None = None
    delta_dd: float | None = None


class ActivityEntry(BaseModel):
    timestamp: str
    event: str
    status: str  # e.g. "OK", "Warning", "Error"


class AccountSummary(BaseModel):
    """Alpaca account summary (when ALPACA_API_KEY set)."""
    equity: Optional[float] = None
    cash: Optional[float] = None
    buying_power: Optional[float] = None
    drawdown_pct: Optional[float] = None
    source: str = "alpaca"  # "alpaca" | "mock"


class PositionSummary(BaseModel):
    """Single open position."""
    symbol: str
    qty: float
    side: str
    market_value: float
    unrealized_pl: float
    entry_price: Optional[float] = None
    current_price: Optional[float] = None


class QuoteSummary(BaseModel):
    """Latest quote for live ticker."""
    symbol: str
    bid: float
    ask: float
    mid: Optional[float] = None
    timestamp: Optional[str] = None



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


def _mock_performance_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        pnl_pct=round(random.uniform(-5, 15), 1),
        sharpe=round(random.uniform(0.5, 2.5), 2),
        sortino=round(random.uniform(0.8, 2.2), 2),
        max_drawdown_pct=round(random.uniform(3, 18), 1),
        hit_rate=round(random.uniform(0.45, 0.70), 2),
        e_ratio=round(random.uniform(1.0, 2.2), 2),
        active_strategies=random.randint(5, 9),
        total_strategies=10,
        delta_sharpe=round(random.uniform(-0.2, 0.3), 2),
        delta_sortino=round(random.uniform(-0.1, 0.2), 2),
        delta_dd=round(random.uniform(-1, 1), 1),
    )


def _mock_activity(limit: int = 10) -> List[ActivityEntry]:
    events = [
        ("Strategy RSI_H1 validated", "OK"),
        ("Alpha decay in Breakout_D1: Sharpe dropped 20%", "Warning"),
        ("New plan: RESEARCH_PLAN_MeanReversion.md", "OK"),
        ("Monte Carlo run completed", "OK"),
        ("Strategy moved to production", "OK"),
    ]
    result = []
    for i in range(min(limit, len(events))):
        ts = datetime.utcnow() - timedelta(hours=i)
        ev, status = events[i % len(events)]
        result.append(ActivityEntry(
            timestamp=ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            event=ev,
            status=status,
        ))
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
    """Return current portfolio risk metrics. Uses Alpaca positions for exposure when available."""
    if is_alpaca_available():
        pos_list = get_positions()
        if pos_list is not None:
            total_mv = sum(p.get("market_value") or 0 for p in pos_list)
            exposure = {}
            for p in pos_list:
                sym = p.get("symbol", "?")
                mv = p.get("market_value") or 0
                if total_mv and total_mv > 0:
                    exposure[sym] = round(mv / total_mv * 100, 1)
            if not exposure:
                exposure = {"Cash": 100.0}
            return RiskMetrics(
                portfolio_var=2.0,
                current_drawdown=0.0,
                max_drawdown_limit=10.0,
                exposure=exposure,
            )
    return _mock_risk()


@app.get("/metrics", response_model=PerformanceMetrics, tags=["Dashboard"])
def get_performance_metrics():
    """Return aggregate performance metrics. Uses Alpaca account/portfolio when ALPACA_API_KEY set."""
    if is_alpaca_available():
        acc = get_account()
        hist = get_portfolio_history(30)
        if acc and acc.get("equity"):
            eq = float(acc["equity"])
            pnl_pct = None
            if hist and len(hist) >= 2:
                first_eq = hist[0].get("equity") or hist[0].get("pnl_pct")
                if first_eq is not None:
                    try:
                        first = float(first_eq)
                        if first and first != 0:
                            pnl_pct = (eq / first - 1.0) * 100
                    except (TypeError, ValueError):
                        pass
                if pnl_pct is None and hist:
                    pnl_pct = hist[-1].get("pnl_pct")
            return PerformanceMetrics(
                pnl_pct=pnl_pct or 0.0,
                sharpe=1.2,
                sortino=1.5,
                max_drawdown_pct=5.0,
                hit_rate=0.55,
                e_ratio=1.5,
                active_strategies=len(get_positions()),
                total_strategies=10,
                delta_sharpe=None,
                delta_sortino=None,
                delta_dd=None,
            )
    return _mock_performance_metrics()


@app.get("/activity", response_model=List[ActivityEntry], tags=["Dashboard"])
def get_activity(limit: int = 20):
    """Return recent activity log for Dashboard (stub; wire to agents/watchers)."""
    return _mock_activity(limit=limit)


@app.get("/account", response_model=AccountSummary, tags=["Alpaca"])
def get_account_summary():
    """Return Alpaca account summary when ALPACA_API_KEY is set."""
    if not is_alpaca_available():
        return AccountSummary(source="mock")
    acc = get_account()
    if not acc:
        return AccountSummary(source="mock")
    return AccountSummary(
        equity=acc.get("equity"),
        cash=acc.get("cash"),
        buying_power=acc.get("buying_power"),
        drawdown_pct=acc.get("drawdown_pct"),
        source="alpaca",
    )


@app.get("/positions", response_model=List[PositionSummary], tags=["Alpaca"])
def get_open_positions():
    """Return open positions from Alpaca when ALPACA_API_KEY is set."""
    if not is_alpaca_available():
        return []
    pos_list = get_positions()
    return [
        PositionSummary(
            symbol=p["symbol"],
            qty=p["qty"],
            side=p["side"],
            market_value=p["market_value"],
            unrealized_pl=p["unrealized_pl"],
            entry_price=p.get("entry_price"),
            current_price=p.get("current_price"),
        )
        for p in pos_list
    ]


@app.get("/portfolio/history", tags=["Alpaca"])
def get_portfolio_history_route(days: int = 30):
    """Return portfolio equity/history for P&L curve (Alpaca symbol bars when keys set)."""
    if not is_alpaca_available():
        return {"history": [], "source": "mock"}
    hist = get_portfolio_history(days=min(days, 365))
    if not hist:
        return {"history": [], "source": "alpaca"}
    return {"history": hist, "source": "alpaca"}


@app.get("/quote", response_model=QuoteSummary, tags=["Alpaca"])
def get_latest_quote(symbol: Optional[str] = None):
    """Return latest quote for symbol (live ticker). Uses ALPACA_TICKER_SYMBOL env if symbol omitted."""
    if not is_alpaca_available():
        return QuoteSummary(symbol=symbol or "SPY", bid=0, ask=0)
    q = get_last_quote(symbol)
    if not q:
        return QuoteSummary(symbol=symbol or "SPY", bid=0, ask=0)
    ts = q.get("timestamp")
    return QuoteSummary(
        symbol=q.get("symbol", "?"),
        bid=q.get("bid", 0),
        ask=q.get("ask", 0),
        mid=q.get("mid"),
        timestamp=str(ts) if ts else None,
    )


@app.get("/alpaca/status", tags=["Alpaca"])
def alpaca_status():
    """Return whether Alpaca is connected (for UI indicator)."""
    return {"connected": is_alpaca_available()}
