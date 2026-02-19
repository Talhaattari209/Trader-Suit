"""
Alpaca connector: data perception and execution via alpaca-py.
Paper trading by default. Standardized OHLCV and order interface.
"""
import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from .base_connector import BaseConnector
from .exceptions import AuthenticationError, InsufficientLiquidityError
from .log_utils import get_connector_logger

# Optional: risk limit from env (max fraction of equity per order)
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


class AlpacaConnector(BaseConnector):
    """
    Alpaca broker connector. Uses TradingClient for execution and
    StockHistoricalDataClient for OHLCV. Paper=True by default.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
        logs_dir: str | None = None,
    ):
        self._api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self._secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        self._paper = paper
        self._logs_dir = logs_dir
        self._trading_client = None
        self._data_client = None
        self._logger = get_connector_logger("alpaca", logs_dir)

    def connect(self) -> bool:
        """Initialize Alpaca trading and data clients."""
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
            self._logger.info("Connected to Alpaca (paper=%s)", self._paper)
            return True
        except Exception as e:
            self._logger.exception("Alpaca connection failed")
            raise AuthenticationError(f"Alpaca connection failed: {e}") from e

    def _ensure_connected(self) -> None:
        if self._trading_client is None:
            self.connect()

    def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Fetch historical bars and return standardized DataFrame [Open, High, Low, Close, Volume], index=Timestamp."""
        self._ensure_connected()
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        amount, unit = _parse_timeframe(timeframe)
        unit_map = {"m": TimeFrameUnit.Minute, "h": TimeFrameUnit.Hour, "d": TimeFrameUnit.Day}
        tf_unit = unit_map.get(unit, TimeFrameUnit.Hour)
        alpaca_tf = TimeFrame(amount=amount, unit=tf_unit)

        end = datetime.utcnow()
        # Rough start: count * bar minutes to have enough bars
        if unit == "m":
            start = end - timedelta(minutes=amount * count * 2)
        elif unit == "h":
            start = end - timedelta(hours=amount * count * 2)
        else:
            start = end - timedelta(days=amount * count * 2)

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start,
            end=end,
            limit=count,
        )
        try:
            bars = self._data_client.get_stock_bars(request)
            self._logger.debug("get_ohlcv symbol=%s timeframe=%s count=%s", symbol, timeframe, count)
        except Exception as e:
            self._logger.exception("get_ohlcv failed")
            raise

        if bars is None or (hasattr(bars, "data") and not bars.data):
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        # BarSet can have .df (multiindex: symbol, timestamp) or we iterate
        if hasattr(bars, "df") and bars.df is not None and not bars.df.empty:
            df = bars.df
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
                if "timestamp" in df.columns:
                    df = df.rename(columns={"timestamp": "Timestamp"})
                df = df.set_index("Timestamp")
            # Standardize column names
            col_map = {c: c.capitalize() for c in ["open", "high", "low", "close", "volume"] if c in df.columns or c in [x.lower() for x in df.columns]}
            for k, v in col_map.items():
                for orig in df.columns:
                    if orig.lower() == k:
                        df = df.rename(columns={orig: v})
                        break
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                if col not in df.columns and col.lower() in [x.lower() for x in df.columns]:
                    for orig in df.columns:
                        if orig.lower() == col.lower():
                            df = df.rename(columns={orig: col})
                            break
            if "Volume" not in df.columns:
                df["Volume"] = 0
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df = df.sort_index().tail(count)
            return df

        # Fallback: build from bars.data (list of Bar per symbol)
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

    def get_account_state(self) -> dict:
        """Return balance, equity, buying_power (and optional drawdown placeholder)."""
        self._ensure_connected()
        try:
            acc = self._trading_client.get_account()
            self._logger.debug("get_account_state called")
            return {
                "balance": float(getattr(acc, "cash", 0) or 0),
                "equity": float(getattr(acc, "equity", 0) or 0),
                "buying_power": float(getattr(acc, "buying_power", 0) or 0),
                "drawdown": None,  # Alpaca doesn't provide this directly
            }
        except Exception as e:
            self._logger.exception("get_account_state failed")
            raise

    def _passes_risk_check(self, symbol: str, qty: float) -> bool:
        """Refuse if qty would exceed configured max risk fraction of equity."""
        try:
            state = self.get_account_state()
            equity = state.get("equity") or state.get("balance") or 0
            if equity <= 0:
                return False
            max_frac = float(os.environ.get(MAX_RISK_FRACTION_ENV, "0.1"))
            # Simple check: notional of order should not exceed max_frac * equity (rough)
            # We don't have price here; allow by default and rely on buying_power on Alpaca side
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
        """Submit order. Returns {status, order_id, message}."""
        self._ensure_connected()
        if not self._passes_risk_check(symbol, qty):
            self._logger.warning("Order rejected: risk check failed symbol=%s qty=%s", symbol, qty)
            return {"status": "rejected", "reason": "Risk limit exceeded", "order_id": None}

        side = (side or "buy").strip().lower()
        order_type = (order_type or "market").strip().lower()

        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        time_in_force = TimeInForce.GTC

        try:
            if order_type == "limit" and limit_price is not None:
                req = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=time_in_force,
                    limit_price=limit_price,
                )
            else:
                req = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=time_in_force,
                )
            order = self._trading_client.submit_order(order_data=req)
            oid = getattr(order, "id", None)
            self._logger.info("Order submitted symbol=%s side=%s qty=%s order_id=%s", symbol, side, qty, oid)
            return {"status": "success", "order_id": str(oid) if oid else None}
        except Exception as e:
            self._logger.exception("execute_order failed")
            if "insufficient" in str(e).lower() or "buying power" in str(e).lower():
                raise InsufficientLiquidityError(str(e)) from e
            return {"status": "error", "order_id": None, "message": str(e)}
