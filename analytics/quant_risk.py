"""Quantitative risk analytics for NG Finance Pro and the MScFE research layer."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean_returns(returns: pd.Series) -> pd.Series:
    return pd.to_numeric(returns, errors="coerce").dropna()


def returns_from_prices(prices: pd.Series) -> pd.Series:
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    return clean.pct_change().dropna()


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float | None:
    clean = _clean_returns(returns)
    if len(clean) < 2:
        return None
    return float(clean.std(ddof=1) * np.sqrt(periods_per_year))


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float | None:
    """Historical VaR as a positive loss fraction using the empirical lower-tail order statistic."""
    clean = _clean_returns(returns)
    if clean.empty or not 0 < confidence < 1:
        return None
    losses = -clean.to_numpy()
    # Use the nearest-rank empirical quantile to avoid interpolation between observations.
    rank = max(1, int(np.ceil((1 - confidence) * len(losses))))
    return max(0.0, float(np.sort(losses)[-rank]))


def historical_expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float | None:
    clean = _clean_returns(returns)
    if clean.empty or not 0 < confidence < 1:
        return None
    var = historical_var(clean, confidence)
    if var is None:
        return None
    tail = clean[clean <= -var]
    return max(0.0, -float(tail.mean())) if not tail.empty else var


def _normal_z(confidence: float) -> float:
    z_table = {0.90: 1.2815515655, 0.95: 1.6448536269, 0.975: 1.9599639845, 0.99: 2.3263478746}
    if confidence in z_table:
        return z_table[confidence]
    grid = np.array(sorted(z_table))
    if confidence < grid[0] or confidence > grid[-1]:
        raise ValueError("confidence must be between 0.90 and 0.99 for interpolated normal quantiles")
    return float(np.interp(confidence, grid, np.array([z_table[x] for x in grid])))


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> float | None:
    clean = _clean_returns(returns)
    if len(clean) < 2 or not 0 < confidence < 1:
        return None
    try:
        z = _normal_z(confidence)
    except ValueError:
        return None
    mu = float(clean.mean())
    sigma = float(clean.std(ddof=1))
    return max(0.0, -(mu - z * sigma))


def parametric_expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float | None:
    clean = _clean_returns(returns)
    if len(clean) < 2 or not 0 < confidence < 1:
        return None
    try:
        z = _normal_z(confidence)
    except ValueError:
        return None
    sigma = float(clean.std(ddof=1))
    mu = float(clean.mean())
    pdf_z = np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)
    return max(0.0, -(mu - sigma * pdf_z / (1 - confidence)))


def monte_carlo_var(returns: pd.Series, confidence: float = 0.95, simulations: int = 10000, seed: int = 42) -> float | None:
    clean = _clean_returns(returns)
    if len(clean) < 2 or not 0 < confidence < 1 or simulations < 100:
        return None
    rng = np.random.default_rng(seed)
    simulated = rng.normal(float(clean.mean()), float(clean.std(ddof=1)), simulations)
    return max(0.0, -float(np.quantile(simulated, 1 - confidence)))


def monte_carlo_expected_shortfall(returns: pd.Series, confidence: float = 0.95, simulations: int = 10000, seed: int = 42) -> float | None:
    clean = _clean_returns(returns)
    if len(clean) < 2 or not 0 < confidence < 1 or simulations < 100:
        return None
    rng = np.random.default_rng(seed)
    simulated = rng.normal(float(clean.mean()), float(clean.std(ddof=1)), simulations)
    threshold = float(np.quantile(simulated, 1 - confidence))
    tail = simulated[simulated <= threshold]
    return max(0.0, -float(tail.mean())) if tail.size else max(0.0, -threshold)


def maximum_drawdown(prices: pd.Series) -> float | None:
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty:
        return None
    running_peak = clean.cummax()
    return max(0.0, -float((clean / running_peak - 1.0).min()))


def downside_volatility(returns: pd.Series, periods_per_year: int = 252) -> float | None:
    clean = _clean_returns(returns)
    if clean.empty:
        return None
    downside = np.minimum(clean.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(downside ** 2)) * np.sqrt(periods_per_year))


def stress_loss(returns: pd.Series, shock: float = -0.05) -> float | None:
    clean = _clean_returns(returns)
    if clean.empty:
        return None
    return max(0.0, -float(shock))


def worst_window_loss(returns: pd.Series, horizon: int = 5) -> float | None:
    """Worst compounded loss over rolling horizons."""
    clean = _clean_returns(returns)
    if clean.empty or horizon < 1 or len(clean) < horizon:
        return None
    compounded = (1.0 + clean).rolling(horizon).apply(np.prod, raw=True) - 1.0
    return max(0.0, -float(compounded.min()))


def risk_metrics(prices: pd.Series, confidence: float = 0.95) -> dict[str, float | int | None]:
    returns = returns_from_prices(prices)
    return {
        "observations": int(len(returns)),
        "annualized_volatility": annualized_volatility(returns),
        "historical_var": historical_var(returns, confidence),
        "expected_shortfall": historical_expected_shortfall(returns, confidence),
        "parametric_var": parametric_var(returns, confidence),
        "parametric_expected_shortfall": parametric_expected_shortfall(returns, confidence),
        "monte_carlo_var": monte_carlo_var(returns, confidence),
        "monte_carlo_expected_shortfall": monte_carlo_expected_shortfall(returns, confidence),
        "maximum_drawdown": maximum_drawdown(prices),
        "downside_volatility": downside_volatility(returns),
        "worst_5d_loss": worst_window_loss(returns, 5),
    }


def var_backtest(returns: pd.Series, confidence: float = 0.95, window: int = 252) -> dict[str, float | int | None]:
    clean = _clean_returns(returns).reset_index(drop=True)
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
    return pd.DataFrame([
        {"Model": "Historical", "VaR": historical_var(returns, confidence), "Expected Shortfall": historical_expected_shortfall(returns, confidence)},
        {"Model": "Parametric Normal", "VaR": parametric_var(returns, confidence), "Expected Shortfall": parametric_expected_shortfall(returns, confidence)},
        {"Model": "Monte Carlo Normal", "VaR": monte_carlo_var(returns, confidence, simulations), "Expected Shortfall": monte_carlo_expected_shortfall(returns, confidence, simulations)},
    ])


def risk_table(price_map: dict[str, pd.Series], confidence: float = 0.95) -> pd.DataFrame:
    rows = []
    for asset, prices in price_map.items():
        row = risk_metrics(prices, confidence)
        row["Asset"] = asset
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    columns = ["Asset", "observations", "annualized_volatility", "historical_var", "expected_shortfall", "parametric_var", "parametric_expected_shortfall", "monte_carlo_var", "monte_carlo_expected_shortfall", "maximum_drawdown", "downside_volatility", "worst_5d_loss"]
    return pd.DataFrame(rows)[columns]
