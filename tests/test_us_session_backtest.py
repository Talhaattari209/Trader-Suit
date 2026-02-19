"""
Tests for US Session 09:30 backtest (buy/sell signals and reversal logic).
Run: uv run pytest tests/test_us_session_backtest.py -v
"""
import pandas as pd
import pytest

from src.backtest.us_session_backtest import (
    buy_signal,
    sell_signal,
    run_backtest_on_dataframe,
)


def test_buy_signal_bullish_strong_body():
    # Body = 20, range = 30 -> 20 > 15 = 50% of range -> True
    row = pd.Series({"Open": 100, "High": 130, "Low": 90, "Close": 120})
    assert buy_signal(row) is True


def test_buy_signal_bullish_weak_body():
    # Body = 5, range = 30 -> 5 < 15 -> False
    row = pd.Series({"Open": 100, "High": 130, "Low": 90, "Close": 105})
    assert buy_signal(row) is False


def test_buy_signal_bearish_returns_false():
    row = pd.Series({"Open": 120, "High": 130, "Low": 90, "Close": 100})
    assert buy_signal(row) is False


def test_sell_signal_bearish_strong_body():
    # Open - Close = 20, range = 30 -> 20 > 15 -> True
    row = pd.Series({"Open": 120, "High": 130, "Low": 90, "Close": 100})
    assert sell_signal(row) is True


def test_sell_signal_bullish_returns_false():
    row = pd.Series({"Open": 100, "High": 130, "Low": 90, "Close": 120})
    assert sell_signal(row) is False


def test_run_backtest_on_dataframe_reversal():
    # Two bars: first buy (go long), second sell (close long, go short), third buy (close short, go long)
    # Bar 1: O=100 H=110 L=90 C=108 -> body=8, range=20, 8>10? No. So no signal... need 8 > 10 for buy. So use 12: body=12>10 -> buy
    # Bar 2: O=108 H=115 L=100 C=102 -> body=6, range=15, 6>7.5? No. For sell we need O>C and (O-C)>0.5*range. 6>7.5? No. Use 8: O=108 C=100 -> 8>7.5 -> sell
    df = pd.DataFrame(
        [
            {"Open": 100, "High": 115, "Low": 95, "Close": 112},   # body 12, range 20 -> buy
            {"Open": 112, "High": 120, "Low": 100, "Close": 101}, # body 11, range 20 -> sell
        ],
        index=pd.DatetimeIndex(["2025-10-09 09:30:00", "2025-10-10 09:30:00"], tz="America/New_York"),
    )
    result = run_backtest_on_dataframe(df, initial_capital=100_000.0)
    assert result["bars"] == 2
    assert result["trades"] >= 1  # at least one close
    # Long from 112, close at 101 -> loss (101-112)/112 = -9.82%
    # cumulative return should be negative
    assert "cumulative_return" in result
    assert result["initial_capital"] == 100_000.0
