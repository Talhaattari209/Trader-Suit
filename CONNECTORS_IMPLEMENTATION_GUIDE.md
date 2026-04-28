# Connectors Implementation Guide

How the three core building blocks — MT5 connector, Gemini LLM wrapper, and DataStore —
are built in this project. Use this as a reference when wiring up the same pattern in a
second project that showcases Alpaca + MT5 with strategies and human-placed trades.

---

## 1. Python ↔ MetaTrader 5 Connector

### How it works

The connector lives in `connectors_tester/src/connectors/mt5_tester.py`.
It wraps the official `MetaTrader5` Python package (Windows-only DLL) in a set of
plain functions that return **plain Python dicts / lists** — no MT5 objects leak out.
This means the rest of the project (Streamlit UI, the LLM agent) never needs to import
MetaTrader5 directly.

### Key design decisions

| Decision | Reason |
|---|---|
| Lazy import via `_get_mt5()` | The package only installs on Windows. Deferring the import lets non-Windows machines import the module for UI / type-checking without crashing. |
| Module-level `_connected` flag | MT5 is a singleton DLL — there is exactly one terminal connection per process. The flag avoids calling `mt5.initialize()` twice. |
| `_ensure_connected()` auto-connect | Every public function calls this first, so callers never have to think about connection state. |
| All return values are `dict` / `list[dict]` | Serialisable to JSON; directly injectable into LLM prompts. |
| Error path returns `{"error": "…"}` (not exceptions) | The Streamlit UI can display `result.get("error")` cleanly instead of catching exceptions everywhere. |

### Required environment variables

```
MT5_LOGIN=<account number as integer>
MT5_PASSWORD=<account password>
MT5_SERVER=<broker server name, e.g. "ICMarkets-Demo">
MT5_PATH=<optional: full path to terminal64.exe>
```

Load them via `python-dotenv` in `.env`. The connector calls `load_dotenv()` lazily on
first `connect()`.

### Connection lifecycle

```python
# mt5_tester.py (simplified)

_connected: bool = False   # module-level singleton flag

def connect() -> dict:
    global _connected
    mt5   = _get_mt5()          # lazy import
    path  = os.environ.get("MT5_PATH") or None
    login = int(os.environ.get("MT5_LOGIN", "0"))
    # ...
    ok = mt5.initialize(path=path, login=login, password=password, server=server)
    if not ok:
        return {"connected": False, "error": str(mt5.last_error())}
    _connected = True
    return {"connected": True, "build": mt5.terminal_info().build}

def _ensure_connected() -> dict | None:
    """Auto-connect if not already. Returns error dict or None."""
    if not _connected:
        result = connect()
        if not result.get("connected"):
            return result
    return None
```

### Full function surface

```
connect()                                    → dict (connection status)
disconnect()                                 → None
get_account()                                → dict (balance, equity, margin, profit, leverage …)
get_positions(symbol=None)                   → list[dict] (open positions)
get_orders(symbol=None)                      → list[dict] (pending orders)
get_history(from_date, to_date, limit=100)   → list[dict] (closed deals, last 30 days default)
get_bars(symbol, timeframe="1h", count=100)  → list[dict] (OHLCV)
get_latest_tick(symbol)                      → dict (bid, ask, last, volume, time)
place_order(symbol, order_type, volume, price, sl, tp, …) → dict
modify_sl_tp(ticket, sl, tp)                 → dict
close_position(ticket, volume=None)          → dict
cancel_order(ticket)                         → dict
```

### Order type mapping

Market orders use `TRADE_ACTION_DEAL`; pending orders use `TRADE_ACTION_PENDING`.
The connector accepts a plain string and maps it internally:

```python
type_map = {
    "buy":             (mt5.TRADE_ACTION_DEAL,    mt5.ORDER_TYPE_BUY),
    "sell":            (mt5.TRADE_ACTION_DEAL,    mt5.ORDER_TYPE_SELL),
    "buy_limit":       (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_LIMIT),
    "sell_limit":      (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_LIMIT),
    "buy_stop":        (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_STOP),
    "sell_stop":       (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_STOP),
    "buy_stop_limit":  (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_BUY_STOP_LIMIT),
    "sell_stop_limit": (mt5.TRADE_ACTION_PENDING, mt5.ORDER_TYPE_SELL_STOP_LIMIT),
}
```

For market orders, if `price=None` the connector fetches the current tick automatically
(`ask` for buys, `bid` for sells).

