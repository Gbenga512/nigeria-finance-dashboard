import numpy as np
import pandas as pd

from analytics.volatility_benchmark import benchmark_volatility_models


def test_volatility_benchmark_is_chronological_and_reproducible():
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(0.0002, 0.012, 360))
    result = benchmark_volatility_models(returns, train_window=120, test_window=60, garch_refit=20)
    assert result["available"]
    assert result["test_observations"] == 60
    assert set(result["summary"]["Model"]) == {"Historical", "EWMA", "GARCH(1,1)"}
    detail = result["detail"]
    assert detail["Observation"].min() == 120
    assert (detail["Forecast Variance"] > 0).all()
    assert (detail["QLIKE"] >= 0).all()


def test_volatility_benchmark_fails_cleanly_when_too_short():
    result = benchmark_volatility_models(pd.Series(np.random.default_rng(1).normal(size=100)), train_window=120)
    assert not result["available"]
