"""Simple, explainable factor analytics for NG Finance Pro research."""

from __future__ import annotations

import numpy as np
import pandas as pd


def factor_features(prices: pd.Series) -> pd.DataFrame:
    """Create non-look-ahead daily momentum, trend and volatility features."""
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty:
        return pd.DataFrame()
    returns = clean.pct_change()
    frame = pd.DataFrame(index=clean.index)
    frame["return_1d"] = returns
    frame["momentum_5d"] = clean.pct_change(5)
    frame["momentum_21d"] = clean.pct_change(21)
    frame["volatility_21d"] = returns.rolling(21).std(ddof=1) * np.sqrt(252)
    frame["trend_21d"] = clean / clean.rolling(21).mean() - 1
    return frame.dropna()


def factor_summary(prices: pd.Series) -> dict[str, float | int | None]:
    """Summarize the latest factor state for an asset."""
    features = factor_features(prices)
    if features.empty:
        return {"observations": 0, "momentum_5d": None, "momentum_21d": None, "volatility_21d": None, "trend_21d": None}
    latest = features.iloc[-1]
    return {
        "observations": int(len(features)),
        "momentum_5d": float(latest["momentum_5d"]),
        "momentum_21d": float(latest["momentum_21d"]),
        "volatility_21d": float(latest["volatility_21d"]),
        "trend_21d": float(latest["trend_21d"]),
    }


def factor_signal(prices: pd.Series) -> str:
    """Return a deliberately simple research label, not a trading recommendation."""
    summary = factor_summary(prices)
    if summary["observations"] == 0:
        return "Insufficient data"
    momentum = float(summary["momentum_21d"])
    trend = float(summary["trend_21d"])
    if momentum > 0 and trend > 0:
        return "Positive trend/momentum"
    if momentum < 0 and trend < 0:
        return "Negative trend/momentum"
    return "Mixed signal"
