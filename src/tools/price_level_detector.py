"""
Price Level Detector — operates on 1-hour (H1) OHLCV candle data.

All public functions accept a DataFrame with columns: Open, High, Low, Close, Volume
and a DatetimeIndex (UTC preferred).  If a higher-frequency DataFrame is passed to
`detect_all_price_levels()`, it is resampled to 1H automatically before detection.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resample_to_1h(df: pd.DataFrame) -> pd.DataFrame:
    """Resample any OHLCV DataFrame to 1-hour candles."""
    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True)
    h1 = df.resample("1h").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna(subset=["Open"])
    return h1


def _infer_needs_resample(df: pd.DataFrame) -> bool:
    """Return True if median candle duration is shorter than 55 minutes."""
    if len(df) < 2:
        return False
    deltas = pd.to_datetime(df.index).to_series().diff().dropna()
    median_minutes = deltas.median().total_seconds() / 60
    return median_minutes < 55


# ── Liquidity Zone Detection ──────────────────────────────────────────────────

def detect_liquidity_zones(df: pd.DataFrame, lookback: int = 20) -> list[dict]:
    """
    Identify swing highs (supply zones) and swing lows (demand zones) on 1H candles.

    Logic:
    - Rolling window: find local maxima/minima using a window of `lookback` bars.
    - Rank by volume at that bar: high volume (top 30%) → 'high' strength,
      mid volume → 'medium', low volume → 'low'.

    Returns list of:
        {"type": "demand"|"supply", "price": float, "strength": "high"|"medium"|"low",
         "timestamp": str}
    """
    if len(df) < lookback + 2:
        return []

    zones: list[dict] = []
    vol_33 = df["Volume"].quantile(0.67) if "Volume" in df.columns else None
    vol_66 = df["Volume"].quantile(0.33) if "Volume" in df.columns else None

    highs = df["High"].values
    lows  = df["Low"].values
    vols  = df["Volume"].values if "Volume" in df.columns else np.ones(len(df))

    half = lookback // 2
    for i in range(half, len(df) - half):
        window_highs = highs[i - half: i + half + 1]
        window_lows  = lows[i  - half: i + half + 1]

        if vol_33 is not None:
            vol = vols[i]
            strength = "high" if vol >= vol_33 else ("medium" if vol >= vol_66 else "low")
        else:
            strength = "medium"

        # Supply zone: this bar's high is the highest in the window
        if highs[i] == window_highs.max() and highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            zones.append({
                "type": "supply",
                "price": float(highs[i]),
                "strength": strength,
                "timestamp": str(df.index[i]),
            })

        # Demand zone: this bar's low is the lowest in the window
        if lows[i] == window_lows.min() and lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            zones.append({
                "type": "demand",
                "price": float(lows[i]),
                "strength": strength,
                "timestamp": str(df.index[i]),
            })

    # Deduplicate zones that are within 0.05% of each other
    unique: list[dict] = []
    for z in zones:
        if not any(abs(z["price"] - u["price"]) / max(u["price"], 1) < 0.0005
                   and z["type"] == u["type"] for u in unique):
            unique.append(z)

    return unique


# ── FVG Detection ─────────────────────────────────────────────────────────────

def detect_fvg_zones(df: pd.DataFrame) -> list[dict]:
    """
    Fair Value Gap (FVG): 3-candle imbalance pattern on 1H candles.

    Bullish FVG: Low[i] > High[i-2]  (gap between candle 1 high and candle 3 low)
    Bearish FVG: High[i] < Low[i-2]

    Returns list of:
        {"type": "bullish"|"bearish", "low": float, "high": float, "timestamp": str}
    """
    fvg_zones: list[dict] = []

    for i in range(2, len(df)):
        if df["Low"].iloc[i] > df["High"].iloc[i - 2]:
            fvg_zones.append({
                "type": "bullish",
                "low": float(df["High"].iloc[i - 2]),
                "high": float(df["Low"].iloc[i]),
                "timestamp": str(df.index[i]),
            })
        elif df["High"].iloc[i] < df["Low"].iloc[i - 2]:
            fvg_zones.append({
                "type": "bearish",
                "low": float(df["High"].iloc[i]),
                "high": float(df["Low"].iloc[i - 2]),
                "timestamp": str(df.index[i]),
            })

    return fvg_zones


# ── Session Levels Detection ──────────────────────────────────────────────────

def detect_session_levels(df: pd.DataFrame) -> dict:
    """
    Compute OHLCM (open/high/low/close/mid) for each time period via resample.

    Periods:
    - us_open:    09:30–10:30 ET (14:30–15:30 UTC)
    - us_session: 09:30–16:00 ET (14:30–21:00 UTC)
    - day:        daily OHLC
    - week:       weekly OHLC
    - month:      monthly OHLC

    Mid = (High + Low) / 2

    Returns full session_levels dict.
    """

    def ohlcm(subset: pd.DataFrame) -> dict[str, float]:
        if subset.empty:
            return {"open": None, "high": None, "low": None, "close": None, "mid": None}
        o = float(subset["Open"].iloc[0])
        h = float(subset["High"].max())
        l = float(subset["Low"].min())
        c = float(subset["Close"].iloc[-1])
        return {"open": o, "high": h, "low": l, "close": c, "mid": round((h + l) / 2, 4)}

    idx = pd.to_datetime(df.index)

    # US Eastern offsets: UTC-5 (EST) / UTC-4 (EDT) — use UTC hours 14:30–15:30 as proxy
    us_open_mask = (
        ((idx.hour == 14) & (idx.minute >= 30)) |
        (idx.hour == 15) |
        ((idx.hour == 15) & (idx.minute <= 30))
    )
    us_session_mask = (
        ((idx.hour == 14) & (idx.minute >= 30)) |
        ((idx.hour >= 15) & (idx.hour < 21))
    )

    # Period resamples
    try:
        daily   = df.resample("D").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
        weekly  = df.resample("W").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
        monthly = df.resample("ME").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    except Exception:
        daily = weekly = monthly = pd.DataFrame()

    def last_period_ohlcm(period_df: pd.DataFrame) -> dict:
        if period_df.empty:
            return {"open": None, "high": None, "low": None, "close": None, "mid": None}
        row = period_df.iloc[-1]
        h, l = float(row["High"]), float(row["Low"])
        return {
            "open":  float(row["Open"]),
            "high":  h,
            "low":   l,
            "close": float(row["Close"]),
            "mid":   round((h + l) / 2, 4),
        }

    return {
        "us_open":    ohlcm(df[us_open_mask]),
        "us_session": ohlcm(df[us_session_mask]),
        "day":        last_period_ohlcm(daily),
        "week":       last_period_ohlcm(weekly),
        "month":      last_period_ohlcm(monthly),
    }


# ── Master Function ───────────────────────────────────────────────────────────

def detect_all_price_levels(df: pd.DataFrame, lookback: int | None = None) -> dict:
    """
    Master function: detects all price levels from OHLCV data.

    Accepts either a tick/M5/M1 DataFrame (auto-resampled to 1H) or a
    pre-resampled 1H DataFrame.  All detection runs on 1H candles.

    Args:
        df:       OHLCV DataFrame (any timeframe; auto-resampled to 1H).
        lookback: Number of 1H bars to use after resampling.
                  Defaults to CB.price_level_lookback (100 local / 500 colab).
                  Tail-slice keeps the most recent structure only, which is
                  sufficient for identifying active price levels.

    Returns:
        {
          "liquidity_zones": [...],
          "fvg_zones": [...],
          "session_levels": {...},
          "timeframe": "1H",
          "detected_at": "<ISO timestamp>",
          "candle_count": int,
        }
    """
    from datetime import datetime, timezone
    from src.config.computation_budget import budget as CB

    lb = lookback if lookback is not None else CB.price_level_lookback

    # Normalise column names (handle lowercase)
    rename = {}
    for col in df.columns:
        if col.lower() in ("open", "high", "low", "close", "volume"):
            rename[col] = col.capitalize()
    if rename:
        df = df.rename(columns=rename)

    # Resample to 1H if needed
    if _infer_needs_resample(df):
        df = _resample_to_1h(df)

    # Apply lookback window AFTER resampling — keeps only active recent structure
    if len(df) > lb:
        df = df.tail(lb)

    # Ensure Volume column exists
    if "Volume" not in df.columns:
        df = df.copy()
        df["Volume"] = 1.0

    liquidity_zones = detect_liquidity_zones(df)
    fvg_zones       = detect_fvg_zones(df)
    session_levels  = detect_session_levels(df)

    return {
        "liquidity_zones": liquidity_zones,
        "fvg_zones":       fvg_zones,
        "session_levels":  session_levels,
        "timeframe":       "1H",
        "detected_at":     datetime.now(timezone.utc).isoformat(),
        "candle_count":    len(df),
    }
