"""
Alpaca MCP Server – exposes trading capabilities to LLMs/Agents via
the Model Context Protocol (stdio transport).

Tools:
  - get_market_data   : Fetch OHLCV bars for a symbol.
  - submit_order      : Place a market or limit order (paper by default).
  - get_positions     : List all open positions.
  - get_account_info  : Return balance, equity, buying power.

Resources:
  - alpaca://market_status  : Whether the US equities market is open.
  - alpaca://account        : Snapshot of the account.

Prompts:
  - analyze_portfolio : Pre-built prompt for portfolio review.

Run:
  python -m src.mcp.alpaca_server          # stdio transport
  # or add to Claude Desktop / IDE MCP config
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Try to import MCP SDK; fall back to a minimal DIY JSON-RPC server
# ---------------------------------------------------------------------------
try:
    from mcp.server import Server
    from mcp.server.stdio import run_server
    from mcp.types import Tool, TextContent, Resource, ResourceContents
    _HAS_MCP_SDK = True
except ImportError:
    _HAS_MCP_SDK = False

# ---------------------------------------------------------------------------
# Alpaca helpers (lazy, so the file can be imported for tests)
# ---------------------------------------------------------------------------
_connector = None
_trading_client = None


def _get_connector():
    global _connector
    if _connector is None:
        from src.connectors.alpaca_connector import AlpacaConnector
        _connector = AlpacaConnector()
        _connector.connect()
    return _connector


def _get_trading_client():
    global _trading_client
    if _trading_client is None:
        _get_connector()  # ensure connected
        _trading_client = _connector._trading_client
    return _trading_client


# ═══════════════════════════════════════════════════════════════════════════
# Tool implementations
# ═══════════════════════════════════════════════════════════════════════════
def tool_get_market_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> dict:
    """Fetch OHLCV bars for *symbol*. Returns JSON-serialisable dict."""
    conn = _get_connector()
    df = conn.get_ohlcv(symbol, timeframe, limit)
    if df.empty:
        return {"symbol": symbol, "bars": [], "count": 0}
    records = df.reset_index().to_dict(orient="records")
    # Ensure timestamps are strings
    for r in records:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return {"symbol": symbol, "bars": records, "count": len(records)}


def tool_submit_order(
    symbol: str,
    side: str = "buy",
    qty: float = 1.0,
    order_type: str = "market",
    limit_price: float | None = None,
) -> dict:
    """Place an order. Returns order result dict."""
    conn = _get_connector()
    return conn.execute_order(symbol, side, qty, order_type, limit_price=limit_price)


def tool_get_positions() -> list[dict]:
    """List all open positions."""
    client = _get_trading_client()
    positions = client.get_all_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": getattr(p, "symbol", ""),
            "qty": str(getattr(p, "qty", 0)),
            "side": str(getattr(p, "side", "")),
            "market_value": str(getattr(p, "market_value", 0)),
            "unrealized_pl": str(getattr(p, "unrealized_pl", 0)),
            "current_price": str(getattr(p, "current_price", 0)),
        })
    return result


def tool_get_account_info() -> dict:
    """Return account balance, equity, buying power."""
    conn = _get_connector()
    return conn.get_account_state()


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════
def resource_market_status() -> dict:
    """Check if us market is open."""
    try:
        client = _get_trading_client()
        clock = client.get_clock()
        return {
            "is_open": getattr(clock, "is_open", False),
            "next_open": str(getattr(clock, "next_open", "")),
            "next_close": str(getattr(clock, "next_close", "")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


def resource_account_summary() -> dict:
    return tool_get_account_info()


# ═══════════════════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════════════════
ANALYZE_PORTFOLIO_PROMPT = """You are a senior quantitative portfolio analyst.
Analyze the current positions and account state and provide:
1. Risk exposure summary
2. Concentration risk warnings
3. Unrealized P&L assessment
4. Recommended actions (trim, hold, add)

