import pandas as pd
import pytest

from analytics.emerging_markets import comparative_statistics, regime_label, stress_scenarios


def test_regime_label():
    assert regime_label(0.10) == "Low volatility"
    assert regime_label(0.25) == "Moderate volatility"
    assert regime_label(0.50) == "High volatility"
    assert regime_label(None) == "Unknown"


def test_comparative_statistics():
    prices = {"A": pd.Series([100, 101, 99, 102, 103], dtype=float)}
    result = comparative_statistics(prices)
    assert len(result) == 1
    assert result.iloc[0]["Observations"] == 4
    assert result.iloc[0]["Maximum Drawdown"] >= 0


def test_stress_scenarios():
    returns = pd.Series([0.01, -0.02, -0.03, 0.01, 0.02], dtype=float)
    result = stress_scenarios(returns, horizons=(1, 2))
    assert set(result["Horizon (days)"]) == {1, 2}
    assert result["Worst Historical Return"].min() < 0
