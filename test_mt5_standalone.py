
import MetaTrader5 as mt5
import sys

def test_mt5_connection():
    print(f"MetaTrader5 package author: {mt5.__author__}")
    print(f"MetaTrader5 package version: {mt5.__version__}")

    # Establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print(f"initialize() failed, error code = {mt5.last_error()}")
        sys.exit(1)
    
    print("MetaTrader5 initialized successfully")
    print("-" * 30)

    # Get account info
    account_info = mt5.account_info()
    if account_info is None:
        print(f"Failed to get account info, error code = {mt5.last_error()}")
    else:
        print(f"Account: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Balance: {account_info.balance}")
        print(f"Equity: {account_info.equity}")
        print(f"Leverage: {account_info.leverage}")
        print(f"Profit: {account_info.profit}")

    # Shutdown connection
    mt5.shutdown()
    print("-" * 30)
    print("Connection closed")

if __name__ == "__main__":
    test_mt5_connection()
