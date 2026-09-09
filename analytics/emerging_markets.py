"""Reproducible emerging-market research analytics for NG Finance Pro."""
from __future__ import annotations
import numpy as np
import pandas as pd


def clean_prices(prices: pd.Series) -> pd.Series:
    return pd.to_numeric(prices, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def returns_from_prices(prices: pd.Series) -> pd.Series:
    return clean_prices(prices).pct_change().dropna()


def rolling_volatility(returns: pd.Series, window: int = 21, periods_per_year: int = 252) -> pd.Series:
    return pd.to_numeric(returns, errors="coerce").rolling(window).std() * np.sqrt(periods_per_year)


def rolling_sharpe(returns: pd.Series, window: int = 63, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> pd.Series:
    clean = pd.to_numeric(returns, errors="coerce")
    excess = clean - risk_free_rate / periods_per_year
    mean = excess.rolling(window).mean() * periods_per_year
    vol = clean.rolling(window).std() * np.sqrt(periods_per_year)
    return mean.div(vol.replace(0, np.nan))


def regime_label(volatility: float | None, low_threshold: float = 0.20, high_threshold: float = 0.40) -> str:
    if volatility is None or pd.isna(volatility): return "Unknown"
    if volatility >= high_threshold: return "High volatility"
    if volatility >= low_threshold: return "Moderate volatility"
    return "Low volatility"


def comparative_statistics(price_map: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, prices in price_map.items():
        returns = returns_from_prices(prices)
        if len(returns) < 2: continue
        annual_return = float((1 + returns).prod() ** (252 / len(returns)) - 1)
        annual_vol = float(returns.std(ddof=1) * np.sqrt(252))
        downside = float(np.sqrt(np.mean(np.minimum(returns.to_numpy(), 0.0) ** 2)) * np.sqrt(252))
        wealth = (1 + returns).cumprod()
        max_dd = abs(float((wealth / wealth.cummax() - 1).min()))
        rows.append({"Asset": name, "Observations": len(returns), "Annual Return": annual_return, "Annual Volatility": annual_vol, "Downside Volatility": downside, "Maximum Drawdown": max_dd, "Volatility Regime": regime_label(annual_vol)})
    return pd.DataFrame(rows)


def rolling_correlation(price_map: dict[str, pd.Series], window: int = 63) -> pd.DataFrame:
    returns = pd.DataFrame({name: returns_from_prices(series) for name, series in price_map.items()}).dropna(how="any")
    if len(returns) < window: return pd.DataFrame()
    return returns.tail(window).corr()


def correlation_breakdown(price_map: dict[str, pd.Series], short_window: int = 21, long_window: int = 126) -> pd.DataFrame:
    returns = pd.DataFrame({name: returns_from_prices(series) for name, series in price_map.items()}).dropna(how="any")
    if len(returns) < long_window: return pd.DataFrame()
    short, long = returns.tail(short_window).corr(), returns.tail(long_window).corr()
    rows = []
    assets = list(returns.columns)
    for i, a in enumerate(assets):
        for b in assets[i + 1:]:
            s, l = float(short.loc[a, b]), float(long.loc[a, b])
            rows.append({"Asset A": a, "Asset B": b, "Short Corr": s, "Long Corr": l, "Correlation Change": s - l, "Breakdown Flag": abs(s - l) >= 0.30})
    return pd.DataFrame(rows).sort_values("Correlation Change", key=lambda s: s.abs(), ascending=False)


def stress_scenarios(returns: pd.Series, horizons: tuple[int, ...] = (1, 5, 21)) -> pd.DataFrame:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    rows = []
    for horizon in horizons:
        if len(clean) < horizon: continue
        cumulative = (1 + clean).rolling(horizon).apply(np.prod, raw=True) - 1
        rows.append({"Horizon (days)": horizon, "Worst Historical Return": float(cumulative.min()), "Scenario End": cumulative.idxmin()})
    return pd.DataFrame(rows)


def rolling_regime_series(returns: pd.Series, window: int = 63, low_threshold: float = 0.20, high_threshold: float = 0.40) -> pd.Series:
    return rolling_volatility(returns, window).map(lambda x: regime_label(x, low_threshold, high_threshold))