SL/TP modification uses `TRADE_ACTION_SLTP` (no cancel-and-replace needed, unlike Alpaca).
Close uses an opposite-direction `TRADE_ACTION_DEAL` pointed at the existing position ticket.

### Debug output pattern

Every call prints a delimited block to stdout so you can trace what was sent and received:

```
============================================================
=== MT5 REQUEST === place_order
{"symbol": "US30", "type": "buy", "volume": 0.1, "sl": 44000.0, "tp": 44500.0}
============================================================

============================================================
=== MT5 RESPONSE === place_order OK
{"order": 123456, "deal": 654321, "volume": 0.1, "price": 44250.0, "status": "filled"}
============================================================
```

---

## 2. GEMINI_API_KEY Wrapper (LLM Client)

### Why Gemini and not OpenAI

The project uses Gemini (`gemini-1.5-flash` by default) as the LLM backend for all agents.
The key is stored in `.env` and read at runtime — no key is ever hardcoded.

### The abstraction layer

`src/tools/llm_client.py` defines a three-layer hierarchy:

```
BaseLLMClient  (abstract)
├── GeminiLLMClient    ← DEFAULT — requires GEMINI_API_KEY
└── AnthropicLLMClient ← OPTIONAL — requires ANTHROPIC_API_KEY
```

This means you can swap out the backend by changing one line in the factory function
without touching any agent code.

### Environment variable setup

```
# .env
GEMINI_API_KEY=AIzaSy...your_key_here...
```

### How the key is loaded (three-tier fallback)

```python
class GeminiLLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key=None):
        self.model_name = model_name
        # Tier 1: explicit argument (for tests / override)
        # Tier 2: environment variable already set in the process
        # Tier 3: load from .env via python-dotenv
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            from dotenv import load_dotenv
            load_dotenv()
            self._api_key = os.environ.get("GEMINI_API_KEY")
```

### How `configure()` mirrors OpenAI Agent SDK style

The `google.generativeai` SDK has a global `configure(api_key=...)` call that is
analogous to setting `openai.api_key` or passing a key to `AsyncOpenAI(api_key=...)`.
The wrapper handles this internally so the caller never touches the SDK directly:

```python
def _configure(self):
    if not self._api_key:
        raise RuntimeError("GEMINI_API_KEY not set; cannot call Gemini.")
    import google.generativeai as genai
    genai.configure(api_key=self._api_key)   # ← equivalent to openai.api_key = "..."
    return genai

async def complete(self, prompt: str, system: str | None = None) -> str:
    genai = self._configure()
    model = genai.GenerativeModel(self.model_name)
    # system prompt prepended inline (Gemini has no separate system role in basic SDK)
    full_prompt = f"System: {system}\n\nUser: {prompt}" if system else prompt
    response = await model.generate_content_async(full_prompt)
    return response.text
```

### If you are adapting this to the OpenAI Agent SDK

Replace `GeminiLLMClient` with an `OpenAILLMClient` that follows the same interface:

```python
class OpenAILLMClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        import openai
        self._client = openai.AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY")
        )
        self.model = model

    async def complete(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self._client.chat.completions.create(
            model=self.model, messages=messages
        )
        return resp.choices[0].message.content
```

Then update the factory:

```python
def get_default_llm_client() -> BaseLLMClient:
    return OpenAILLMClient()   # one-line swap
```

All agents continue to call `llm.complete(prompt, system=system_prompt)` without any changes.

### Debug logging

Every LLM call writes to both stdout and `DataStore/debug.log`:

```
============================================================
[2026-04-02T10:30:00+00:00] LLM CALL — model=gemini-1.5-flash
PROMPT (first 500 chars): System: You are the Trader-Suit agent…
RESPONSE (first 500 chars): I can see you have 3 open positions…
Elapsed: 1.43s
============================================================
```

### Instantiation in an agent

```python
# Inside any agent module:
from src.tools.llm_client import get_default_llm_client

llm = get_default_llm_client()                    # GeminiLLMClient()
response = await llm.complete(prompt, system=system_prompt)
```

---

## 3. DataStore — File-Based Agent Memory

### What it is

`AgentDatabase` (`src/autonomous_agent/database.py`) is the agent's persistent memory.
It stores three collections as human-readable JSON files so the LLM can always answer
questions like "what strategies do we have in production?", "what are my open MT5
positions?", or "what is my total realized P&L on US30?".

### Storage layout

