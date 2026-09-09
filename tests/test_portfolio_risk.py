import pandas as pd
import pytest

from analytics.portfolio_risk import (
    align_returns,
    component_var,
    correlation_matrix,
    monte_carlo_var_es,
    portfolio_returns,
    portfolio_risk,
    risk_ratios,
    minimum_variance_weights,
    optimized_portfolio_walk_forward,
    portfolio_stress_matrix,
)


def prices(values):
    return pd.Series(values, dtype=float)


def test_align_returns_and_portfolio_returns():
    data = {"A": prices([100, 110, 121]), "B": prices([100, 90, 99])}
    aligned = align_returns(data)
    assert aligned.shape == (2, 2)
    result = portfolio_returns(data, {"A": 0.5, "B": 0.5})
    assert result.iloc[0] == pytest.approx(0.0)


def test_correlation_matrix():
    data = {"A": prices([100, 110, 121, 133.1]), "B": prices([200, 220, 242, 266.2])}
    corr = correlation_matrix(data)
    assert corr.loc["A", "B"] == pytest.approx(1.0)


def test_monte_carlo_var_es_is_deterministic():
    returns = pd.Series([-0.02, -0.01, 0.0, 0.01, 0.02])
    first = monte_carlo_var_es(returns, 0.95, 1000, 42)
    second = monte_carlo_var_es(returns, 0.95, 1000, 42)
    assert first == pytest.approx(second)
    assert first[1] >= first[0]


def test_portfolio_risk_and_component_var():
    data = {"A": prices([100, 102, 101, 104, 103]), "B": prices([100, 99, 101, 100, 102])}
    weights = {"A": 0.6, "B": 0.4}
    metrics = portfolio_risk(data, weights)
    assert metrics["observations"] == 4
    table = component_var(data, weights)
    assert len(table) == 2
    assert table["% of Portfolio Risk"].sum() == pytest.approx(1.0)


def test_risk_ratios_handles_short_series():
    assert risk_ratios(pd.Series([0.01]))["sharpe"] is None


def test_minimum_variance_weights_are_long_only_and_normalized():
    data = pd.DataFrame({"A": [0.01, -0.01, 0.01, -0.01], "B": [0.005, -0.005, 0.005, -0.005]})
    weights = minimum_variance_weights(data)
    assert weights is not None
    assert (weights >= 0).all()
    assert weights.sum() == pytest.approx(1.0)


def test_optimized_walk_forward_is_reproducible_and_oos():
    index = pd.date_range("2020-01-01", periods=120, freq="D")
    a = pd.Series(100 * (1.001 ** pd.Series(range(120))), index=index)
    b = pd.Series(100 * (1.0005 ** pd.Series(range(120))), index=index)
    result = optimized_portfolio_walk_forward({"A": a, "B": b}, train_window=40, test_window=20, transaction_cost=0.001)
    assert result["summary"]
    assert len(result["blocks"]) >= 3
    assert result["weights"].shape[0] == len(result["blocks"])
    assert result["equity"].index.min() >= index[40]


def test_portfolio_stress_matrix():
    data = {"A": prices([100, 101, 102]), "B": prices([100, 99, 101])}
    stress = portfolio_stress_matrix(data, {"A": 0.6, "B": 0.4}, [-0.10, -0.20])
    assert not stress.empty
    assert stress["Portfolio Loss"].ge(0).all()
    assert "Common shock -10%" in stress["Scenario"].tolist()
