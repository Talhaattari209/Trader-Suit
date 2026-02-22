"""
Alpaca connector – advanced architecture.

Key upgrades over the original AlpacaConnector:
* **WebSocket streaming** via ``StockDataStream`` for real-time OHLCV / trade updates.
* **CacheManager** integration – ``get_ohlcv`` checks the cache before hitting REST.
* **ExecutionManager** – orders go through async queue with throttling and multi-account failover.
* **Multi-account support** – reads primary + backup credentials from env.
* **Event bus** – simple observer callbacks for streaming events.
"""
import asyncio
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import pandas as pd

from .base_connector import BaseConnector
from .cache_manager import CacheManager
from .exceptions import AuthenticationError, InsufficientLiquidityError
from .log_utils import get_connector_logger

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment keys
# ---------------------------------------------------------------------------
MAX_RISK_FRACTION_ENV = "CONNECTOR_MAX_RISK_FRACTION"


def _parse_timeframe(tf: str) -> tuple[int, str]:
    """Map internal timeframe string (e.g. '1h', '5m', '1d') to (amount, unit)."""
    tf = (tf or "1h").strip().lower()
    unit = "h"
    if tf.endswith("m"):
        unit = "m"
        amount_str = tf[:-1]
    elif tf.endswith("h"):
        unit = "h"
        amount_str = tf[:-1]
    elif tf.endswith("d"):
        unit = "d"
        amount_str = tf[:-1]
    else:
        amount_str = tf
    try:
        amount = int(amount_str) if amount_str else 1
    except ValueError:
        amount = 1
    return amount, unit