```
DataStore/
└── autonomous_agent/
    ├── strategies.json   ← strategy registry
    ├── positions.json    ← position snapshots (open & closed)
    └── trades.json       ← every executed fill
```

The path is resolved in this order:
1. `datastore_path` constructor argument (for tests)
2. `AGENT_DATASTORE_PATH` environment variable
3. `DataStore/autonomous_agent/` relative to CWD (default)

### Why JSON files instead of SQLite

- Human-readable: you (or your client) can open the file in any editor to verify data.
- Zero extra dependency — `json` is in the Python standard library.
- For a trading system with fewer than ~10 000 records over its lifetime, file I/O is fast enough.
- Full consistency with the rest of the project's file-based patterns.

### Collection 1 — Strategies

Tracks the lifecycle of every strategy from draft through production to graveyard.

**Schema:**
```json
{
  "strategy_id":  "strat_20260402_143022_a3f9",
  "name":         "US30 Breakout H1",
  "status":       "production",
  "regime":       "trending",
  "symbol":       "US30",
  "timeframe":    "H1",
  "params":       {"fast_ema": 9, "slow_ema": 21, "atr_mult": 1.5},
  "performance":  {"sharpe": 1.8, "max_dd": 0.12, "hit_rate": 0.58},
  "code_path":    "src/models/production/us30_breakout_h1.py",
  "notes":        "Passed Monte Carlo 1000-run validation.",
  "created_at":   "2026-04-02T14:30:22+00:00",
  "updated_at":   "2026-04-02T14:30:22+00:00"
}
```

**Key methods:**
```python
db.add_strategy(data)                            # create / upsert by strategy_id
db.list_strategies(status="production")          # filter by status | symbol | regime
db.get_strategy(strategy_id)                     # fetch single record
db.update_strategy_status(strategy_id, "graveyard")  # lifecycle promotion
db.strategy_summary()                            # → {"total":12, "production":4, ...}
```

**Status lifecycle:**
```
draft → production   (after passing Killer / Monte Carlo validation)
draft → graveyard    (failed validation)
production → graveyard  (retired strategy)
```

### Collection 2 — Positions

Syncs broker position state into a local snapshot so the agent can answer
questions about SL, TP, unrealized P&L, and which strategy opened a position —
information that the broker API alone does not always expose.

**Schema:**
```json
{
  "position_id":     "pos_20260402_143022_b7c1",
  "symbol":          "US30",
  "side":            "long",
  "qty":             0.5,
  "entry_price":     44200.0,
  "current_price":   44380.0,
  "unrealized_pl":   90.0,
  "unrealized_plpc": 0.0041,
  "sl":              44050.0,
  "tp":              44600.0,
  "broker":          "mt5",
  "broker_pos_id":   "789012",
  "strategy_id":     "strat_20260402_143022_a3f9",
  "status":          "open",
  "opened_at":       "2026-04-02T09:00:00+00:00",
  "closed_at":       null,
  "last_updated":    "2026-04-02T14:30:22+00:00"
}
```

**Key methods:**
```python
db.upsert_position(data)              # create or update by broker_pos_id
db.list_positions(status="open")      # filter: open | closed | all
db.update_sl_tp(position_id, sl=44100.0, tp=44700.0)
db.close_position(position_id, close_price=44500.0, realized_pl=150.0)
db.position_summary()                 # → {"open":3, "closed":17, "total_unrealized_pl":245.50}
```

The `upsert_position` method matches on `broker_pos_id` so running a sync loop that
calls `get_positions()` from the broker and then `upsert_position()` for each result
is safe and idempotent — it updates existing records rather than creating duplicates.

### Collection 3 — Trades

An immutable append-only log of every executed fill. This is the source of truth
for P&L reporting and post-trade analysis.

**Schema:**
```json
{
  "trade_id":        "trade_20260402_143022_c2d4",
  "symbol":          "US30",
  "side":            "buy",
  "qty":             0.5,
  "order_type":      "market",
  "fill_price":      44200.0,
  "commission":      2.5,
  "realized_pl":     null,
  "broker":          "mt5",
  "broker_order_id": "123456",
  "strategy_id":     "strat_20260402_143022_a3f9",
  "sl":              44050.0,
  "tp":              44600.0,
  "status":          "filled",
  "executed_at":     "2026-04-02T09:00:00+00:00",
  "notes":           "Entry on H1 breakout signal"
}
```

