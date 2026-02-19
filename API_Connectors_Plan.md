# implementation Plan: API Connectors ("Pluggable Senses")

This document outlines the step-by-step plan to implement the "Pluggable Senses" architecture for financial data and execution, as defined in `API_Connectors.md`.

## 1. Overview
Object: Establish a standardized interface for multi-broker connectivity (MetaTrader 5 & Alpaca). Connectors will translate broker-specific APIs into a standardized internal format for Actor and Critic agents.

**Key Principles:**
- **Zero-MQL**: All logic resides in Python; MT5 is a headless execution gateway.
- **Unified Interface**: All connectors inherit from `BaseConnector`.
- **Safety First**: Risk checks and sync verification before execution.

---

## Phase 1: Foundation & Dependencies

### 1.1 Dependency Management
- [ ] Update `requirements.txt` to include:
    - `MetaTrader5` (Windows environments only checklist/warning)
    - `alpaca-py`
    - `pandas` (if not already present)

### 1.2 Base Connector Interface
- [ ] Create directory: `src/connectors/`
- [ ] Create `src/connectors/__init__.py`
- [ ] Create `src/connectors/base_connector.py`:
    - Define abstract base class `BaseConnector(ABC)`.
    - Define abstract methods:
        - `connect(self)`
        - `get_ohlcv(self, symbol, timeframe, count) -> pd.DataFrame`
        - `execute_order(self, symbol, side, qty, order_type)`
        - `get_account_state(self) -> dict`

### 1.3 Connector Factory
- [ ] Create `src/connectors/connector_factory.py`:
    - Implement factory pattern to initialize the correct connector based on environment variables (e.g., `BROKER_TYPE`).
    - Handle conditional logic for OS-specific imports (MT5 on Windows vs Linux/WSL).

---

## Phase 2: Alpaca Connector Implementation

### 2.1 Alpaca Connector Setup
- [ ] Create `src/connectors/alpaca_connector.py`.
- [ ] Implement `__init__`:
    - Load API Key and Secret from environment variables (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`).
    - Initialize `TradingClient` (set `paper=True` by default).

### 2.2 Data Perception (Alpaca)
- [ ] Implement `get_ohlcv`:
    - Use `StockHistoricalDataClient` or equivalent.
    - Fetch historical bars.
    - Convert to standardized Pandas DataFrame: `[Timestamp, Open, High, Low, Close, Volume]`.

### 2.3 Execution & Safety (Alpaca)
- [ ] Implement `get_account_state`:
    - Fetch account balance, equity, and buying power.
- [ ] Implement `_passes_risk_check(symbol, qty)`:
    - Basic check against max risk/drawdown limits.
- [ ] Implement `execute_order`:
    - Perform risk check.
    - Map internal order types (Market/Limit) to Alpaca `OrderRequest` objects.
    - Submit order and return standard response (`status`, `order_id`).

---

## Phase 3: MetaTrader 5 (MT5) Connector Implementation

### 3.1 MT5 Connector Layout
- [ ] Create `src/connectors/mt5_connector.py`.
- [ ] Implement `__init__`:
    - Initialize connection to MT5 terminal (`mt5.initialize()`).
    - Handle connection errors.

### 3.2 "Zero-MQL" Data Perception
- [ ] Implement `get_ohlcv`:
    - Use `mt5.copy_rates_from_pos`.
    - Map internal timeframes (e.g., "1h") to MT5 constants (e.g., `mt5.TIMEFRAME_H1`).
    - Convert result to standardized Pandas DataFrame.

### 3.3 "Zero-MQL" Execution
- [ ] Implement `get_account_state`:
    - Use `mt5.account_info()` to get balance, equity, margin.
- [ ] Implement `execute_order`:
    - Construct trade request dictionary (action, symbol, volume, type, price, etc.).
    - Use `mt5.order_send(request)`.
    - Check `result.retcode` for success/failure.
    - **Critical**: Ensure "Allow Algorithmic Trading" is enabled in MT5 terminal.

---

## Phase 4: Integration & Validation

### 4.1 US30Loader / Data Ingestion Update
- [ ] Update data ingestion pipelines (`src/watchers/data_ingestion_watcher.py` or similar) to use `ConnectorFactory` instead of direct CSV loading where applicable.

### 4.2 Logging & Monitoring
- [ ] Ensure all connectors log actions to `logs/connector_[broker]_[date].log`.
- [ ] Implement custom exceptions: `BrokerConnectionError`, `InsufficientLiquidityError`, `AuthenticationError`.

### 4.3 Verification Steps
- [ ] **Alpaca Test**: Run a script to fetch NASDAQ(US100) cfd/Dow Jones (US30) cfd data and place a small paper trade.
- [ ] **MT5 Test (Windows)**: Verify connection to terminal and data fetching.
- [ ] **WSL2 Check**: If running in WSL2, ensure the MT5 connector fails gracefully or specific instructions are provided for the Windows Bridge.

---

## Future / Advanced Features
- [ ] **Streaming Data**: Implement `StreamConn` for real-time ticket updates.
- [ ] **Rate Limiting**: Add exponential backoff for API calls.
- [ ] **HITL (Human-in-the-Loop)**: Integrate with `Obsidian_Vault/Needs_Action` for manual trade approval before execution.
