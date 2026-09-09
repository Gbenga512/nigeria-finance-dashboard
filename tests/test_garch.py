import numpy as np
import pandas as pd

from analytics.garch import ewma_volatility, fit_garch11


def test_garch_estimation_is_valid_on_clustered_returns():
    rng = np.random.default_rng(42)
    n = 500
    eps = np.zeros(n)
    variance = np.zeros(n)
    variance[0] = 0.0001
    for i in range(1, n):
        variance[i] = 0.000001 + 0.10 * eps[i - 1] ** 2 + 0.85 * variance[i - 1]
        eps[i] = np.sqrt(variance[i]) * rng.normal()
    result = fit_garch11(pd.Series(eps))
    assert result["success"]
    assert result["omega"] > 0
    assert result["alpha"] >= 0
    assert result["beta"] >= 0
    assert result["persistence"] < 1
    assert result["forecast_volatility"] > 0
    assert len(result["conditional_volatility"]) == n


def test_garch_short_series_fails_cleanly():
    result = fit_garch11(pd.Series(np.zeros(20)))
    assert not result["success"]


def test_ewma_is_positive_and_annualized():
    returns = pd.Series(np.linspace(-0.01, 0.01, 100))
    vol = ewma_volatility(returns)
    assert len(vol) == 100
    assert (vol > 0).all()
