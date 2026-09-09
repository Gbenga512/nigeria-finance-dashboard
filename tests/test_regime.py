import numpy as np
import pandas as pd

from analytics.regime import classify_volatility_regime, rolling_correlation, rolling_volatility, regime_summary


def test_rolling_volatility_is_annualized():
    returns = pd.Series([0.01] * 30)
    result = rolling_volatility(returns, 5)
    assert result.iloc[-1] == 0.0


def test_rolling_correlation_tracks_relationship():
    base = pd.Series(np.arange(20, dtype=float))
    returns = pd.DataFrame({"A": base, "B": base * 2})
    result = rolling_correlation(returns, "A", "B", 5).dropna()
    assert np.allclose(result.to_numpy(), 1.0)


def test_regime_classifier_has_three_categories():
    volatility = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06])
    result = classify_volatility_regime(volatility)
    assert set(result.dropna()) == {"Low volatility", "Normal volatility", "High volatility"}


def test_regime_summary_contains_observations():
    returns = pd.Series(np.linspace(-0.02, 0.02, 40))
    result = regime_summary(returns, 5)
    assert "Observations" in result.columns
    assert result["Observations"].sum() == 36
