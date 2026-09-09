"""Reproducible research utilities for NG Finance Pro."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.quant_risk import (
    annualized_volatility,
    historical_expected_shortfall,
    historical_var,
    maximum_drawdown,
    monte_carlo_expected_shortfall,
    monte_carlo_var,
    returns_from_prices,
    var_backtest,
    worst_window_loss,
)


def research_metrics(prices: pd.Series, confidence: float = 0.95, backtest_window: int = 252) -> dict:
    """Create a compact research-results record for one price series."""
    returns = returns_from_prices(prices)
    backtest = var_backtest(returns, confidence, backtest_window)
    return {
        "observations": int(len(returns)),
        "annualized_volatility": annualized_volatility(returns),
        "historical_var": historical_var(returns, confidence),
        "historical_es": historical_expected_shortfall(returns, confidence),
        "monte_carlo_var": monte_carlo_var(returns, confidence),
        "monte_carlo_es": monte_carlo_expected_shortfall(returns, confidence),
        "maximum_drawdown": maximum_drawdown(prices),
        "worst_5d_loss": worst_window_loss(returns, 5),
        "var_exception_rate": backtest["exception_rate"],
        "expected_exception_rate": backtest["expected_rate"],
        "var_exceptions": backtest["exceptions"],
        "backtest_observations": backtest["observations"],
    }


def run_research_experiment(price_map: dict[str, pd.Series], confidence: float = 0.95, backtest_window: int = 252) -> pd.DataFrame:
    """Run the same methodology across all supplied assets."""
    rows = []
    for asset, prices in price_map.items():
        result = research_metrics(prices, confidence, backtest_window)
        result["Asset"] = asset
        rows.append(result)
    if not rows:
        return pd.DataFrame()
    columns = ["Asset", "observations", "annualized_volatility", "historical_var", "historical_es", "monte_carlo_var", "monte_carlo_es", "maximum_drawdown", "worst_5d_loss", "var_exception_rate", "expected_exception_rate", "var_exceptions", "backtest_observations"]
    return pd.DataFrame(rows)[columns]


def scenario_loss(prices: pd.Series, shock: float = -0.05) -> float | None:
    """Estimate one-period percentage loss under an explicit price shock."""
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty or shock > 0:
        return None
    return max(0.0, -float(shock))


def scenario_matrix(price_map: dict[str, pd.Series], shocks: list[float]) -> pd.DataFrame:
    """Apply common one-period downside scenarios to each asset for sensitivity analysis."""
    rows = []
    for asset, prices in price_map.items():
        for shock in shocks:
            loss = scenario_loss(prices, shock)
            rows.append({"Asset": asset, "Shock": shock, "Scenario Loss": loss})
    return pd.DataFrame(rows)


def rolling_volatility(prices: pd.Series, window: int = 21, periods_per_year: int = 252) -> pd.Series:
    """Compute annualized rolling volatility from daily simple returns."""
    returns = returns_from_prices(prices)
    if window < 2:
        return pd.Series(dtype="float64")
    return returns.rolling(window).std(ddof=1) * np.sqrt(periods_per_year)


def research_summary(results: pd.DataFrame, confidence: float) -> str:
    if results.empty:
        return "No research result is available because no valid historical dataset was supplied."
    highest_vol = results.loc[results["annualized_volatility"].idxmax(), "Asset"]
    highest_dd = results.loc[results["maximum_drawdown"].idxmax(), "Asset"]
    return (
        f"Experiment completed at {confidence:.1%} confidence across {len(results)} assets. "
        f"Highest annualized volatility: {highest_vol}. Highest maximum drawdown: {highest_dd}. "
        "Use the exception rate and model outputs for formal model validation; results are descriptive and not investment advice."
    )


def methodology_record(confidence: float, lookback: str, backtest_window: int) -> dict:
    return {
        "lookback": lookback,
        "confidence": confidence,
        "backtest_window": backtest_window,
        "return_definition": "Daily simple percentage returns",
        "annualization": "252 trading days",
        "historical_model": "Empirical lower-tail VaR and Expected Shortfall",
        "monte_carlo_model": "Normal simulation calibrated to sample mean and volatility",
        "scenario_analysis": "Explicit one-period downside price shocks",
        "rolling_volatility": "21-trading-day rolling standard deviation annualized by sqrt(252)",
        "reproducibility_seed": 42,
        "risk_free_rate": "0% for current risk-adjusted ratios",
    }