Account: {account}
Positions: {positions}
Market Status: {market_status}
"""


# ═══════════════════════════════════════════════════════════════════════════
# MCP Server (SDK or DIY)
# ═══════════════════════════════════════════════════════════════════════════

TOOL_REGISTRY = {
    "get_market_data": {
        "fn": tool_get_market_data,
        "description": "Fetch OHLCV bars for a stock symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock/index symbol (e.g., AAPL, SPY)"},
                "timeframe": {"type": "string", "description": "Bar size: 1m, 5m, 15m, 1h, 1d", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of bars", "default": 100},
            },
            "required": ["symbol"],
        },
    },
    "submit_order": {
        "fn": tool_submit_order,
        "description": "Place a stock order (paper trading by default).",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock symbol"},
                "side": {"type": "string", "enum": ["buy", "sell"], "default": "buy"},
                "qty": {"type": "number", "description": "Number of shares", "default": 1},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "limit_price": {"type": "number", "description": "Limit price (required for limit orders)"},
            },
            "required": ["symbol"],
        },
    },
    "get_positions": {
        "fn": tool_get_positions,
        "description": "List all open positions with P&L.",
        "parameters": {"type": "object", "properties": {}},
    },
    "get_account_info": {
        "fn": tool_get_account_info,
        "description": "Get account balance, equity, and buying power.",
        "parameters": {"type": "object", "properties": {}},
    },
}


# ---------------------------------------------------------------------------
# Minimal JSON-RPC stdio server (fallback when `mcp` package is not installed)
# ---------------------------------------------------------------------------
def _run_jsonrpc_stdio():
    """
    Bare-bones JSON-RPC 2.0 server over stdin/stdout that implements the
    MCP tool-calling protocol so it works with Claude Desktop / IDE plugins.
    """
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    log = logging.getLogger("alpaca_mcp")
    log.info("Alpaca MCP server starting (JSON-RPC stdio, no SDK)")

    def _respond(id_, result=None, error=None):
        resp = {"jsonrpc": "2.0", "id": id_}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        line = json.dumps(resp)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        id_ = msg.get("id")
        params = msg.get("params", {})

        log.debug("Received: method=%s params=%s", method, params)

        # --- Initialize ---
        if method == "initialize":
            _respond(id_, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "alpaca-mcp", "version": "1.0.0"},
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            })

        # --- List tools ---
        elif method == "tools/list":
            tools = []
            for name, spec in TOOL_REGISTRY.items():
                tools.append({
                    "name": name,
                    "description": spec["description"],
                    "inputSchema": spec["parameters"],
                })
            _respond(id_, {"tools": tools})

        # --- Call tool ---
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            spec = TOOL_REGISTRY.get(tool_name)
            if not spec:
                _respond(id_, error={"code": -32601, "message": f"Unknown tool: {tool_name}"})
                continue
            try:
                result = spec["fn"](**arguments)
                _respond(id_, {
                    "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                    "isError": False,
                })
            except Exception as e:
                _respond(id_, {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                })

        # --- Resources list ---
        elif method == "resources/list":
            _respond(id_, {"resources": [
                {"uri": "alpaca://market_status", "name": "Market Status", "mimeType": "application/json"},
                {"uri": "alpaca://account", "name": "Account Summary", "mimeType": "application/json"},
            ]})

        # --- Resources read ---
        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri == "alpaca://market_status":
                data = resource_market_status()
            elif uri == "alpaca://account":
                data = resource_account_summary()
            else:
                _respond(id_, error={"code": -32602, "message": f"Unknown resource: {uri}"})
                continue
            _respond(id_, {"contents": [
                {"uri": uri, "mimeType": "application/json", "text": json.dumps(data, default=str)}
            ]})

        # --- Prompts list ---
        elif method == "prompts/list":
            _respond(id_, {"prompts": [
                {"name": "analyze_portfolio", "description": "Generates a portfolio analysis prompt with live data."},
            ]})

        # --- Prompts get ---
        elif method == "prompts/get":
            pname = params.get("name", "")
            if pname == "analyze_portfolio":
                account = json.dumps(tool_get_account_info(), default=str)
                positions = json.dumps(tool_get_positions(), default=str)
                market = json.dumps(resource_market_status(), default=str)
                text = ANALYZE_PORTFOLIO_PROMPT.format(
                    account=account, positions=positions, market_status=market
                )
                _respond(id_, {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]})
            else:
                _respond(id_, error={"code": -32602, "message": f"Unknown prompt: {pname}"})

        # --- Ping / unknown ---
        elif method == "ping":
            _respond(id_, {})
        else:
            if id_ is not None:
                _respond(id_, error={"code": -32601, "message": f"Method not found: {method}"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    if _HAS_MCP_SDK:
        # TODO: wire up via the official SDK's Server class when available
        # For now, use the DIY JSON-RPC server which is fully compatible.
        _run_jsonrpc_stdio()
    else:
        _run_jsonrpc_stdio()


if __name__ == "__main__":
    main()
