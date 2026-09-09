import pandas as pd

from analytics.factors import factor_features, factor_signal


def test_factor_features_have_expected_columns():
    prices = pd.Series(range(1, 80), dtype=float)
    result = factor_features(prices)
    assert {"return_1d", "momentum_5d", "momentum_21d", "volatility_21d", "trend_21d"}.issubset(result.columns)
    assert not result.empty


def test_positive_trend_signal_is_detected():
    prices = pd.Series(range(1, 80), dtype=float)
    assert factor_signal(prices) == "Positive trend/momentum"
