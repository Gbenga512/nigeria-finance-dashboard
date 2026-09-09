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
