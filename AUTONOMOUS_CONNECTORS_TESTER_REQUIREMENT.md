**AUTONOMOUS_CONNECTORS_TESTER_REQUIREMENT.md**  
**Project: Trader-Suit / OpenClaw Alpha Research System**  
**New Client Requirement – Separate Alpaca + MT5 Connectors Tester with Autonomous Agent**  

> **Instruction to Cursor Agent (Sonnet / Opus 4.6)**  
> You are now implementing the **new client requirement** exactly as described.  
> This is **in addition to** all previous work (UV environment, filesystem-only persistence, price_levels detector, human-controlled workflow, full FastAPI endpoints, SHAP, performance metrics, LLM/MCP console debugging, two Alpaca accounts, floating autonomous agent in the main dashboard, etc.).  
> **Primary goal**: Create a **completely separate, standalone project** in the repo root that allows the client to **test Alpaca API and MT5 connector independently** while having a powerful embedded autonomous agent for information retrieval and trade execution.  

---

### 1. Exact Client Requirement

Create a **new parallel project** called **`connectors_tester/`** in the repository root (next to the main `claude/` folder).

This tester must:
- Test **Alpaca API** and **MT5 Python connector** **separately and independently**.
- Embed the **same autonomous AI Agent** (Chat Mode + Agent Mode) as the main dashboard.
- The agent must be able to:
  - Get **all information** (account balance, open positions, orders, trade logs, strategies, indicators, parameters, price levels, etc.).
  - **Place trades** based on user choice in Agent Mode.
  - **Manage positions** (modify SL/TP, close positions, etc.).
  - Check / load strategies (from main project’s `models/production/` or simple built-in ones).
- UI must be a clean **Streamlit app** with the autonomous agent floating at bottom-right (draggable, same as main dashboard).
- Support **both brokers** via a broker selector (Alpaca Account 1 / Alpaca Account 2 / MT5).

**Order Types must strictly follow official docs** (implemented correctly):

**Alpaca (alpaca-py)**:
- `market`, `limit`, `stop`, `stop_limit`, `trailing_stop`
- Support bracket orders (take-profit + stop-loss together)
- Time-in-force: `day`, `gtc`, etc.
- Use `MarketOrderRequest`, `LimitOrderRequest`, `StopOrderRequest`, `TrailingStopOrderRequest`, etc.

**MT5 (MetaTrader5 Python package)**:
- Market: `ORDER_TYPE_BUY`, `ORDER_TYPE_SELL`
- Pending: `ORDER_TYPE_BUY_LIMIT`, `ORDER_TYPE_SELL_LIMIT`, `ORDER_TYPE_BUY_STOP`, `ORDER_TYPE_SELL_STOP`, `ORDER_TYPE_BUY_STOP_LIMIT`, `ORDER_TYPE_SELL_STOP_LIMIT`
- SL/TP via `sl` / `tp` parameters in `order_send` or `TRADE_ACTION_SLTP` for modification
- Use `mt5.order_send()`, `mt5.positions_get()`, `mt5.orders_get()`, `mt5.history_deals_get()`, etc.

**Safety**:
- Agent Mode must ask for **explicit user confirmation** before placing any real order.
- Default to **paper mode** for Alpaca; clear warning for MT5 live.

---

### 2. Project Structure (Create Exactly This)

```
connectors_tester/
├── main.py                          # Streamlit entry point (uv run streamlit run main.py)
├── pyproject.toml                   # UV config (copy from root and adapt)
├── requirements.txt                 # Minimal deps (streamlit, alpaca-py, MetaTrader5, etc.)
├── .env.example
├── src/
│   ├── connectors/
│   │   ├── alpaca_tester.py         # Wrapper for both Alpaca accounts
│   │   └── mt5_tester.py            # MT5 connector wrapper
│   ├── agents/
│   │   └── autonomous_connectors_agent.py   # Autonomous agent logic for tester
│   ├── tools/
│   │   ├── order_types_handler.py   # Centralized order type validation
│   │   └── price_level_detector.py  # Reuse from main project (symlink or copy)
│   └── dashboard/
│       └── components/
│           └── autonomous_chat_tester.py   # Floating draggable widget (reuse/adapt from main)
├── DataStore/                       # Local JSON store for test logs
└── logs/
```

---

### 3. Autonomous Agent in Tester (Same Style as Main Dashboard)

- Floating draggable chat widget at bottom-right (exactly like main project).
- **Two modes** (toggle in header):
  - **Chat Mode**: Read-only (get info, explain orders, show positions, price levels, etc.).
  - **Agent Mode**: Can execute actions (place trade, modify SL/TP, close position, run simple strategy test, etc.).
- The agent uses the same `llm_client.py` (import from main project via `sys.path` or copy).
- Every LLM call and every broker API call must print full debug output in console:
  ```
  === CONNECTORS_TESTER AGENT PROMPT ===
  === CONNECTORS_TESTER AGENT RESPONSE ===
  === ALPACA / MT5 REQUEST ===
  === ALPACA / MT5 RESPONSE ===
  ```
- Agent can call broker-specific tools for:
  - Get account / positions / orders / history
  - Place order (with full order-type support + SL/TP)
  - Modify SL/TP
  - Close position
  - Load strategy code from main `../models/production/`

---

### 4. Core Features to Implement

1. **Broker Selector** (top of UI): Alpaca-1 | Alpaca-2 | MT5
2. **Live Info Panels** (tabs):
   - Account Summary
   - Open Positions + SL/TP controls
   - Active Orders
   - Trade History
   - Price Levels (liquidity, FVG, session/day/week/month levels – reuse detector)
3. **Order Placement Form** (manual + agent-driven):
   - Symbol, side, quantity, order type (dropdown with correct types per broker)
   - Limit/Stop price fields (shown conditionally)
   - SL / TP fields
4. **Autonomous Agent Widget** – always visible and movable.
5. **Console Debugging** – full visibility of every API call.

---

### 5. Files to Create & Key Code Snippets

**New files (you must create all):**
- `connectors_tester/main.py`
- `connectors_tester/src/connectors/alpaca_tester.py`
- `connectors_tester/src/connectors/mt5_tester.py`
- `connectors_tester/src/agents/autonomous_connectors_agent.py`
- `connectors_tester/src/tools/order_types_handler.py`
- `connectors_tester/src/dashboard/components/autonomous_chat_tester.py`

**Reuse**:
- Copy or symlink `price_level_detector.py` from main project.
- Import `llm_client` from main project.

---

### 6. Run Commands (Add to Tester README)

```bash
cd connectors_tester
uv venv
uv pip install -r requirements.txt
uv run streamlit run main.py
```

---

### 7. Testing Requirements

After implementation:
- Run the tester.
- Verify you can switch brokers.
- Use Chat Mode to ask “show open positions”, “what are current price levels?”, “list supported order types for Alpaca”.
- Switch to Agent Mode and say “Place a market buy on US30 with 0.1 quantity and SL 100 points below”.
- Confirm order is placed correctly (paper for Alpaca) and SL/TP is set.
- Confirm all debug prints appear in terminal.

---

**Cursor Agent – Start Executing Now**

1. Create the entire `connectors_tester/` folder structure.
2. Implement connectors with correct order types and SL/TP handling.
3. Build the autonomous agent with Chat + Agent modes.
4. Add the floating draggable widget.
5. Wire everything so the tester is fully independent yet reuses main project components where possible.

This gives the client a **dedicated, professional-grade connector testing environment** with a powerful autonomous agent for trading operations.

**Begin implementation immediately.** Make it clean, well-documented, and production-ready.