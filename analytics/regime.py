"""Market regime detection utilities for NG Finance Pro."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_volatility(returns: pd.Series, window: int = 21, periods_per_year: int = 252) -> pd.Series:
    """Annualized rolling volatility from daily returns."""
    clean = pd.to_numeric(returns, errors="coerce")
    return clean.rolling(window).std(ddof=1) * np.sqrt(periods_per_year)


def rolling_correlation(returns: pd.DataFrame, asset_a: str, asset_b: str, window: int = 60) -> pd.Series:
    """Rolling Pearson correlation between two return series."""
    if asset_a not in returns.columns or asset_b not in returns.columns:
        return pd.Series(dtype="float64")
    return returns[asset_a].rolling(window).corr(returns[asset_b])


def classify_volatility_regime(volatility: pd.Series, low_quantile: float = 0.33, high_quantile: float = 0.67) -> pd.Series:
    """Classify observations into low, normal and high volatility regimes."""
    clean = pd.to_numeric(volatility, errors="coerce")
    valid = clean.dropna()
    if valid.empty:
        return pd.Series(index=volatility.index, dtype="object")
    low = float(valid.quantile(low_quantile))
    high = float(valid.quantile(high_quantile))
    return pd.Series(
        np.select([clean <= low, clean >= high], ["Low volatility", "High volatility"], default="Normal volatility"),
        index=volatility.index,
        dtype="object",
    )


def regime_summary(returns: pd.Series, window: int = 21) -> pd.DataFrame:
    """Summarize observations and average volatility by detected regime."""
    vol = rolling_volatility(returns, window)
    regime = classify_volatility_regime(vol)
    data = pd.DataFrame({"Volatility": vol, "Regime": regime}).dropna(subset=["Volatility"])
    if data.empty:
        return pd.DataFrame(columns=["Regime", "Observations", "Average Volatility"])
    return (
        data.groupby("Regime", as_index=False)
        .agg(Observations=("Volatility", "size"), **{"Average Volatility": ("Volatility", "mean")})
        .sort_values("Average Volatility")
    )
