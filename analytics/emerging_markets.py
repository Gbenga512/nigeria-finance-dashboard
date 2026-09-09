"""Emerging-market analytics for NG Finance Pro.

The module deliberately uses only data supplied by the caller. It never fabricates
Nigeria-specific observations, making the research workflow reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_volatility(returns: pd.Series, window: int = 21, periods_per_year: int = 252) -> pd.Series:
    """Annualized rolling volatility."""
    clean = pd.to_numeric(returns, errors="coerce")
    return clean.rolling(window).std() * np.sqrt(periods_per_year)


def rolling_sharpe(returns: pd.Series, window: int = 63, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> pd.Series:
    """Rolling annualized Sharpe ratio."""
    clean = pd.to_numeric(returns, errors="coerce")
    excess = clean - risk_free_rate / periods_per_year
    mean = excess.rolling(window).mean() * periods_per_year
    vol = clean.rolling(window).std() * np.sqrt(periods_per_year)
    return mean.div(vol.replace(0, np.nan))


def regime_label(volatility: float | None, low_threshold: float = 0.20, high_threshold: float = 0.40) -> str:
    """Classify a current annualized volatility observation."""
    if volatility is None or pd.isna(volatility):
        return "Unknown"
    if volatility >= high_threshold:
        return "High volatility"
    if volatility >= low_threshold:
        return "Moderate volatility"
    return "Low volatility"


def comparative_statistics(price_map: dict[str, pd.Series]) -> pd.DataFrame:
    """Create comparable return/risk statistics for supplied markets or assets."""
    rows = []
    for name, prices in price_map.items():
        clean = pd.to_numeric(prices, errors="coerce").dropna()
        returns = clean.pct_change().dropna()
        if returns.empty:
            continue
        annual_return = float((1 + returns).prod() ** (252 / len(returns)) - 1)
        annual_vol = float(returns.std(ddof=1) * np.sqrt(252)) if len(returns) > 1 else None
        downside = float(np.sqrt(np.mean(np.minimum(returns.to_numpy(), 0.0) ** 2)) * np.sqrt(252))
        wealth = (1 + returns).cumprod()
        max_dd = abs(float((wealth / wealth.cummax() - 1).min()))
        rows.append({
            "Asset": name,
            "Observations": len(returns),
            "Annual Return": annual_return,
            "Annual Volatility": annual_vol,
            "Downside Volatility": downside,
            "Maximum Drawdown": max_dd,
            "Volatility Regime": regime_label(annual_vol),
        })
    return pd.DataFrame(rows)


def stress_scenarios(returns: pd.Series, horizons: tuple[int, ...] = (1, 5, 21)) -> pd.DataFrame:
    """Calculate worst historical cumulative return over common stress horizons."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    rows = []
    for horizon in horizons:
        if len(clean) < horizon:
            continue
        cumulative = (1 + clean).rolling(horizon).apply(np.prod, raw=True) - 1
        worst = float(cumulative.min())
        end = cumulative.idxmin()
        rows.append({"Horizon (days)": horizon, "Worst Historical Return": worst, "Scenario End": end})
    return pd.DataFrame(rows)
