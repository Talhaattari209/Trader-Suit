"""
US Session 09:30 backtest — no Docker.

Run with UV (recommended):
  uv sync
  uv run python run_us_session_backtest.py

Or with system Python (after pip install -r requirements.txt):
  python run_us_session_backtest.py

Strategy:
- Load CSV data.
- Filter for US Session start (09:30 EST).
- Buy on close of bullish candle where Close > Open and (Close - Open) > 0.5 * (High - Low).
- Sell on close of bearish candle where Open > Close and (Open - Close) > 0.5 * (High - Low).
- Reversal logic: each signal flips position (long <-> short).
- Print cumulative return.
"""
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.backtest.us_session_backtest import run_backtest


def main():
    csv_path = os.environ.get(
        "US30_CSV_PATH",
        str(Path(__file__).resolve().parent / "Dataset-Testing-US30" / "usa30idxusd-m5-bid-2025-10-09-2025-11-29.csv"),
    )
    if not Path(csv_path).exists():
        print(f"CSV not found: {csv_path}")
        print("Set US30_CSV_PATH or place CSV in Dataset-Testing-US30/.")
        sys.exit(1)

    result = run_backtest(csv_path)
    print("US Session 09:30 backtest (bullish close > 50% body = buy, bearish close < 50% body = sell, reversal)")
    print(f"  CSV: {csv_path}")
    print(f"  09:30 EST bars: {result['bars']}")
    print(f"  Trades: {result['trades']}")
    print(f"  Initial capital: {result['initial_capital']:,.2f}")
    print(f"  Final equity: {result.get('equity', 0):,.2f}")
    print(f"  Cumulative return: {result['cumulative_return']:.4%}")
    if result.get("message"):
        print(f"  Note: {result['message']}")
    return result


if __name__ == "__main__":
    main()
