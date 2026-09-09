"""Quantitative risk analytics used by NG Finance Pro and the MScFE research layer."""

from __future__ import annotations

import numpy as np
import pandas as pd


def returns_from_prices(prices: pd.Series) -> pd.Series:
    """Compute simple percentage returns from a price series."""
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    return clean.pct_change().dropna()


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float | None:
    """Annualized standard deviation of returns."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2:
        return None
    return float(clean.std(ddof=1) * np.sqrt(periods_per_year))


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Historical VaR reported as a positive loss fraction."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty or not 0 < confidence < 1:
        return None
    quantile = float(clean.quantile(1 - confidence))
    return max(0.0, -quantile)


def historical_expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Historical Expected Shortfall (average loss beyond the VaR threshold)."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty or not 0 < confidence < 1:
        return None
    threshold = float(clean.quantile(1 - confidence))
    tail = clean[clean <= threshold]
    if tail.empty:
        return max(0.0, -threshold)
    return max(0.0, -float(tail.mean()))


def maximum_drawdown(prices: pd.Series) -> float | None:
    """Maximum peak-to-trough drawdown as a positive fraction."""
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty:
        return None
    running_peak = clean.cummax()
    drawdown = clean / running_peak - 1.0
    return max(0.0, -float(drawdown.min()))


def downside_volatility(returns: pd.Series, periods_per_year: int = 252) -> float | None:
    """Annualized downside deviation using zero as the target return."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return None
    downside = np.minimum(clean.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(downside ** 2)) * np.sqrt(periods_per_year))


def stress_loss(returns: pd.Series, shock: float = -0.05) -> float | None:
    """Apply a deterministic one-period market shock."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return None
    return max(0.0, -float(shock))


def risk_metrics(prices: pd.Series, confidence: float = 0.95) -> dict[str, float | int | None]:
    """Return a reproducible risk-metric bundle for one asset."""
    returns = returns_from_prices(prices)
    return {
        "observations": int(len(returns)),
        "annualized_volatility": annualized_volatility(returns),
        "historical_var": historical_var(returns, confidence),
        "expected_shortfall": historical_expected_shortfall(returns, confidence),
        "maximum_drawdown": maximum_drawdown(prices),
        "downside_volatility": downside_volatility(returns),
    }


def risk_table(price_map: dict[str, pd.Series], confidence: float = 0.95) -> pd.DataFrame:
    """Build a cross-asset risk table from named price series."""
    rows = []
    for asset, prices in price_map.items():
        row = risk_metrics(prices, confidence)
        row["Asset"] = asset
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    columns = [
        "Asset", "observations", "annualized_volatility", "historical_var",
        "expected_shortfall", "maximum_drawdown", "downside_volatility",
    ]
    return pd.DataFrame(rows)[columns]