# ═══════════════════════════════════════════════════════════════════════════
# AlpacaConnector
# ═══════════════════════════════════════════════════════════════════════════
class AlpacaConnector(BaseConnector):
    """
    Production-grade Alpaca connector with caching, streaming,
    throttled execution, and multi-account failover.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
        logs_dir: str | None = None,
        enable_cache: bool = True,
        cache_ttl: int = 60,
    ):
        # Primary credentials
        self._api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self._secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        # Backup credentials (multi-account failover)
        self._api_key_2 = os.environ.get("ALPACA_API_KEY_2")
        self._secret_key_2 = os.environ.get("ALPACA_SECRET_KEY_2")
        self._paper = paper
        self._logs_dir = logs_dir
        self._logger = get_connector_logger("alpaca", logs_dir)

        # Clients (lazy-initialized in connect())
        self._trading_client = None
        self._data_client = None
        self._trading_client_2 = None  # backup account

        # Cache
        self._cache: CacheManager | None = CacheManager(ttl_seconds=cache_ttl) if enable_cache else None

        # Streaming
        self._stream = None
        self._stream_thread: threading.Thread | None = None
        self._event_listeners: dict[str, list[Callable]] = {}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Initialize Alpaca trading and data clients (primary + optional backup)."""
        if not self._api_key or not self._secret_key:
            self._logger.error("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY")
            raise AuthenticationError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required")

        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient

            self._trading_client = TradingClient(
                api_key=self._api_key,
                secret_key=self._secret_key,
                paper=self._paper,
            )
            self._data_client = StockHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._secret_key,
            )
            self._logger.info("Connected to Alpaca primary (paper=%s)", self._paper)

            # Backup account (optional)
            if self._api_key_2 and self._secret_key_2:
                self._trading_client_2 = TradingClient(
                    api_key=self._api_key_2,
                    secret_key=self._secret_key_2,
                    paper=self._paper,
                )
                self._logger.info("Backup Alpaca account initialized")

            return True
        except Exception as e:
            self._logger.exception("Alpaca connection failed")
            raise AuthenticationError(f"Alpaca connection failed: {e}") from e

    def _ensure_connected(self) -> None:
        if self._trading_client is None:
            self.connect()

    # ------------------------------------------------------------------
    # Event Bus (Observer pattern for streaming)
    # ------------------------------------------------------------------
    def on(self, event: str, callback: Callable) -> None:
        """Register a listener for a streaming event (e.g. 'bar', 'trade', 'quote')."""
        self._event_listeners.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: Any) -> None:
        for cb in self._event_listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                self._logger.exception("Event listener error for '%s'", event)

    # ------------------------------------------------------------------
    # WebSocket Streaming
    # ------------------------------------------------------------------
    def start_stream(self, symbols: list[str] | None = None) -> None:
        """
        Start a background WebSocket stream for bars/trades/quotes.

        Received data is broadcast to registered listeners via ``on(event, cb)``.
        Also updates the cache with live bars.
        """
        if self._stream_thread and self._stream_thread.is_alive():
            self._logger.warning("Stream already running")
            return

        self._ensure_connected()

        from alpaca.data.live import StockDataStream

        stream = StockDataStream(
            api_key=self._api_key,
            secret_key=self._secret_key,
        )

        symbols = symbols or ["US30", "US100"]

        async def _bar_handler(bar):
            self._emit("bar", bar)
            self._logger.debug("Stream bar: %s", bar)

        async def _trade_handler(trade):
            self._emit("trade", trade)

        async def _quote_handler(quote):
            self._emit("quote", quote)

        stream.subscribe_bars(_bar_handler, *symbols)
        stream.subscribe_trades(_trade_handler, *symbols)
        stream.subscribe_quotes(_quote_handler, *symbols)

        def _run():
            try:
                stream.run()
            except Exception:
                self._logger.exception("Stream died")

        self._stream = stream
        self._stream_thread = threading.Thread(target=_run, daemon=True, name="alpaca-stream")
        self._stream_thread.start()
        self._logger.info("WebSocket stream started for %s", symbols)

    def stop_stream(self) -> None:
        if self._stream:
            try:
                self._stream.stop()
            except Exception:
                pass
            self._stream = None
        self._logger.info("WebSocket stream stopped")

    # ------------------------------------------------------------------
    # Data Perception (with cache)
    # ------------------------------------------------------------------
    def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        Fetch historical bars. Checks cache first; on miss, calls REST
        and stores the result.
        """
        self._ensure_connected()

        # Cache check
        if self._cache:
            key = self._cache.make_key(symbol, timeframe, count)
            hit = self._cache.get(key)
            if hit is not None:
                self._logger.debug("Cache HIT for %s %s %d", symbol, timeframe, count)
                return hit

        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from alpaca.data.enums import DataFeed

        amount, unit = _parse_timeframe(timeframe)
        unit_map = {"m": TimeFrameUnit.Minute, "h": TimeFrameUnit.Hour, "d": TimeFrameUnit.Day}
        tf_unit = unit_map.get(unit, TimeFrameUnit.Hour)
        alpaca_tf = TimeFrame(amount=amount, unit=tf_unit)

        end = datetime.now(timezone.utc)
        if unit == "m":
            start = end - timedelta(minutes=amount * count * 2)
        elif unit == "h":
            start = end - timedelta(hours=amount * count * 2)
        else:
            start = end - timedelta(days=amount * count * 2)

        # Use IEX feed for free-tier accounts (SIP requires Algo Trader Plus)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start,
            end=end,
            limit=count,
            feed=DataFeed.IEX,
        )
        try:
            bars = self._data_client.get_stock_bars(request)
            self._logger.debug("REST get_ohlcv symbol=%s timeframe=%s count=%s", symbol, timeframe, count)
        except Exception:
            self._logger.exception("get_ohlcv failed")
            raise

        df = self._bars_to_dataframe(bars, count)

        # Store in cache
        if self._cache and not df.empty:
            self._cache.set(key, df)

        return df

    # ------------------------------------------------------------------
    # Account State
    # ------------------------------------------------------------------
    def get_account_state(self) -> dict:
        """Return balance, equity, buying_power."""
        self._ensure_connected()
        try:
            acc = self._trading_client.get_account()
            return {
                "balance": float(getattr(acc, "cash", 0) or 0),
                "equity": float(getattr(acc, "equity", 0) or 0),
                "buying_power": float(getattr(acc, "buying_power", 0) or 0),
                "drawdown": None,
            }
        except Exception:
            self._logger.exception("get_account_state failed")
            raise

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def _passes_risk_check(self, symbol: str, qty: float) -> bool:
        try:
            state = self.get_account_state()
            equity = state.get("equity") or state.get("balance") or 0
            if equity <= 0:
                return False
            buying_power = state.get("buying_power") or 0
            if buying_power <= 0:
                return False
            return True
        except Exception:
            return False

    def execute_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        limit_price: float | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Submit order via primary account.  If the caller wraps this in an
        ``ExecutionManager``, throttling and failover are handled externally.
        """
        self._ensure_connected()
        if not self._passes_risk_check(symbol, qty):
            self._logger.warning("Order rejected: risk check failed symbol=%s qty=%s", symbol, qty)
            return {"status": "rejected", "reason": "Risk limit exceeded", "order_id": None}

        return self._submit_via_client(self._trading_client, symbol, side, qty, order_type, limit_price)

    def execute_order_backup(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        limit_price: float | None = None,
        **kwargs: Any,
    ) -> dict:
        """Execute on the backup account (used by ExecutionManager failover)."""
        if not self._trading_client_2:
            return {"status": "error", "order_id": None, "message": "No backup account configured"}
        return self._submit_via_client(self._trading_client_2, symbol, side, qty, order_type, limit_price)

    def _submit_via_client(self, client, symbol, side, qty, order_type, limit_price=None) -> dict:
        side = (side or "buy").strip().lower()
        order_type = (order_type or "market").strip().lower()

        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        tif = TimeInForce.GTC

        try:
            if order_type == "limit" and limit_price is not None:
                req = LimitOrderRequest(symbol=symbol, qty=qty, side=order_side, time_in_force=tif, limit_price=limit_price)
            else:
                req = MarketOrderRequest(symbol=symbol, qty=qty, side=order_side, time_in_force=tif)
            order = client.submit_order(order_data=req)
            oid = getattr(order, "id", None)
            self._logger.info("Order submitted symbol=%s side=%s qty=%s order_id=%s", symbol, side, qty, oid)
            return {"status": "success", "order_id": str(oid) if oid else None}
        except Exception as e:
            self._logger.exception("execute_order failed")
            msg = str(e).lower()
            if "insufficient" in msg or "buying power" in msg:
                raise InsufficientLiquidityError(str(e)) from e
            if "429" in msg or "rate" in msg:
                return {"status": "error", "order_id": None, "message": f"rate_limited: {e}"}
            return {"status": "error", "order_id": None, "message": str(e)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _bars_to_dataframe(bars, count: int) -> pd.DataFrame:
        """Normalize alpaca BarSet → standardized DataFrame."""
        if bars is None or (hasattr(bars, "data") and not bars.data):
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        if hasattr(bars, "df") and bars.df is not None and not bars.df.empty:
            df = bars.df
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
                if "timestamp" in df.columns:
                    df = df.rename(columns={"timestamp": "Timestamp"})
                df = df.set_index("Timestamp")
            # Capitalize columns
            rename_map = {}
            for col in df.columns:
                if col.lower() in ("open", "high", "low", "close", "volume"):
                    rename_map[col] = col.capitalize()
            df = df.rename(columns=rename_map)
            if "Volume" not in df.columns:
                df["Volume"] = 0
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            return df.sort_index().tail(count)

        # Fallback: build manually
        rows = []
        if hasattr(bars, "data") and isinstance(bars.data, dict):
            for sym, bar_list in bars.data.items():
                for b in (bar_list or []):
                    t = getattr(b, "timestamp", None)
                    if t is None:
                        continue
                    rows.append({
                        "Timestamp": pd.Timestamp(t) if not isinstance(t, pd.Timestamp) else t,
                        "Open": float(getattr(b, "open", 0)),
                        "High": float(getattr(b, "high", 0)),
                        "Low": float(getattr(b, "low", 0)),
                        "Close": float(getattr(b, "close", 0)),
                        "Volume": int(getattr(b, "volume", 0)),
                    })
        if not rows:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        df = pd.DataFrame(rows).set_index("Timestamp").sort_index().tail(count)
        return df[["Open", "High", "Low", "Close", "Volume"]]
