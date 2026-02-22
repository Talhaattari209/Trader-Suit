"""
Tests for advanced Alpaca connector architecture.
- CacheManager hit/miss/expiry
- ExecutionManager throttling and batching
- AlpacaConnector event bus
- MCP server tool registry
"""
import asyncio
import os
import sys
import time

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# CacheManager
# ---------------------------------------------------------------------------

class TestCacheManager:
    def test_make_key_deterministic(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=10)
        k1 = cm.make_key("US30", "1h", 500)
        k2 = cm.make_key("US30", "1h", 500)
        assert k1 == k2

    def test_set_and_get(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=60)
        df = pd.DataFrame({"Open": [1, 2], "Close": [3, 4]})
        key = cm.make_key("TEST", "1h", 2)
        cm.set(key, df)
        hit = cm.get(key)
        assert hit is not None
        assert len(hit) == 2

    def test_get_returns_none_on_miss(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=60)
        assert cm.get("nonexistent") is None

    def test_expiry(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=1)
        df = pd.DataFrame({"A": [1]})
        key = cm.make_key("X", "1m", 1)
        cm.set(key, df)
        assert cm.get(key) is not None
        time.sleep(1.1)
        assert cm.get(key) is None

    def test_invalidate(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=60)
        df = pd.DataFrame({"A": [1]})
        key = cm.make_key("Y", "1h", 1)
        cm.set(key, df)
        cm.invalidate(key)
        assert cm.get(key) is None

    def test_clear(self):
        from src.connectors.cache_manager import CacheManager
        cm = CacheManager(ttl_seconds=60)
        for i in range(5):
            cm.set(cm.make_key(f"S{i}", "1h", 1), pd.DataFrame({"A": [i]}))
        assert cm.size == 5
        cm.clear()
        assert cm.size == 0


# ---------------------------------------------------------------------------
# ExecutionManager – throttler
# ---------------------------------------------------------------------------

class TestTokenBucket:
    def test_acquire_does_not_block_under_limit(self):
        from src.connectors.execution_manager import TokenBucket
        bucket = TokenBucket(rate=100.0, burst=10)
        async def _run():
            start = time.monotonic()
            for _ in range(5):
                await bucket.acquire()
            elapsed = time.monotonic() - start
            assert elapsed < 1.0  # should be near-instant
        asyncio.run(_run())


class TestExecutionManager:
    def test_submit_order_calls_execute_fn(self):
        from src.connectors.execution_manager import ExecutionManager

        calls = []
        def mock_execute(symbol, side, qty, order_type, **kw):
            calls.append((symbol, side, qty))
            return {"status": "success", "order_id": "123"}

        mgr = ExecutionManager(execute_fn=mock_execute)

        async def _run():
            await mgr.start()
            result = await mgr.submit_order("AAPL", "buy", 1.0, "market")
            await mgr.stop()
            return result

        result = asyncio.run(_run())
        assert result["status"] == "success"
        assert len(calls) == 1
        assert calls[0] == ("AAPL", "buy", 1.0)

    def test_failover_on_rate_limit(self):
        from src.connectors.execution_manager import ExecutionManager

        def primary(symbol, side, qty, order_type, **kw):
            return {"status": "error", "order_id": None, "message": "429 rate limited"}

        backup_calls = []
        def backup(symbol, side, qty, order_type, **kw):
            backup_calls.append(symbol)
            return {"status": "success", "order_id": "backup-456"}

        mgr = ExecutionManager(execute_fn=primary, execute_fn_backup=backup)

        async def _run():
            await mgr.start()
            result = await mgr.submit_order("SPY", "buy", 1.0)
            await mgr.stop()
            return result

        result = asyncio.run(_run())
        assert result["status"] == "success"
        assert len(backup_calls) == 1


# ---------------------------------------------------------------------------
# AlpacaConnector event bus (no live connection needed)
# ---------------------------------------------------------------------------

class TestAlpacaEventBus:
    def test_on_and_emit(self):
        from src.connectors.alpaca_connector import AlpacaConnector
        conn = AlpacaConnector.__new__(AlpacaConnector)
        conn._event_listeners = {}
        conn._logger = __import__("logging").getLogger("test")

        received = []
        conn.on("bar", lambda data: received.append(data))
        conn._emit("bar", {"symbol": "US30", "close": 42000})
        assert len(received) == 1
        assert received[0]["symbol"] == "US30"


# ---------------------------------------------------------------------------
# MCP Server – tool registry
# ---------------------------------------------------------------------------

class TestMCPToolRegistry:
    def test_tool_registry_has_expected_tools(self):
        from src.mcp.alpaca_server import TOOL_REGISTRY
        expected = {"get_market_data", "submit_order", "get_positions", "get_account_info"}
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_each_tool_has_fn_and_description(self):
        from src.mcp.alpaca_server import TOOL_REGISTRY
        for name, spec in TOOL_REGISTRY.items():
            assert "fn" in spec, f"Tool {name} missing 'fn'"
            assert "description" in spec, f"Tool {name} missing 'description'"
            assert callable(spec["fn"]), f"Tool {name} 'fn' is not callable"
