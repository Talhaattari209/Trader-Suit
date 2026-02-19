"""
US Session 09:30 strategy logic (reusable for backtest and tests).
- Filter for 09:30 EST.
- Buy on close of bullish candle: Close > Open and (Close - Open) > 0.5 * (High - Low).
- Sell on close of bearish candle: Open > Close and (Open - Close) > 0.5 * (High - Low).
- Reversal logic.
"""
from pathlib import Path
import pandas as pd

from ..data.us30_loader import US30Loader


def _to_est(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure index is timezone-aware US/Eastern."""
    if df.index.tz is None:
        df = df.copy()
        df.index = df.index.tz_localize("UTC", ambiguous="infer")
    df = df.tz_convert("America/New_York")
    return df


def filter_us_session_open(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only candles at 09:30 US Eastern (US session open)."""
    df = _to_est(df)
    mask = (df.index.hour == 9) & (df.index.minute == 30)
    return df.loc[mask].copy()


def buy_signal(row: pd.Series) -> bool:
    """Close > Open AND (Close - Open) > 0.5 * (High - Low)."""
    o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
    if c <= o:
        return False
    body = c - o
    range_ = h - l
    if range_ <= 0:
        return False
    return body > 0.5 * range_


def sell_signal(row: pd.Series) -> bool:
    """Open > Close AND (Open - Close) > 0.5 * (High - Low)."""
    o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
    if o <= c:
        return False
    body = o - c
    range_ = h - l
    if range_ <= 0:
        return False
    return body > 0.5 * range_


def run_backtest(csv_path: str, initial_capital: float = 100_000.0) -> dict:
    """
    Reversal logic: position in {-1, 0, 1}. Start flat (0).
    On buy signal: if short or flat -> go long at close (close short first if needed).
    On sell signal: if long or flat -> go short at close (close long first if needed).
    """
    loader = US30Loader(csv_path)
    df = loader.load_clean_data()
    df = filter_us_session_open(df)

    if df.empty:
        return {"cumulative_return": 0.0, "trades": 0, "bars": 0, "message": "No 09:30 EST bars found."}

    position = 0
    entry_price = None
    equity = initial_capital
    trades = []

    for ts, row in df.iterrows():
        close = row["Close"]
        if buy_signal(row):
            if position == -1:
                pnl_pct = (entry_price - close) / entry_price
                equity *= 1 + pnl_pct
                trades.append({"time": ts, "action": "close_short", "price": close, "pnl_pct": pnl_pct})
            if position != 1:
                position = 1
                entry_price = close
        elif sell_signal(row):
            if position == 1:
                pnl_pct = (close - entry_price) / entry_price
                equity *= 1 + pnl_pct
                trades.append({"time": ts, "action": "close_long", "price": close, "pnl_pct": pnl_pct})
            if position != -1:
                position = -1
                entry_price = close

    if position == 1 and entry_price is not None:
        last_close = df["Close"].iloc[-1]
        pnl_pct = (last_close - entry_price) / entry_price
        equity *= 1 + pnl_pct
        trades.append({"time": df.index[-1], "action": "flat_long", "price": last_close, "pnl_pct": pnl_pct})
    elif position == -1 and entry_price is not None:
        last_close = df["Close"].iloc[-1]
        pnl_pct = (entry_price - last_close) / entry_price
        equity *= 1 + pnl_pct
        trades.append({"time": df.index[-1], "action": "flat_short", "price": last_close, "pnl_pct": pnl_pct})

    cumulative_return = (equity / initial_capital) - 1.0
    return {
        "cumulative_return": cumulative_return,
        "equity": equity,
        "initial_capital": initial_capital,
        "trades": len(trades),
        "bars": len(df),
        "trade_log": trades,
    }


def run_backtest_on_dataframe(df: pd.DataFrame, initial_capital: float = 100_000.0) -> dict:
    """
    Same as run_backtest but on an already-loaded DataFrame with 09:30 bars
    (must have Open, High, Low, Close and datetime index).
    """
    if df.empty:
        return {"cumulative_return": 0.0, "trades": 0, "bars": 0, "message": "No bars."}

    position = 0
    entry_price = None
    equity = initial_capital
    trades = []

    for ts, row in df.iterrows():
        close = row["Close"]
        if buy_signal(row):
            if position == -1:
                pnl_pct = (entry_price - close) / entry_price
                equity *= 1 + pnl_pct
                trades.append({"time": ts, "action": "close_short", "price": close, "pnl_pct": pnl_pct})
            if position != 1:
                position = 1
                entry_price = close
        elif sell_signal(row):
            if position == 1:
                pnl_pct = (close - entry_price) / entry_price
                equity *= 1 + pnl_pct
                trades.append({"time": ts, "action": "close_long", "price": close, "pnl_pct": pnl_pct})
            if position != -1:
                position = -1
                entry_price = close

    if position == 1 and entry_price is not None:
        last_close = df["Close"].iloc[-1]
        pnl_pct = (last_close - entry_price) / entry_price
        equity *= 1 + pnl_pct
        trades.append({"time": df.index[-1], "action": "flat_long", "price": last_close, "pnl_pct": pnl_pct})
    elif position == -1 and entry_price is not None:
        last_close = df["Close"].iloc[-1]
        pnl_pct = (entry_price - last_close) / entry_price
        equity *= 1 + pnl_pct
        trades.append({"time": df.index[-1], "action": "flat_short", "price": last_close, "pnl_pct": pnl_pct})

    cumulative_return = (equity / initial_capital) - 1.0
    return {
        "cumulative_return": cumulative_return,
        "equity": equity,
        "initial_capital": initial_capital,
        "trades": len(trades),
        "bars": len(df),
        "trade_log": trades,
    }
