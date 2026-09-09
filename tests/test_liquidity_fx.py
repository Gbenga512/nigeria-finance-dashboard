import pandas as pd
import pytest

from analytics.liquidity_fx import fx_exposure_stress, fx_risk_metrics, liquidity_metrics, liquidity_stress, risk_signal


def test_fx_risk_metrics():
    prices = pd.Series([100, 101, 99, 102, 100, 103] * 20)
    result = fx_risk_metrics(prices, window=5)
    assert result["observations"] == len(prices) - 1
    assert result["annualized_volatility"] > 0
    assert len(result["rolling_volatility"]) > 0


def test_liquidity_metrics():
    result = liquidity_metrics(100_000_000, 5_000_000, 50_000_000)
    assert result["runway_days"] == pytest.approx(20)
    assert result["liquidity_coverage"] == pytest.approx(2)


def test_fx_stress_scales_with_exposure():
    result = fx_exposure_stress(100_000_000)
    assert result.iloc[0]["Naira Impact"] == pytest.approx(-2_000_000)
    assert result.iloc[-1]["Absolute Impact"] == pytest.approx(10_000_000)


def test_liquidity_stress_reduces_runway():
    result = liquidity_stress(100_000_000, 5_000_000)
    assert (result["Runway Days"].diff().dropna() < 0).all()


def test_risk_signal():
    level, alerts = risk_signal(0.50, 10)
    assert level == "High attention"
    assert len(alerts) >= 2
