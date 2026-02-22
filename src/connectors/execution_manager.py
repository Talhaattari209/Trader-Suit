"""
Execution Manager – order queuing, throttling, and batching.

Provides an *async* order pipeline that:
1. Accepts orders into an ``asyncio.Queue``.
2. Drains orders through a **token-bucket throttler** that respects
   Alpaca's documented rate limit (~200 order calls / minute).
3. Optionally batches small orders on the same symbol/side into a
   single larger order ("fewer but larger orders").
4. Supports **multi-account failover**: if Account-1 is rate-limited
   (HTTP 429), the next order attempt is routed to Account-2.

Non-async callers can use ``submit_order_sync`` which bridges via
``asyncio.run`` (or the running loop).

Usage (async)::

    mgr = ExecutionManager(connector)
    await mgr.start()
    result = await mgr.submit_order("US30", "buy", 1.0, "market")
    await mgr.stop()
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
MAX_ORDERS_PER_MINUTE = int(os.environ.get("ALPACA_MAX_ORDERS_PER_MIN", "200"))
BATCH_WINDOW_MS = int(os.environ.get("ORDER_BATCH_WINDOW_MS", "500"))


# ---------------------------------------------------------------------------
# Token-bucket throttler
# ---------------------------------------------------------------------------
class TokenBucket:
    """
    Simple token-bucket rate limiter.

    ``tokens_per_second`` defaults to MAX_ORDERS_PER_MINUTE / 60.
    """

    def __init__(self, rate: float | None = None, burst: int | None = None):
        self._rate = rate or (MAX_ORDERS_PER_MINUTE / 60.0)
        self._burst = burst or max(10, int(self._rate * 2))
        self._tokens = float(self._burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # Sleep until at least one token refills
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)


# ---------------------------------------------------------------------------
# Pending order
# ---------------------------------------------------------------------------
@dataclass
class PendingOrder:
    symbol: str
    side: str
    qty: float
    order_type: str
    kwargs: dict = field(default_factory=dict)
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


# ---------------------------------------------------------------------------
# Execution Manager
# ---------------------------------------------------------------------------
class ExecutionManager:
    """
    Async order pipeline with throttling, batching, and multi-account failover.

    Parameters
    ----------
    execute_fn : callable
        The actual ``connector.execute_order`` function (or any async/sync
        callable with signature ``(symbol, side, qty, order_type, **kw) -> dict``).
    execute_fn_backup : callable, optional
        Backup execution function (second account).  Used when the primary
        returns a rate-limit / 429 response.
    enable_batching : bool
        When True, orders for the same symbol+side arriving within
        ``BATCH_WINDOW_MS`` are combined into one larger order.
    """

    def __init__(
        self,
        execute_fn: Callable[..., Any],
        execute_fn_backup: Optional[Callable[..., Any]] = None,
        enable_batching: bool = False,
    ):
        self._execute = execute_fn
        self._execute_backup = execute_fn_backup
        self._bucket = TokenBucket()
        self._queue: asyncio.Queue[PendingOrder] = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._enable_batching = enable_batching
        self._batch_window = BATCH_WINDOW_MS / 1000.0  # seconds

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("ExecutionManager started (batching=%s)", self._enable_batching)

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("ExecutionManager stopped")

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------
    async def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        **kwargs: Any,
    ) -> dict:
        """
        Enqueue an order and wait for the result.

        Returns the dict from the underlying ``execute_fn``.
        """
        loop = asyncio.get_running_loop()
        pending = PendingOrder(
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            kwargs=kwargs,
            future=loop.create_future(),
        )
        await self._queue.put(pending)
        return await pending.future

    def submit_order_sync(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        **kwargs: Any,
    ) -> dict:
        """Synchronous bridge for non-async callers."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Schedule on the running loop (e.g. from a thread)
            future = asyncio.run_coroutine_threadsafe(
                self.submit_order(symbol, side, qty, order_type, **kwargs), loop
            )
            return future.result(timeout=30)
        else:
            return asyncio.run(
                self.submit_order(symbol, side, qty, order_type, **kwargs)
            )

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------
    async def _worker(self) -> None:
        """Drain the queue, applying throttling and optional batching."""
        while self._running:
            try:
                pending = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if self._enable_batching:
                batch = [pending]
                # Collect more orders arriving within the batch window
                deadline = time.monotonic() + self._batch_window
                while time.monotonic() < deadline:
                    try:
                        extra = self._queue.get_nowait()
                        batch.append(extra)
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(0.05)
                await self._execute_batch(batch)
            else:
                await self._execute_single(pending)

    async def _execute_single(self, order: PendingOrder) -> None:
        await self._bucket.acquire()
        result = await self._call_execute(
            order.symbol, order.side, order.qty, order.order_type, **order.kwargs
        )
        if not order.future.done():
            order.future.set_result(result)

    async def _execute_batch(self, batch: list[PendingOrder]) -> None:
        """Group orders by (symbol, side, order_type) and fire one per group."""
        groups: dict[tuple[str, str, str], list[PendingOrder]] = {}
        for o in batch:
            key = (o.symbol, o.side, o.order_type)
            groups.setdefault(key, []).append(o)

        for (symbol, side, otype), orders in groups.items():
            total_qty = sum(o.qty for o in orders)
            merged_kwargs = orders[0].kwargs  # use first order's kwargs
            await self._bucket.acquire()
            result = await self._call_execute(
                symbol, side, total_qty, otype, **merged_kwargs
            )
            for o in orders:
                if not o.future.done():
                    o.future.set_result(result)

    async def _call_execute(
        self, symbol: str, side: str, qty: float, order_type: str, **kwargs: Any
    ) -> dict:
        """Call primary execute_fn; failover to backup on 429 / rate-limit."""
        result = await self._invoke(self._execute, symbol, side, qty, order_type, **kwargs)

        # Check for rate-limit signal
        if self._execute_backup and self._is_rate_limited(result):
            logger.warning(
                "Primary account rate-limited; failing over to backup account"
            )
            result = await self._invoke(
                self._execute_backup, symbol, side, qty, order_type, **kwargs
            )
        return result

    async def _invoke(
        self, fn: Callable, symbol: str, side: str, qty: float, order_type: str, **kwargs: Any
    ) -> dict:
        """Invoke fn (sync or async)."""
        try:
            out = fn(symbol=symbol, side=side, qty=qty, order_type=order_type, **kwargs)
            if asyncio.iscoroutine(out):
                out = await out
            return out  # type: ignore[return-value]
        except Exception as e:
            logger.exception("execute_fn raised")
            return {"status": "error", "order_id": None, "message": str(e)}

    @staticmethod
    def _is_rate_limited(result: dict) -> bool:
        msg = str(result.get("message", "")).lower()
        status = str(result.get("status", "")).lower()
        return "429" in msg or "rate" in msg or status == "rate_limited"
