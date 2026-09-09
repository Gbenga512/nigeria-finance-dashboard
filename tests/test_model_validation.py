import numpy as np
import pandas as pd
import pytest

from analytics.model_validation import (
    bootstrap_exception_rate_ci,
    christoffersen_independence_test,
    conditional_coverage_test,
    kupiec_pof_test,
    validate_var_model,
    var_exception_series,
)


def synthetic_returns(seed=42, n=700):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0002, 0.01, n))


def test_exception_series_is_binary_and_oos():
    series = var_exception_series(synthetic_returns(), 0.95, 252)
    assert len(series) == 448
    assert set(series.unique()).issubset({0, 1})


def test_kupiec_returns_valid_statistics():
    result = kupiec_pof_test(synthetic_returns(), 0.95, 252)
    assert result["observations"] == 448
    assert 0 <= result["p_value"] <= 1
    assert result["lr_stat"] >= 0


def test_christoffersen_returns_transition_counts():
    result = christoffersen_independence_test(synthetic_returns(), 0.95, 252)
    assert result["n00"] + result["n01"] + result["n10"] + result["n11"] == 447
    assert 0 <= result["p_value"] <= 1


def test_conditional_coverage_uses_two_degree_of_freedom_pvalue():
    result = conditional_coverage_test(synthetic_returns(), 0.95, 252)
    assert result["conditional_coverage_lr"] >= 0
    assert 0 <= result["conditional_coverage_p_value"] <= 1


def test_bootstrap_interval_contains_point_estimate():
    result = bootstrap_exception_rate_ci(synthetic_returns(), 0.95, 252, 500, 42)
    assert result["ci_lower"] <= result["exception_rate"] <= result["ci_upper"]
    assert result["bootstrap_samples"] == 500


def test_validation_suite_is_reproducible():
    returns = synthetic_returns()
    first = validate_var_model(returns, 0.95, 252, 500)
    second = validate_var_model(returns, 0.95, 252, 500)
    assert first == second


def test_validation_handles_insufficient_history():
    result = validate_var_model(pd.Series([0.01, -0.01, 0.02]), 0.95, 10, 500)
    assert result["kupiec"]["p_value"] is None
    assert result["bootstrap"]["ci_lower"] is None
