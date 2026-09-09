"""Quantitative risk analytics for NG Finance Pro and the MScFE research layer."""

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
    return max(0.0, -float(clean.quantile(1 - confidence)))


def historical_expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Historical Expected Shortfall: mean loss in the tail beyond VaR."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty or not 0 < confidence < 1:
        return None
    threshold = float(clean.quantile(1 - confidence))
    tail = clean[clean <= threshold]
    return max(0.0, -float(tail.mean())) if not tail.empty else max(0.0, -threshold)


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Normal/parametric VaR using sample mean and standard deviation."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2 or not 0 < confidence < 1:
        return None
    # Standard normal quantiles for common confidence levels; linear interpolation otherwise.
    z_table = {0.90: 1.2815515655, 0.95: 1.6448536269, 0.975: 1.9599639845, 0.99: 2.3263478746}
    if confidence in z_table:
        z = z_table[confidence]
    else:
        grid = np.array(sorted(z_table))
        vals = np.array([z_table[x] for x in grid])
        z = float(np.interp(confidence, grid, vals))
    mu = float(clean.mean())
    sigma = float(clean.std(ddof=1))
    return max(0.0, -(mu - z * sigma))


def parametric_expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Normal-distribution Expected Shortfall."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2 or not 0 < confidence < 1:
        return None
    z_table = {0.90: 1.2815515655, 0.95: 1.6448536269, 0.975: 1.9599639845, 0.99: 2.3263478746}
    if confidence not in z_table:
        grid = np.array(sorted(z_table))
        z = float(np.interp(confidence, grid, np.array([z_table[x] for x in grid])))
    else:
        z = z_table[confidence]
    sigma = float(clean.std(ddof=1))
    mu = float(clean.mean())
    pdf_z = np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)
    return max(0.0, -(mu - sigma * pdf_z / (1 - confidence)))


def monte_carlo_var(returns: pd.Series, confidence: float = 0.95, simulations: int = 10000, seed: int = 42) -> float | None:
    """Monte Carlo VaR using a normal model calibrated to observed returns."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2 or not 0 < confidence < 1 or simulations < 100:
        return None
    rng = np.random.default_rng(seed)
    simulated = rng.normal(float(clean.mean()), float(clean.std(ddof=1)), simulations)
    return max(0.0, -float(np.quantile(simulated, 1 - confidence)))


def maximum_drawdown(prices: pd.Series) -> float | None:
    """Maximum peak-to-trough drawdown as a positive fraction."""
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty:
        return None
    running_peak = clean.cummax()
    return max(0.0, -float((clean / running_peak - 1.0).min()))


def downside_volatility(returns: pd.Series, periods_per_year: int = 252) -> float | None:
    """Annualized downside deviation using zero as the target return."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return None
    downside = np.minimum(clean.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(downside ** 2)) * np.sqrt(periods_per_year))


def stress_loss(returns: pd.Series, shock: float = -0.05) -> float | None:
    """Loss implied by a deterministic one-period shock."""
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
        "parametric_var": parametric_var(returns, confidence),
        "parametric_expected_shortfall": parametric_expected_shortfall(returns, confidence),
        "monte_carlo_var": monte_carlo_var(returns, confidence),
        "maximum_drawdown": maximum_drawdown(prices),
        "downside_volatility": downside_volatility(returns),
    }


def var_backtest(returns: pd.Series, confidence: float = 0.95, window: int = 252) -> dict[str, float | int | None]:
    """Rolling historical VaR backtest with exception count and rate."""
    clean = pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)
    if len(clean) <= window or not 0 < confidence < 1:
        return {"observations": 0, "exceptions": 0, "exception_rate": None, "expected_rate": 1 - confidence}
    exceptions = 0
    forecasts = 0
    for i in range(window, len(clean)):
        var = historical_var(clean.iloc[i-window:i], confidence)
        if var is not None and float(clean.iloc[i]) < -var:
            exceptions += 1
        forecasts += 1
    return {"observations": forecasts, "exceptions": exceptions, "exception_rate": exceptions / forecasts, "expected_rate": 1 - confidence}


def risk_model_comparison(returns: pd.Series, confidence: float = 0.95, simulations: int = 10000) -> pd.DataFrame:
    """Compare historical, parametric and Monte Carlo VaR/ES estimates."""
    rows = [
        {"Model": "Historical", "VaR": historical_var(returns, confidence), "Expected Shortfall": historical_expected_shortfall(returns, confidence)},
        {"Model": "Parametric Normal", "VaR": parametric_var(returns, confidence), "Expected Shortfall": parametric_expected_shortfall(returns, confidence)},
        {"Model": "Monte Carlo Normal", "VaR": monte_carlo_var(returns, confidence, simulations), "Expected Shortfall": None},
    ]
    return pd.DataFrame(rows)


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
        "expected_shortfall", "parametric_var", "parametric_expected_shortfall",
        "monte_carlo_var", "maximum_drawdown", "downside_volatility",
    ]
    return pd.DataFrame(rows)[columns]
