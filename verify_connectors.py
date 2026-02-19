"""
Verification script for API Connectors.
Run this to test connection, data fetching, and optional order execution.

Usage:
    python verify_connectors.py [--broker alpaca|mt5] [--symbol US30] [--order]

Default broker is read from .env (BROKER_TYPE).
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.connectors.connector_factory import get_connector
from src.connectors.exceptions import ConnectorError
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Verify API Connectors")
    parser.add_argument("--broker", help="Broker to test (alpaca or mt5)", default=None)
    parser.add_argument("--symbol", help="Symbol to fetch/trade", default="US30")
    parser.add_argument("--order", action="store_true", help="Place a small test market order (PAPER TRADING ONLY!)")
    args = parser.parse_args()

    # 1. Initialize Connector
    print(f"--- Initializing Connector ({args.broker or os.environ.get('BROKER_TYPE', 'default')}) ---")
    try:
        if args.broker:
            # Override env for this run
            os.environ["BROKER_TYPE"] = args.broker
        
        connector = get_connector()
        print(f"Connector class: {connector.__class__.__name__}")
        
    except ConnectorError as e:
        print(f"[ERROR] Failed to initialize connector: {e}")
        return
    except Exception as e:
        print(f"[ERROR] Unexpected error during initialization: {e}")
        return

    # 2. Connect
    print("\n--- Connecting ---")
    try:
        connector.connect()
        print("Successfully connected.")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # 3. Fetch Account State
    print("\n--- Account State ---")
    try:
        state = connector.get_account_state()
        print(f"Balance: {state.get('balance')}")
        print(f"Equity:  {state.get('equity')}")
        print(f"Buying Power: {state.get('buying_power', 'N/A')}")
        if state.get('drawdown'):
            print(f"Drawdown: {state.get('drawdown')}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch account state: {e}")

    # 4. Fetch Data (Perception)
    print(f"\n--- Fetching Data for {args.symbol} ---")
    try:
        df = connector.get_ohlcv(args.symbol, timeframe="1h", count=5)
        if df.empty:
            print("[WARNING] Dataframe is empty.")
        else:
            print("Successfully fetched 5 rows:")
            print(df)
            print("Columns:", df.columns.tolist())
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")

    # 5. Execution (Optional)
    if args.order:
        print(f"\n--- Placing Test Order for {args.symbol} ---")
        confirm = input(f"Are you sure you want to place a MARKET BUY order for 0.1 qty of {args.symbol}? (y/n): ")
        if confirm.lower() == 'y':
            try:
                # Small quantity for test
                qty = 0.1
                # Check risk first (internal check)
                if hasattr(connector, "_passes_risk_check"):
                    # Quick hack to check risk method if strictly internal or exposed
                     pass

                result = connector.execute_order(
                    symbol=args.symbol,
                    side="buy",
                    qty=qty,
                    order_type="market"
                )
                print("Order Result:", result)
            except Exception as e:
                print(f"[ERROR] Order execution failed: {e}")
        else:
            print("Order cancelled.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
