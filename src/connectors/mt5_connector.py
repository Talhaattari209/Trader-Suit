"""
MetaTrader 5 connector (Zero-MQL): headless execution gateway.
Windows-only: MT5 is a native Windows DLL. On WSL2/Linux, connect() fails gracefully
with instructions to use a Windows-hosted REST/Socket bridge for future use.
"""
import sys
from typing import Any

import pandas as pd

from .base_connector import BaseConnector
from .exceptions import BrokerConnectionError
from .log_utils import get_connector_logger

WSL_BRIDGE_MSG = (
    "MT5 is Windows-native and cannot run inside WSL2/Linux. "
    "For future use: run a lightweight REST or Socket bridge on the Windows host "
    "that connects to the MT5 terminal, and use that bridge from this codebase."
)


def _is_windows() -> bool:
    return sys.platform == "win32"


def _get_mt5():
    """Lazy import of MetaTrader5 so that on Linux the module can still load."""
    import MetaTrader5 as mt5

    return mt5


# Map internal timeframe strings to MT5 constants
_TIMEFRAME_MAP = {
    "1m": None,  # set in code via _get_mt5().TIMEFRAME_M1
    "5m": None,
    "15m": None,
    "30m": None,
    "1h": None,
    "2h": None,
    "4h": None,
    "1d": None,
    "1w": None,
}


def _mt5_timeframe(tf: str):
    tf = (tf or "1h").strip().lower()
    mt5 = _get_mt5()
    mapping = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
        "2h": mt5.TIMEFRAME_H2,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
        "1w": mt5.TIMEFRAME_W1,
    }
    return mapping.get(tf, mt5.TIMEFRAME_H1)


class MT5Connector(BaseConnector):
    """
    MT5 connector: data via copy_rates_from_pos, execution via order_send.
    Zero-MQL: no Expert Advisors; terminal must have "Allow Algorithmic Trading" enabled.
    On non-Windows (WSL2/Linux), connect() raises BrokerConnectionError with bridge instructions.
    """

    def __init__(self, path: str | None = None, logs_dir: str | None = None):
        """
        path: optional path to MT5 terminal executable (for initialize(path=...)).
        logs_dir: optional directory for connector log file.
        """
        self._path = path
        self._logs_dir = logs_dir
        self._logger = get_connector_logger("mt5", logs_dir)
        self._connected = False

    def connect(self) -> bool:
        """Initialize connection to MT5 terminal. On WSL/Linux, fail with clear message."""
        if not _is_windows():
            self._logger.warning(WSL_BRIDGE_MSG)
            raise BrokerConnectionError(WSL_BRIDGE_MSG)

        mt5 = _get_mt5()
        if self._path:
            ok = mt5.initialize(self._path)
        else:
            ok = mt5.initialize()
        if not ok:
            err = mt5.last_error()
            self._logger.error("MT5 initialize failed: %s", err)
            raise BrokerConnectionError(f"MT5 initialize failed: {err}")
        self._connected = True
        self._logger.info("MT5 connected (Allow Algorithmic Trading must be enabled in terminal)")
        return True

    def _ensure_connected(self) -> None:
        if not self._connected:
            self.connect()

    def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Fetch bars from MT5 and return standardized DataFrame."""
        self._ensure_connected()
        mt5 = _get_mt5()
        tf = _mt5_timeframe(timeframe)
        # start_pos=0 is current bar, count bars into the past
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            err = mt5.last_error()
            self._logger.warning("copy_rates_from_pos failed: %s", err)
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        if hasattr(rates, "__len__") and len(rates) == 0:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        # numpy structured array: time, open, high, low, close, tick_volume, spread, real_volume
        df = pd.DataFrame(
            {
                "Timestamp": pd.to_datetime(rates["time"], unit="s"),
                "Open": rates["open"],
                "High": rates["high"],
                "Low": rates["low"],
                "Close": rates["close"],
                "Volume": rates["tick_volume"] if "tick_volume" in rates.dtype.names else (rates["real_volume"] if "real_volume" in rates.dtype.names else 0),
            }
        )
        df.set_index("Timestamp", inplace=True)
        df = df.sort_index()
        self._logger.debug("get_ohlcv symbol=%s timeframe=%s count=%s bars=%s", symbol, timeframe, count, len(df))
        return df

    def get_account_state(self) -> dict:
        """Return balance, equity, margin from MT5 account_info()."""
        self._ensure_connected()
        mt5 = _get_mt5()
        acc = mt5.account_info()
        if acc is None:
            err = mt5.last_error()
            self._logger.error("account_info failed: %s", err)
            raise BrokerConnectionError(f"MT5 account_info failed: {err}")
        balance = getattr(acc, "balance", 0) or 0
        equity = getattr(acc, "equity", 0) or 0
        margin = getattr(acc, "margin", 0) or 0
        return {
            "balance": float(balance),
            "equity": float(equity),
            "margin": float(margin),
            "drawdown": float(equity - balance) if (equity < balance) else None,
        }

    def execute_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        sl: float | None = None,
        tp: float | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Send order via mt5.order_send. Uses TRADE_ACTION_DEAL for market.
        volume in MT5 is in lots; qty here is passed as volume (caller can convert if needed).
        """
        self._ensure_connected()
        mt5 = _get_mt5()
        side = (side or "buy").strip().lower()
        order_type = (order_type or "market").strip().lower()

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            err = mt5.last_error()
            self._logger.error("symbol_info_tick failed: %s", err)
            return {"status": "error", "order_id": None, "message": f"Symbol {symbol} not available: {err}"}

        price = float(tick.ask) if side == "buy" else float(tick.bid)
        mt5_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": round(qty, 2),
            "type": mt5_type,
            "price": price,
            "magic": kwargs.get("magic", 0),
            "comment": kwargs.get("comment", "Digital FTE"),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if sl is not None:
            request["sl"] = float(sl)
        if tp is not None:
            request["tp"] = float(tp)

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            self._logger.error("order_send failed: %s", err)
            return {"status": "error", "order_id": None, "message": str(err)}

        retcode = getattr(result, "retcode", None)
        if retcode is not None and retcode != mt5.TRADE_RETCODE_DONE:
            self._logger.warning("order_send retcode=%s comment=%s", retcode, getattr(result, "comment", ""))
            return {
                "status": "error",
                "order_id": getattr(result, "order", None),
                "message": f"retcode={retcode}",
            }
        order_id = getattr(result, "order", None)
        self._logger.info("Order sent symbol=%s side=%s volume=%s order=%s", symbol, side, qty, order_id)
        return {"status": "success", "order_id": str(order_id) if order_id is not None else None}
