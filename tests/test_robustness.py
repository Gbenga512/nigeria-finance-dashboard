import numpy as np
import pandas as pd

from analytics.robustness import bootstrap_metric_ci, model_sensitivity, rolling_var_stability, robustness_summary


def synthetic_returns(seed=42, n=700):
    return pd.Series(np.random.default_rng(seed).normal(0.0002, 0.01, n))


def test_model_sensitivity_covers_three_models_and_confidences():
    result = model_sensitivity(synthetic_returns(), confidences=(0.90, 0.95))
    assert len(result) == 6
    assert set(result["Model"]) == {"Historical", "Parametric Normal", "Monte Carlo Normal"}


def test_rolling_var_stability_respects_available_windows():
    result = rolling_var_stability(synthetic_returns(), 0.95, windows=(60, 120, 1000))
    assert result["Window"].tolist() == [60, 120]
    assert result["VaR"].notna().all()


def test_bootstrap_metric_ci_is_reproducible_and_contains_estimate():
    returns = synthetic_returns()
    first = bootstrap_metric_ci(returns, 0.95, "VaR", 200, 42)
    second = bootstrap_metric_ci(returns, 0.95, "VaR", 200, 42)
    assert first == second
    assert first["ci_lower"] <= first["estimate"] <= first["ci_upper"]


def test_robustness_summary_has_nonnegative_model_disagreement():
    summary = robustness_summary(synthetic_returns(), 0.95)
    assert summary["var_range"] >= 0
    assert summary["es_range"] >= 0
