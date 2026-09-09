"""Lightweight GARCH(1,1) conditional-volatility estimation.

Uses Gaussian quasi-maximum likelihood with scipy. Inputs are decimal returns
(e.g. 0.01 = 1%). The estimator is deliberately self-contained so the app
remains zero-cost and does not require a paid API or the arch package.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.optimize import minimize


def clean_returns(returns: pd.Series) -> pd.Series:
    x = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return x.astype(float)


def _neg_loglik(params: np.ndarray, x: np.ndarray) -> float:
    omega, alpha, beta = params
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.999999:
        return 1e100
    variance = np.empty(len(x), dtype=float)
    variance[0] = max(np.var(x), omega / max(1.0 - alpha - beta, 1e-8), 1e-12)
    for t in range(1, len(x)):
        variance[t] = omega + alpha * x[t - 1] ** 2 + beta * variance[t - 1]
        if not np.isfinite(variance[t]) or variance[t] <= 0:
            return 1e100
    return 0.5 * float(np.sum(np.log(2.0 * math.pi) + np.log(variance) + (x ** 2) / variance))


def fit_garch11(returns: pd.Series) -> dict:
    """Estimate GARCH(1,1) and return parameters, conditional volatility and forecast."""
    raw = clean_returns(returns)
    if len(raw) < 80 or raw.nunique() < 2:
        return {"success": False, "message": "At least 80 non-constant return observations are required."}

    scale = 100.0
    x = raw.to_numpy(dtype=float) * scale
    variance0 = max(float(np.var(x)), 1e-8)
    starts = [
        np.array([variance0 * 0.05, 0.08, 0.90]),
        np.array([variance0 * 0.02, 0.12, 0.85]),
        np.array([variance0 * 0.10, 0.05, 0.80]),
    ]
    bounds = [(1e-10, max(variance0 * 2.0, 1e-6)), (1e-8, 0.999), (1e-8, 0.999)]
    constraints = ({"type": "ineq", "fun": lambda p: 0.999999 - p[1] - p[2]},)
    best = None
    for start in starts:
        result = minimize(_neg_loglik, start, args=(x,), method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000, "ftol": 1e-10})
        if result.success and np.isfinite(result.fun) and (best is None or result.fun < best.fun):
            best = result
    if best is None:
        return {"success": False, "message": "GARCH optimizer did not converge on the supplied series."}

    omega, alpha, beta = map(float, best.x)
    variance = np.empty(len(x), dtype=float)
    variance[0] = max(np.var(x), omega / max(1.0 - alpha - beta, 1e-8), 1e-12)
    for t in range(1, len(x)):
        variance[t] = omega + alpha * x[t - 1] ** 2 + beta * variance[t - 1]
    conditional_vol = np.sqrt(variance) / scale
    forecast_variance = omega + alpha * x[-1] ** 2 + beta * variance[-1]
    persistence = alpha + beta
    half_life = float(math.log(0.5) / math.log(persistence)) if 0 < persistence < 1 else np.inf
    n = len(x)
    k = 3
    ll = -float(best.fun)
    aic = 2 * k - 2 * ll
    bic = k * math.log(n) - 2 * ll
    std_resid = (x - np.mean(x)) / np.sqrt(variance)

    return {
        "success": True,
        "message": "GARCH(1,1) estimated by Gaussian quasi-maximum likelihood.",
        "omega": omega / scale**2,
        "alpha": alpha,
        "beta": beta,
        "persistence": persistence,
        "half_life": half_life,
        "loglikelihood": ll,
        "aic": aic,
        "bic": bic,
        "latest_volatility": float(conditional_vol[-1]),
        "forecast_volatility": float(math.sqrt(max(forecast_variance, 1e-12)) / scale),
        "conditional_volatility": pd.Series(conditional_vol, index=raw.index, name="GARCH Volatility"),
        "standardized_residuals": pd.Series(std_resid, index=raw.index, name="Standardized Residual"),
    }


def ewma_volatility(returns: pd.Series, lam: float = 0.94) -> pd.Series:
    """Return annualized EWMA volatility for comparison with GARCH."""
    x = clean_returns(returns)
    if x.empty:
        return pd.Series(dtype=float)
    var = np.empty(len(x), dtype=float)
    var[0] = max(float(x.var()), 1e-12)
    for i in range(1, len(x)):
        var[i] = lam * var[i - 1] + (1.0 - lam) * x.iloc[i - 1] ** 2
    return pd.Series(np.sqrt(var) * np.sqrt(252), index=x.index, name="EWMA Volatility")
