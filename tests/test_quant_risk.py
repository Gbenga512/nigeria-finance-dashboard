import pandas as pd
import pytest

from analytics.quant_risk import (
    annualized_volatility,
    historical_expected_shortfall,
    historical_var,
    maximum_drawdown,
    returns_from_prices,
)


def test_returns_from_prices():
    prices = pd.Series([100.0, 110.0, 99.0])
    returns = returns_from_prices(prices)
    assert len(returns) == 2
    assert returns.iloc[0] == pytest.approx(0.10)
    assert returns.iloc[1] == pytest.approx(-0.10)


def test_historical_var_is_positive_loss():
    returns = pd.Series([-0.10, -0.05, -0.02, 0.01, 0.03])
    assert historical_var(returns, 0.80) == pytest.approx(0.05)


def test_expected_shortfall_is_not_below_var():
    returns = pd.Series([-0.10, -0.05, -0.02, 0.01, 0.03])
    var = historical_var(returns, 0.80)
    es = historical_expected_shortfall(returns, 0.80)
    assert es >= var


def test_maximum_drawdown():
    prices = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert maximum_drawdown(prices) == pytest.approx(0.25)


def test_annualized_volatility_requires_two_observations():
    assert annualized_volatility(pd.Series([0.01])) is None
