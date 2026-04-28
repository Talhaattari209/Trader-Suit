"""
Indicator Engine — wraps the local pandas_ta_classic library.

Uses the FULL source code from:
  C:/Users/User/Downloads/claude/Technical Indicators/pandas-ta-classic-main/

Each indicator is defined with:
  - defaults: default parameter values
  - ranges:   (min, max) tuples used by Monte Carlo parameter sweeping
  - category: which sub-package the indicator lives in
  - inputs:   which OHLCV columns are required

Monte Carlo parameter sweep:
  call sweep_indicator_params(name, df, n_samples) to get a list of
  DataFrames/Series computed with randomly sampled parameters — used by
  MonteCarloPro.indicator_parameter_sweep().
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── Register the local pandas_ta_classic library ─────────────────────────────

_TA_LIB_ROOT = Path(
    r"C:\Users\User\Downloads\claude\Technical Indicators\pandas-ta-classic-main"
)

def _ensure_ta_on_path() -> bool:
    """Add the local pandas_ta_classic to sys.path if not already importable."""
    try:
        import pandas_ta_classic  # noqa: F401
        return True
    except ImportError:
        pass

    candidate = str(_TA_LIB_ROOT)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)
    try:
        import pandas_ta_classic  # noqa: F401
        return True
    except ImportError:
        return False


_TA_AVAILABLE = _ensure_ta_on_path()


# ── Indicator parameter catalogue ────────────────────────────────────────────
#
# Each entry: {
#   "defaults": {param: value, ...},
#   "ranges":   {param: (min, max), ...},   ← used for MC sweeping
#   "category": str,
#   "inputs":   list[str],                  ← "close" | "high" | "low" | "volume"
# }

INDICATOR_SPECS: dict[str, dict] = {
    # ── Moving averages / overlap ─────────────────────────────────────────────
    "SMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 200)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "EMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 200)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "DEMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 100)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "TEMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 100)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "WMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 100)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "HMA": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 100)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "KAMA": {
        "defaults": {"length": 10, "fast": 2, "slow": 30},
        "ranges":   {"length": (5, 30), "fast": (2, 10), "slow": (15, 50)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "ALMA": {
        "defaults": {"length": 10, "sigma": 6.0, "distribution_offset": 0.85},
        "ranges":   {"length": (5, 50), "sigma": (3.0, 12.0)},
        "category": "overlap",
        "inputs":   ["close"],
    },
    "VWAP": {
        "defaults": {"anchor": "D"},
        "ranges":   {},
        "category": "overlap",
        "inputs":   ["high", "low", "close", "volume"],
    },
    "VWMA": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 50)},
        "category": "overlap",
        "inputs":   ["close", "volume"],
    },
    "SuperTrend": {
        "defaults": {"length": 7, "multiplier": 3.0},
        "ranges":   {"length": (5, 20), "multiplier": (1.5, 5.0)},
        "category": "overlap",
        "inputs":   ["high", "low", "close"],
    },

    # ── Momentum ──────────────────────────────────────────────────────────────
    "RSI": {
        "defaults": {"length": 14, "scalar": 100},
        "ranges":   {"length": (5, 30)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "MACD": {
        "defaults": {"fast": 12, "slow": 26, "signal": 9},
        "ranges":   {"fast": (5, 20), "slow": (15, 50), "signal": (5, 15)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "Stochastic": {
        "defaults": {"k": 14, "d": 3, "smooth_k": 3},
        "ranges":   {"k": (5, 21), "d": (2, 5), "smooth_k": (1, 5)},
        "category": "momentum",
        "inputs":   ["high", "low", "close"],
    },
    "StochRSI": {
        "defaults": {"length": 14, "rsi_length": 14, "k": 3, "d": 3},
        "ranges":   {"length": (5, 21), "rsi_length": (5, 21)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "CCI": {
        "defaults": {"length": 14, "c": 0.015},
        "ranges":   {"length": (5, 30), "c": (0.005, 0.03)},
        "category": "momentum",
        "inputs":   ["high", "low", "close"],
    },
    "AO": {
        "defaults": {"fast": 5, "slow": 34},
        "ranges":   {"fast": (3, 10), "slow": (20, 50)},
        "category": "momentum",
        "inputs":   ["high", "low"],
    },
    "MOM": {
        "defaults": {"length": 10},
        "ranges":   {"length": (3, 30)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "ROC": {
        "defaults": {"length": 10},
        "ranges":   {"length": (3, 30)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "WillR": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "momentum",
        "inputs":   ["high", "low", "close"],
    },
    "PPO": {
        "defaults": {"fast": 12, "slow": 26, "signal": 9},
        "ranges":   {"fast": (5, 20), "slow": (15, 50), "signal": (5, 15)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "RSX": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "momentum",
        "inputs":   ["close"],
    },
    "KDJ": {
        "defaults": {"length": 9, "signal": 3},
        "ranges":   {"length": (5, 21), "signal": (2, 5)},
        "category": "momentum",
        "inputs":   ["high", "low", "close"],
    },
    "Fisher": {
        "defaults": {"length": 9},
        "ranges":   {"length": (5, 21)},
        "category": "momentum",
        "inputs":   ["high", "low"],
    },
    "QQE": {
        "defaults": {"length": 14, "smooth": 5},
        "ranges":   {"length": (5, 30), "smooth": (3, 10)},
        "category": "momentum",
        "inputs":   ["close"],
    },

    # ── Volatility ────────────────────────────────────────────────────────────
    "ATR": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "volatility",
        "inputs":   ["high", "low", "close"],
    },
    "BBands": {
        "defaults": {"length": 20, "std": 2.0},
        "ranges":   {"length": (10, 50), "std": (1.5, 3.0)},
        "category": "volatility",
        "inputs":   ["close"],
    },
    "KeltnerChannel": {
        "defaults": {"length": 20, "scalar": 2.0},
        "ranges":   {"length": (10, 50), "scalar": (1.5, 3.0)},
        "category": "volatility",
        "inputs":   ["high", "low", "close"],
    },
    "NATR": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "volatility",
        "inputs":   ["high", "low", "close"],
    },
    "Donchian": {
        "defaults": {"lower_length": 20, "upper_length": 20},
        "ranges":   {"lower_length": (5, 50), "upper_length": (5, 50)},
        "category": "volatility",
        "inputs":   ["high", "low", "close"],
    },
    "UI": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "volatility",
        "inputs":   ["close"],
    },

    # ── Trend ─────────────────────────────────────────────────────────────────
    "ADX": {
        "defaults": {"length": 14, "lensig": 14},
        "ranges":   {"length": (5, 30), "lensig": (5, 30)},
        "category": "trend",
        "inputs":   ["high", "low", "close"],
    },
    "AROON": {
        "defaults": {"length": 25},
        "ranges":   {"length": (10, 50)},
        "category": "trend",
        "inputs":   ["high", "low"],
    },
    "PSAR": {
        "defaults": {"af0": 0.02, "af": 0.02, "max_af": 0.20},
        "ranges":   {"af0": (0.01, 0.05), "af": (0.01, 0.05), "max_af": (0.10, 0.40)},
        "category": "trend",
        "inputs":   ["high", "low", "close"],
    },
    "CHOP": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "trend",
        "inputs":   ["high", "low", "close"],
    },
    "Vortex": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "trend",
        "inputs":   ["high", "low", "close"],
    },

    # ── Volume ────────────────────────────────────────────────────────────────
    "OBV": {
        "defaults": {},
        "ranges":   {},
        "category": "volume",
        "inputs":   ["close", "volume"],
    },
    "CMF": {
        "defaults": {"length": 20},
        "ranges":   {"length": (5, 40)},
        "category": "volume",
        "inputs":   ["high", "low", "close", "volume"],
    },
    "MFI": {
        "defaults": {"length": 14},
        "ranges":   {"length": (5, 30)},
        "category": "volume",
        "inputs":   ["high", "low", "close", "volume"],
    },
    "VWMACD": {
        "defaults": {"fast": 12, "slow": 26, "signal": 9},
        "ranges":   {"fast": (5, 20), "slow": (15, 50), "signal": (5, 15)},
        "category": "volume",
        "inputs":   ["close", "volume"],
    },

    # ── Statistics ────────────────────────────────────────────────────────────
    "ZScore": {
        "defaults": {"length": 30},
        "ranges":   {"length": (10, 60)},
        "category": "statistics",
        "inputs":   ["close"],
    },
    "StDev": {
        "defaults": {"length": 30},
        "ranges":   {"length": (10, 60)},
        "category": "statistics",
        "inputs":   ["close"],
    },
}


# ── Core compute function ─────────────────────────────────────────────────────

def compute_indicator(
    name: str,
    df: pd.DataFrame,
    **params: Any,
) -> pd.Series | pd.DataFrame | None:
    """
    Compute a named indicator using the local pandas_ta_classic library.

    Args:
        name:   Indicator name (case-insensitive, e.g. "RSI", "MACD", "ATR")
        df:     OHLCV DataFrame with columns Open/High/Low/Close/Volume
        **params: Override default parameters (e.g. length=20, fast=12)

    Returns:
        pd.Series or pd.DataFrame depending on the indicator.
        Returns None if the library is unavailable or calculation fails.
    """
    if not _TA_AVAILABLE:
        return _fallback_compute(name, df, **params)

    try:
        import pandas_ta_classic as ta
    except ImportError:
        return _fallback_compute(name, df, **params)

    spec = INDICATOR_SPECS.get(name.upper() if name.upper() in INDICATOR_SPECS
                               else _normalize_name(name))
    defaults = (spec or {}).get("defaults", {})
    merged   = {**defaults, **params}

    # Column aliases — handle both upper and title case
    close  = _col(df, "close")
    high   = _col(df, "high")
    low    = _col(df, "low")
    volume = _col(df, "volume")

    key = name.upper()
    try:
        if key == "SMA":
            return ta.sma(close, **merged)
        elif key == "EMA":
            return ta.ema(close, **merged)
        elif key == "DEMA":
            return ta.dema(close, **merged)
        elif key == "TEMA":
            return ta.tema(close, **merged)
        elif key == "WMA":
            return ta.wma(close, **merged)
        elif key == "HMA":
            return ta.hma(close, **merged)
        elif key == "KAMA":
            return ta.kama(close, **merged)
        elif key == "ALMA":
            return ta.alma(close, **merged)
        elif key == "VWAP":
            return ta.vwap(high, low, close, volume, **merged)
        elif key == "VWMA":
            return ta.vwma(close, volume, **merged)
        elif key == "SUPERTREND":
            return ta.supertrend(high, low, close, **merged)
        elif key == "RSI":
            return ta.rsi(close, **merged)
        elif key == "MACD":
            return ta.macd(close, **merged)
        elif key in ("STOCHASTIC", "STOCH"):
            return ta.stoch(high, low, close, **{k.replace("smooth_k", "smooth_k"): v for k, v in merged.items()})
        elif key == "STOCHRSI":
            return ta.stochrsi(close, **merged)
        elif key == "CCI":
            return ta.cci(high, low, close, **merged)
        elif key == "AO":
            return ta.ao(high, low, **merged)
        elif key == "MOM":
            return ta.mom(close, **merged)
        elif key == "ROC":
            return ta.roc(close, **merged)
        elif key == "WILLR":
            return ta.willr(high, low, close, **merged)
        elif key == "PPO":
            return ta.ppo(close, **merged)
        elif key == "RSX":
            return ta.rsx(close, **merged)
        elif key == "KDJ":
            return ta.kdj(high, low, close, **merged)
        elif key == "FISHER":
            return ta.fisher(high, low, **merged)
        elif key == "QQE":
            return ta.qqe(close, **merged)
        elif key == "ATR":
            return ta.atr(high, low, close, **merged)
        elif key in ("BBANDS", "BOLLINGER BANDS", "BB"):
            return ta.bbands(close, **merged)
        elif key in ("KELTNERCHANNEL", "KC"):
            return ta.kc(high, low, close, **merged)
        elif key == "NATR":
            return ta.natr(high, low, close, **merged)
        elif key == "DONCHIAN":
            return ta.donchian(high, low, **{k.replace("lower_length", "lower_length"): v for k, v in merged.items()})
        elif key == "UI":
            return ta.ui(close, **merged)
        elif key == "ADX":
            return ta.adx(high, low, close, **merged)
        elif key == "AROON":
            return ta.aroon(high, low, **merged)
        elif key == "PSAR":
            return ta.psar(high, low, close, **merged)
        elif key == "CHOP":
            return ta.chop(high, low, close, **merged)
        elif key == "VORTEX":
            return ta.vortex(high, low, close, **merged)
        elif key == "OBV":
            return ta.obv(close, volume)
        elif key == "CMF":
            return ta.cmf(high, low, close, volume, **merged)
        elif key == "MFI":
            return ta.mfi(high, low, close, volume, **merged)
        elif key == "VWMACD":
            return ta.vwmacd(close, volume, **merged)
        elif key == "ZSCORE":
            return ta.zscore(close, **merged)
        elif key == "STDEV":
            return ta.stdev(close, **merged)
        else:
            # Generic fallback: try ta.<lower>(close, ...)
            fn = getattr(ta, key.lower(), None)
            if fn:
                return fn(close, **merged)
            return None
    except Exception:
        return _fallback_compute(name, df, **params)


def _col(df: pd.DataFrame, name: str) -> pd.Series | None:
    """Return a column from df by case-insensitive name."""
    for c in df.columns:
        if c.lower() == name.lower():
            return df[c]
    return None


def _normalize_name(name: str) -> str:
    mapping = {
        "bollinger bands": "BBANDS",
        "bb": "BBANDS",
        "bollinger": "BBANDS",
        "stochastic": "STOCHASTIC",
        "stoch": "STOCHASTIC",
        "supertrend": "SUPERTREND",
        "kc": "KELTNERCHANNEL",
        "keltnerchannel": "KELTNERCHANNEL",
    }
    return mapping.get(name.lower(), name.upper())


# ── Pure-pandas fallback (no local library needed) ────────────────────────────

def _fallback_compute(
    name: str, df: pd.DataFrame, **params
) -> pd.Series | pd.DataFrame | None:
    """
    Minimal fallback implementations using only pandas/numpy.
    Used when pandas_ta_classic is not importable.
    """
    close  = _col(df, "close")
    high   = _col(df, "high")
    low    = _col(df, "low")
    volume = _col(df, "volume")
    if close is None:
        return None

    key = name.upper()

    if key == "SMA":
        length = params.get("length", 20)
        s = close.rolling(length).mean()
        s.name = f"SMA_{length}"
        return s

    if key == "EMA":
        length = params.get("length", 20)
        s = close.ewm(span=length, adjust=False).mean()
        s.name = f"EMA_{length}"
        return s

    if key == "RSI":
        length = params.get("length", 14)
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(length).mean()
        loss  = (-delta.clip(upper=0)).rolling(length).mean()
        rs    = gain / loss.replace(0, 1e-9)
        s     = 100 - 100 / (1 + rs)
        s.name = f"RSI_{length}"
        return s

    if key == "MACD":
        fast   = params.get("fast", 12)
        slow   = params.get("slow", 26)
        signal = params.get("signal", 9)
        macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return pd.DataFrame({
            f"MACD_{fast}_{slow}_{signal}": macd_line,
            f"MACDs_{fast}_{slow}_{signal}": signal_line,
            f"MACDh_{fast}_{slow}_{signal}": hist,
        })

    if key == "ATR":
        length = params.get("length", 14)
        if high is None or low is None:
            return None
        hl  = high - low
        hpc = (high - close.shift()).abs()
        lpc = (low  - close.shift()).abs()
        tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        s   = tr.ewm(alpha=1/length, adjust=False).mean()
        s.name = f"ATR_{length}"
        return s

    if key in ("BBANDS", "BB", "BOLLINGER BANDS"):
        length = params.get("length", 20)
        std    = params.get("std", 2.0)
        mid    = close.rolling(length).mean()
        sigma  = close.rolling(length).std()
        upper  = mid + std * sigma
        lower  = mid - std * sigma
        return pd.DataFrame({
            f"BBL_{length}_{std}": lower,
            f"BBM_{length}_{std}": mid,
            f"BBU_{length}_{std}": upper,
        })

    if key == "WMA":
        length = params.get("length", 20)
        weights = np.arange(1, length + 1)
        s = close.rolling(length).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
        s.name = f"WMA_{length}"
        return s

    if key == "MOM":
        length = params.get("length", 10)
        s = close.diff(length)
        s.name = f"MOM_{length}"
        return s

    if key == "ROC":
        length = params.get("length", 10)
        s = close.pct_change(length) * 100
        s.name = f"ROC_{length}"
        return s

    if key == "CCI":
        length = params.get("length", 14)
        c_val  = params.get("c", 0.015)
        if high is None or low is None:
            return None
        tp  = (high + low + close) / 3
        mad = tp.rolling(length).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        s   = (tp - tp.rolling(length).mean()) / (c_val * mad)
        s.name = f"CCI_{length}"
        return s

    if key == "STDEV":
        length = params.get("length", 30)
        s = close.rolling(length).std()
        s.name = f"STDEV_{length}"
        return s

    if key == "ZSCORE":
        length = params.get("length", 30)
        mu    = close.rolling(length).mean()
        sigma = close.rolling(length).std().replace(0, 1e-9)
        s     = (close - mu) / sigma
        s.name = f"ZSCORE_{length}"
        return s

    if key == "OBV":
        if volume is None:
            return None
        direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        s = (direction * volume).cumsum()
        s.name = "OBV"
        return s

    return None


# ── MC parameter sweep ────────────────────────────────────────────────────────

def sweep_indicator_params(
    name: str,
    df: pd.DataFrame,
    n_samples: int | None = None,
    seed: int | None = 42,
) -> list[dict]:
    """
    Randomly sample indicator parameters within their defined ranges and
    compute the indicator for each sample.

    Returns a list of dicts:
        [{"params": {...}, "result": pd.Series|pd.DataFrame}, ...]
    Used by MonteCarloPro.indicator_parameter_sweep().
    """
    from src.config.computation_budget import budget as CB
    n_samples = n_samples if n_samples is not None else CB.mc_indicator_samples

    spec = INDICATOR_SPECS.get(_normalize_name(name))
    if spec is None:
        return []

    rng    = np.random.default_rng(seed)
    ranges = spec.get("ranges", {})
    defaults = spec.get("defaults", {})

    if not ranges:
        # No sweepable params — just return one result with defaults
        result = compute_indicator(name, df, **defaults)
        if result is not None:
            return [{"params": defaults, "result": result}]
        return []

    samples = []
    for _ in range(n_samples):
        sampled: dict[str, Any] = {}
        for param, (lo, hi) in ranges.items():
            if isinstance(lo, int) and isinstance(hi, int):
                sampled[param] = int(rng.integers(lo, hi + 1))
            else:
                sampled[param] = float(rng.uniform(lo, hi))
        result = compute_indicator(name, df, **sampled)
        if result is not None:
            samples.append({"params": sampled, "result": result})

    return samples


def get_all_indicator_specs() -> dict:
    """Return the full INDICATOR_SPECS catalogue (for UI/MC configuration)."""
    return INDICATOR_SPECS


def list_indicators() -> list[str]:
    """Return sorted list of all indicator names."""
    return sorted(INDICATOR_SPECS.keys())


def ta_available() -> bool:
    """Return True if the local pandas_ta_classic library is importable."""
    return _TA_AVAILABLE
