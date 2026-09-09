"""Liquidity and FX risk analytics for Nigerian finance workflows."""
from __future__ import annotations

import numpy as np
import pandas as pd


def fx_returns(prices: pd.Series) -> pd.Series:
    x = pd.to_numeric(prices, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return x.pct_change().dropna()


def fx_risk_metrics(prices: pd.Series, window: int = 21, periods_per_year: int = 252) -> dict:
    returns = fx_returns(prices)
    if len(returns) < 2:
        return {"observations": len(returns), "annualized_volatility": None, "rolling_volatility": pd.Series(dtype=float), "worst_day": None, "max_drawdown": None}
    rolling = returns.rolling(window).std() * np.sqrt(periods_per_year) if len(returns) >= window else pd.Series(dtype=float)
    wealth = (1 + returns).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    return {
        "observations": len(returns),
        "annualized_volatility": float(returns.std(ddof=1) * np.sqrt(periods_per_year)),
        "rolling_volatility": rolling.dropna(),
        "worst_day": float(returns.min()),
        "max_drawdown": float(drawdown.min()),
    }


def liquidity_metrics(cash: float, daily_outflow: float, near_term_liabilities: float = 0.0, liquid_assets: float | None = None) -> dict:
    available = max(float(cash), 0.0) if liquid_assets is None else max(float(liquid_assets), 0.0)
    runway = available / daily_outflow if daily_outflow > 0 else np.inf
    coverage = available / near_term_liabilities if near_term_liabilities > 0 else np.inf
    return {"liquid_assets": available, "daily_outflow": max(float(daily_outflow), 0.0), "runway_days": float(runway), "liquidity_coverage": float(coverage)}


def fx_exposure_stress(fx_exposure: float, shocks: tuple[float, ...] = (-0.02, -0.05, -0.10)) -> pd.DataFrame:
    """Estimate Naira impact from adverse FX moves on a foreign-currency exposure."""
    exposure = float(fx_exposure)
    rows = []
    for shock in shocks:
        rows.append({"FX Shock": shock, "Naira Impact": exposure * shock, "Absolute Impact": abs(exposure * shock)})
    return pd.DataFrame(rows)


def liquidity_stress(cash: float, daily_outflow: float, outflow_multipliers: tuple[float, ...] = (1.25, 1.50, 2.00), cash_haircut: float = 0.10) -> pd.DataFrame:
    """Stress runway under higher outflows and a haircut to liquid cash."""
    stressed_cash = max(float(cash), 0.0) * (1.0 - cash_haircut)
    rows = []
    for multiplier in outflow_multipliers:
        stressed_outflow = max(float(daily_outflow), 0.0) * multiplier
        runway = stressed_cash / stressed_outflow if stressed_outflow else np.inf
        rows.append({"Outflow Multiplier": multiplier, "Stressed Cash": stressed_cash, "Daily Outflow": stressed_outflow, "Runway Days": runway})
    return pd.DataFrame(rows)


def risk_signal(fx_volatility: float | None, runway_days: float | None) -> tuple[str, list[str]]:
    alerts = []
    if fx_volatility is not None:
        if fx_volatility >= 0.40:
            alerts.append("High FX volatility")
        elif fx_volatility >= 0.20:
            alerts.append("Elevated FX volatility")
    if runway_days is not None and np.isfinite(runway_days):
        if runway_days < 15:
            alerts.append("Critical liquidity runway")
        elif runway_days < 30:
            alerts.append("Tight liquidity runway")
    if any("High" in a or "Critical" in a for a in alerts):
        return "High attention", alerts
    if alerts:
        return "Elevated", alerts
    return "Normal", alerts
