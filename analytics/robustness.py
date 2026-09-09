"""Robustness and sensitivity analysis for quantitative risk models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.quant_risk import (
    historical_expected_shortfall,
    historical_var,
    monte_carlo_expected_shortfall,
    monte_carlo_var,
    parametric_expected_shortfall,
    parametric_var,
)


def model_sensitivity(returns: pd.Series, confidences=(0.90, 0.95, 0.975, 0.99), simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    """Compare VaR/ES models across confidence levels."""
    rows = []
    for confidence in confidences:
        rows.extend([
            {"Confidence": confidence, "Model": "Historical", "VaR": historical_var(returns, confidence), "Expected Shortfall": historical_expected_shortfall(returns, confidence)},
            {"Confidence": confidence, "Model": "Parametric Normal", "VaR": parametric_var(returns, confidence), "Expected Shortfall": parametric_expected_shortfall(returns, confidence)},
            {"Confidence": confidence, "Model": "Monte Carlo Normal", "VaR": monte_carlo_var(returns, confidence, simulations, seed), "Expected Shortfall": monte_carlo_expected_shortfall(returns, confidence, simulations, seed)},
        ])
    return pd.DataFrame(rows)


def rolling_var_stability(returns: pd.Series, confidence: float = 0.95, windows=(60, 120, 252, 504)) -> pd.DataFrame:
    """Measure historical VaR sensitivity to the estimation window."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    rows = []
    for window in windows:
        if len(clean) < window:
            continue
        value = historical_var(clean.tail(window), confidence)
        rows.append({"Window": window, "VaR": value})
    return pd.DataFrame(rows)


def bootstrap_metric_ci(returns: pd.Series, confidence: float = 0.95, metric: str = "VaR", samples: int = 1000, seed: int = 42) -> dict:
    """Estimate a percentile bootstrap interval for a risk metric."""
    clean = pd.to_numeric(returns, errors="coerce").dropna().to_numpy()
    if len(clean) < 20 or samples < 100:
        return {"metric": metric, "estimate": None, "ci_lower": None, "ci_upper": None, "samples": samples}
    fn = historical_var if metric == "VaR" else historical_expected_shortfall
    estimate = fn(pd.Series(clean), confidence)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(samples):
        sample = rng.choice(clean, size=len(clean), replace=True)
        value = fn(pd.Series(sample), confidence)
        if value is not None:
            values.append(value)
    if not values or estimate is None:
        return {"metric": metric, "estimate": estimate, "ci_lower": None, "ci_upper": None, "samples": samples}
    return {"metric": metric, "estimate": float(estimate), "ci_lower": float(np.quantile(values, 0.025)), "ci_upper": float(np.quantile(values, 0.975)), "samples": samples}


def robustness_summary(returns: pd.Series, confidence: float = 0.95) -> dict:
    """Summarize cross-model disagreement as a model-risk diagnostic."""
    comparison = model_sensitivity(returns, confidences=(confidence,))
    valid = comparison.dropna(subset=["VaR", "Expected Shortfall"])
    if valid.empty:
        return {"var_range": None, "es_range": None, "var_mean": None, "es_mean": None}
    return {
        "var_range": float(valid["VaR"].max() - valid["VaR"].min()),
        "es_range": float(valid["Expected Shortfall"].max() - valid["Expected Shortfall"].min()),
        "var_mean": float(valid["VaR"].mean()),
        "es_mean": float(valid["Expected Shortfall"].mean()),
    }
