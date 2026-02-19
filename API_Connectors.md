To ensure a 10-year modular lifecycle, these connectors must be built as "Pluggable Senses." They should not contain trading logic; their only job is to translate broker-specific APIs into a standardized internal format for your Actor and Critic agents.

Copy the following into a file named connector_specs.md and provide it to your coding agent.

Technical Specification: Financial Data & Execution Connectors
1. Objective
Establish a standardized interface for multi-broker connectivity. The system must support MetaTrader 5 (MT5) for legacy/prop firm integration and Alpaca for modern, API-first execution.

2. The Unified Connector Interface (src/connectors/base_connector.py)
All connectors must inherit from this base class to ensure the Actor Agent can swap brokers without code changes.

Python
from abc import ABC, abstractmethod
import pandas as pd

class BaseConnector(ABC):
    @abstractmethod
    def connect(self):
        """Initialize session and authenticate."""
        pass

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Fetch historical data in standardized OHLCV format."""
        pass

    @abstractmethod
    def execute_order(self, symbol: str, side: str, qty: float, order_type: str):
        """Standardized order execution (Market/Limit)."""
        pass

    @abstractmethod
    def get_account_state(self) -> dict:
        """Returns Balance, Equity, and Current Drawdown."""
        pass
3. MetaTrader 5 (MT5) Connector Logic
Library: MetaTrader5

WSL2 Note: MT5 is a Windows-native DLL. If running in WSL2, the connector must communicate via a lightweight REST Bridge or a Socket to a Windows-hosted MT5 terminal, or use Wine (high complexity).

Core Requirement: The agent must handle "Market Watch" synchronization and ensure the symbol (e.g., US30, DJI, or Indices\US30) is mapped correctly to internal IDs.

4. Alpaca Connector Logic
Library: alpaca-py

Data Stream: Implement TradingStream for real-time execution and StockDataStream (or CryptoDataStream) for live OHLCV perception.

Rate Limiting: Implementation must include an exponential backoff decorator for Alpaca’s REST API to prevent 429 errors during high-frequency Alpha research.

5. Implementation Plan for Coding Agent
Phase 1: Dependency Injection
Update requirements.txt with MetaTrader5 (for Windows environments) and alpaca-py.

Create src/connectors/connector_factory.py to initialize the correct broker based on .env settings.

Phase 2: The Data "Perception" Bridge
Implement get_ohlcv for both. Standardize the output to a Pandas DataFrame with columns: [Timestamp, Open, High, Low, Close, Volume].

Map MT5 timeframes (e.g., MT5_TIMEFRAME_H1) to a universal string format (e.g., "1h").

Phase 3: Order Execution & Safety
Implement Position Sizing Guardrails: The connector must refuse orders if the qty exceeds the risk-limit set in the Company_Handbook.md.

Implement Sync Check: A function that verifies if the local "Memory" (Neon DB) matches the actual Broker state to prevent "Ghost Trades."

6. 10-Year Maintenance Strategy
Logging: Every API request and response must be logged to logs/connector_[broker]_[date].log.

Error Handling: Implement custom exceptions: BrokerConnectionError, InsufficientLiquidityError, and AuthenticationError.

Versioning: Documentation must track API versioning (e.g., Alpaca v2) to ensure easy upgrades when brokers update their SDKs.

Next Step for Execution
Run the following in your terminal:

**"I have the connector_specs.md. Please:

Implement the BaseConnector abstract class.

Create the AlpacaConnector using the alpaca-py library.

Create a placeholder MT5Connector that logs a warning if run on Linux (WSL2), suggesting a Windows Bridge.

Ensure the US30Loader from Phase 2 can now accept data directly from these connectors instead of just CSVs."

-----------------------------

The Zero-MQL approach is a paradigm shift in algorithmic trading where the MetaTrader 5 (MT5) terminal is treated strictly as a headless execution gateway. Instead of writing complex Expert Advisors (EAs) in the C++ based MQL5 language, all intelligence, data processing, and order logic reside in Python.

1. The Zero-MQL Architecture
In a Zero-MQL setup, you do not compile .mq5 files. Instead, the MetaTrader5 Python Library communicates with the terminal through a background inter-process communication (IPC) layer.

Logic Layer (Python): Handles RL/DL models, Monte Carlo simulations, and strategy decisions.

Communication Layer: The official MetaTrader5 module acts as the bridge.

Execution Layer (MT5 Terminal): Receives raw trade requests and broadcasts market data.

2. Implementation Steps
A. Environment Setup
The official library is Windows-only. For a WSL2 or Linux-based project, you must implement a REST or Socket Bridge. This involves a small Python script running on the Windows host that "listens" for commands from your Linux environment.

B. The Core Implementation Logic
The implementation follows a four-step lifecycle:

Initialization: Establish a persistent link to the terminal.

Perception (Data Pull): Request OHLCV or Tick data as Pandas DataFrames.

Action (Execution): Send a structured dictionary (JSON-like) containing order parameters.

Shutdown: Gracefully disconnect to free up terminal resources.

C. Zero-MQL Trade Request Template
Instead of using MQL5's OrderSend() function, you use a Python dictionary. This is the heart of the "Zero-MQL" execution:

Python
import MetaTrader5 as mt5

# Define the trade request
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "US30",
    "volume": 0.1,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("US30").ask,
    "sl": 34000.0,
    "tp": 35000.0,
    "magic": 123456,
    "comment": "Digital FTE Execution",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

# Send the order
result = mt5.order_send(request)
3. Verification: The Zero-MQL "Check"
To confirm your implementation is truly Zero-MQL, verify the following:

No Active EA: The "Expert Advisors" section of your MT5 navigator should be empty. No script should be attached to the chart.

Terminal Settings: Under Tools > Options > Expert Advisors, "Allow Algorithmic Trading" must be checked, even though you aren't using an EA.

Synchronous State: The Python library must handle the Trade Result (retrying if the broker returns a "Requote" or "Invalid Price") since there is no MQL5 script to catch these errors.

Key Constraints for the 10-Year Lifecycle
Latency: Zero-MQL is not suitable for High-Frequency Trading (HFT) due to the communication overhead between Python and the MT5 terminal. It is ideal for Intraday and Swing strategies.

Terminal Dependency: The MT5 terminal must be open and logged in on a Windows environment. If the terminal closes, the Python connector will lose its "Senses."

-------------------------------
The Alpaca Execution Blueprint
The execution logic resides in src/connectors/alpaca_connector.py. It transforms the Actor Agent's conviction into a formatted API request.

Standardization: All orders use the Market or Limit type with Immediate-or-Cancel (IOC) or Good-til-Canceled (GTC) parameters.

Asynchronous Handling: Using asyncio ensures that order injection doesn't block the perception of incoming US30 data.

2. Implementation: AlpacaConnector.execute_order
This logic uses the official alpaca-py SDK to communicate with the brokerage.

Python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os

class AlpacaConnector:
    def __init__(self):
        self.client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=True # Default to paper trading for safety
        )

    async def execute_order(self, symbol: str, qty: float, side: str, order_type="market", price=None):
        # 1. Safety Check (The Guardian Agent)
        if not self._passes_risk_check(symbol, qty):
            return {"status": "rejected", "reason": "Risk limit exceeded"}

        # 2. Build Request
        if order_type == "market":
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
        
        # 3. Inject Order
        try:
            order = self.client.submit_order(order_data=req)
            return {"status": "success", "order_id": order.id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _passes_risk_check(self, symbol, qty):
        # Implement logic to check Company_Handbook.md or current account drawdown
        return True 
3. The "HITL" Order Gate
To maintain the Digital FTE safety standards, the agent should never execute a trade autonomously without an explicit signal.

Drafting: The Actor writes a PENDING_ORDER_[ID].md file to Obsidian_Vault/Needs_Action.

Review: You review the trade rationale in Obsidian.

Approval: Moving that file to the /Approved folder triggers a Watcher script that calls execute_order.

4. Step-by-Step Order Injection Plan
Step 1: Configuration. Add your Alpaca keys to the .env file. Ensure paper=True is set in the client initialization to prevent accidental real-money losses.

Step 2: Syncing. Implement the get_account_state method to verify current Buying Power before sizing the order.

Step 3: Logging. Every injected order must be logged to the Neon DB alpha_history table to track execution quality and slippage (the Critic's job).