**Key methods:**
```python
db.log_trade(data)                                # append new fill
db.list_trades(symbol="US30", broker="mt5", limit=50)
db.update_trade(trade_id, {"realized_pl": 150.0}) # set realized P&L after close
db.pnl_summary(symbol="US30")                     # aggregated stats (see below)
db.trade_summary()                                # quick count for context snapshot
```

`pnl_summary()` returns computed statistics in Python (not by the LLM, which is
unreliable at arithmetic):

```python
{
    "total_trades":        48,
    "trades_with_pl":      35,   # position closed, P&L known
    "winning_trades":      22,
    "losing_trades":       13,
    "total_realized_pl":   1230.50,
    "avg_pl_per_trade":    35.16,
    "hit_rate":            0.629,
    "largest_win":         420.00,
    "largest_loss":        -185.00,
}
```

### How the DataStore is injected into agent prompts

At the start of every LLM turn, `_build_context()` in the agent module calls
`db.full_summary()` and renders it into a compact text block that is appended to the
system prompt:

```python
db  = AgentDatabase()
s   = db.full_summary()
# Rendered as:
# LocalDB: strategies=12 (prod=4) | open_positions=3 | trades=48 realised_pl=1230.50
```

When the agent needs details (e.g. "list all production strategies"), it issues a
tool call and `_execute_tool()` calls the appropriate `db.*` method and returns JSON.
The full JSON is then appended as `TOOL_RESULT:` and the LLM synthesises a plain-English
answer from it.

### Tool protocol used by the agent

The agent communicates tool calls in plain text (no special SDK format needed), which
makes it model-agnostic:

```
TOOL_CALL: {"tool": "db_list_strategies", "args": {"status": "production"}}
TOOL_RESULT: [{"strategy_id": "strat_...", "name": "US30 Breakout H1", ...}]
```

The same pattern handles broker queries (`mt5_get_positions`, `get_account`, etc.)
and database writes (`db_log_trade`, `db_upsert_position`, `db_update_strategy_status`).

---

## Putting It All Together in a New Project

Here is the minimal wiring you need to replicate the pattern:

### File structure

```
your_project/
├── .env                          # GEMINI_API_KEY, MT5_*, ALPACA_*, ...
├── DataStore/
│   └── autonomous_agent/         # auto-created on first write
│       ├── strategies.json
│       ├── positions.json
│       └── trades.json
└── src/
    ├── connectors/
    │   ├── mt5_connector.py      # copy / adapt mt5_tester.py
    │   └── alpaca_connector.py   # copy / adapt alpaca_tester.py
    ├── tools/
    │   └── llm_client.py         # copy as-is; swap GeminiLLMClient for OpenAI if needed
    └── agent/
        ├── database.py           # copy as-is
        └── agent_core.py         # your agent loop using the three pieces above
```

### Minimal agent loop

```python
from src.tools.llm_client import get_default_llm_client
from src.agent.database import AgentDatabase
from src.connectors import mt5_connector, alpaca_connector

async def run_agent(user_message: str, broker: str, mode: str) -> str:
    llm = get_default_llm_client()
    db  = AgentDatabase()

    # 1. Build context snapshot
    summary = db.full_summary()
    account = mt5_connector.get_account() if broker == "mt5" else alpaca_connector.get_account()
    context = f"Account: {account}\nDB: {summary}"

    # 2. Build system prompt
    system = f"""You are a trading assistant.
{context}
TOOL_CALL: {{"tool": "<name>", "args": {{...}}}} to call tools.
"""

    # 3. Call LLM
    response = await llm.complete(user_message, system=system)

    # 4. Tool-call loop
    while "TOOL_CALL:" in response:
        tc   = parse_tool_call(response)           # extract JSON from response
        result = dispatch_tool(tc, broker, db)      # call connector or db
        response = await llm.complete(
            f"TOOL_RESULT: {result}\n\nASSISTANT:", system=system
        )

    return response
```

### Environment variables quick reference

```
# LLM
GEMINI_API_KEY=...          # or OPENAI_API_KEY if you swap the client

# MT5
MT5_LOGIN=123456
MT5_PASSWORD=yourpassword
MT5_SERVER=ICMarkets-Demo
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe   # optional

# Alpaca (paper or live)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ENDPOINT=https://paper-api.alpaca.markets/v2

# DataStore (optional override)
AGENT_DATASTORE_PATH=DataStore/autonomous_agent
```

---

*Generated from the `connectors_tester/` sub-project of the Alpha FTE Project, April 2026.*
