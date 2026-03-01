"""
Market stream: real-time US30 (or other) data from Alpaca (stream_market_data skill).
Persist to local buffer or Neon when configured. Stub implementation; extend with alpaca-py Stream.
"""
import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_ASSET = "US30"
DEFAULT_INTERVAL_MIN = 1


class MarketStreamer:
    """
    Stream quotes/ticks for an asset and optionally persist (e.g. Parquet, Neon).
    Use start() in a PM2-managed process. Requires ALPACA_API_KEY when using Alpaca.
    """

    def __init__(
        self,
        asset: str = DEFAULT_ASSET,
        provider: str = "alpaca",
        storage_interval_min: int = DEFAULT_INTERVAL_MIN,
        on_quote: Optional[Callable[[Any], None]] = None,
    ):
        self.asset = asset
        self.provider = provider
        self.storage_interval_min = storage_interval_min
        self.on_quote = on_quote or (lambda q: None)
        self._running = False

    def start(self) -> None:
        """Start streaming. Stub: log and return; override with alpaca-py Stream."""
        logger.info("MarketStreamer stub started (asset=%s, provider=%s). Wire alpaca-py for live data.", self.asset, self.provider)
        self._running = True
        # When implementing: from alpaca_trade_api import Stream; stream = Stream(); stream.subscribe_quotes(self._on_quote, self.asset); stream.run()

    def _on_quote(self, quote: Any) -> None:
        try:
            self.on_quote(quote)
        except Exception as e:
            logger.exception("on_quote: %s", e)

    def stop(self) -> None:
        self._running = False
