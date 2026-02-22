"""
Market Data Cache Manager.

Provides in-memory + optional file-backed caching for OHLCV data
to reduce redundant REST API calls.  Cache entries expire based on
a configurable TTL (default 60 seconds for intraday data).

Usage:
    cache = CacheManager(ttl_seconds=60)
    key   = cache.make_key("US30", "1h", 500)
    hit   = cache.get(key)          # returns DataFrame or None
    cache.set(key, df)              # stores with timestamp
"""
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via env)
# ---------------------------------------------------------------------------
DEFAULT_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
CACHE_DIR = os.environ.get("CACHE_DIR", "")  # empty = in-memory only


class CacheEntry:
    """Single cached value with an expiration timestamp."""

    __slots__ = ("data", "expires_at")

    def __init__(self, data: pd.DataFrame, ttl: int):
        self.data = data
        self.expires_at = time.time() + ttl

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at


class CacheManager:
    """
    Thread-safe in-memory cache with optional disk persistence.

    * ``get`` / ``set`` operate on an in-memory dict guarded by a lock.
    * When ``cache_dir`` is provided, cache misses try the disk first,
      and ``set`` writes a Parquet snapshot beside the in-memory copy.
    * ``invalidate`` and ``clear`` are O(1).
    """

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL,
        cache_dir: Optional[str] = CACHE_DIR or None,
    ):
        self._ttl = ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._cache_dir: Optional[Path] = None
        if cache_dir:
            self._cache_dir = Path(cache_dir)
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------
    @staticmethod
    def make_key(symbol: str, timeframe: str, count: int) -> str:
        """Deterministic cache key."""
        raw = f"{symbol}|{timeframe}|{count}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Return cached DataFrame or None if missing / expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry and not entry.expired:
                return entry.data.copy()
            # Remove stale
            self._store.pop(key, None)

        # Fallback: try disk
        if self._cache_dir:
            return self._read_disk(key)
        return None

    def set(self, key: str, df: pd.DataFrame) -> None:
        """Store *df* under *key* with the configured TTL."""
        with self._lock:
            self._store[key] = CacheEntry(df.copy(), self._ttl)
        if self._cache_dir:
            self._write_disk(key, df)

    def invalidate(self, key: str) -> None:
        """Remove a single entry."""
        with self._lock:
            self._store.pop(key, None)
        if self._cache_dir:
            p = self._cache_dir / f"{key}.parquet"
            p.unlink(missing_ok=True)

    def clear(self) -> None:
        """Drop every cached entry."""
        with self._lock:
            self._store.clear()
        if self._cache_dir:
            for p in self._cache_dir.glob("*.parquet"):
                p.unlink(missing_ok=True)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # ------------------------------------------------------------------
    # Disk helpers (best-effort; failures are silent)
    # ------------------------------------------------------------------
    def _write_disk(self, key: str, df: pd.DataFrame) -> None:
        try:
            path = self._cache_dir / f"{key}.parquet"  # type: ignore[union-attr]
            meta_path = self._cache_dir / f"{key}.meta.json"  # type: ignore[union-attr]
            df.to_parquet(path)
            meta_path.write_text(json.dumps({"expires_at": time.time() + self._ttl}))
        except Exception:
            pass

    def _read_disk(self, key: str) -> Optional[pd.DataFrame]:
        try:
            path = self._cache_dir / f"{key}.parquet"  # type: ignore[union-attr]
            meta_path = self._cache_dir / f"{key}.meta.json"  # type: ignore[union-attr]
            if not path.exists() or not meta_path.exists():
                return None
            meta = json.loads(meta_path.read_text())
            if time.time() >= meta.get("expires_at", 0):
                path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return None
            df = pd.read_parquet(path)
            # Promote back to in-memory
            remaining = max(1, int(meta["expires_at"] - time.time()))
            with self._lock:
                self._store[key] = CacheEntry(df, remaining)
            return df.copy()
        except Exception:
            return None
