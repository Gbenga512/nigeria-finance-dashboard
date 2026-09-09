import numpy as np
import pandas as pd

from analytics.var_backtesting import backtest_var, christoffersen_independence, kupiec_pof


def test_kupiec_accepts_reasonable_exception_rate():
    exceptions = pd.Series([0] * 95 + [1] * 5)
    result = kupiec_pof(exceptions, 0.95)
    assert result["observations"] == 100
    assert result["exceptions"] == 5
    assert result["p_value"] > 0.05


def test_independence_detects_clustered_exceptions():
    exceptions = pd.Series([1, 1, 1, 0, 0, 0, 1, 1, 0, 0] * 10)
    result = christoffersen_independence(exceptions)
    assert result["n11"] > 0
    assert np.isfinite(result["statistic"])


def test_full_backtest_aligns_series():
    returns = pd.Series([-0.01, -0.10, 0.01, -0.02, 0.03])
    var = pd.Series([0.02, 0.02, 0.02, 0.02, 0.02])
    result = backtest_var(returns, var, 0.95)
    assert int(result["exceptions"].sum()) == 1
    assert result["kupiec"]["observations"] == 5
    assert np.isfinite(result["conditional_coverage"]["statistic"])
