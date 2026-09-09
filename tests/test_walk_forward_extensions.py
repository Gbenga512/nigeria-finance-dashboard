import numpy as np
import pandas as pd

from analytics.backtesting import regime_conditioned_performance, walk_forward_backtest
from analytics.portfolio_risk import portfolio_walk_forward


def test_regime_conditioned_performance_returns_regime_rows():
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.0002, 0.01, 320))
    prices = pd.Series(100 * np.cumprod(1 + returns))
    result = regime_conditioned_performance(returns, prices)
    assert not result.empty
    assert {"Regime", "Observations", "Sharpe"}.issubset(result.columns)


def test_walk_forward_exposes_regime_summary():
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.01, 700)
    prices = pd.Series(100 * np.cumprod(1 + returns))
    result = walk_forward_backtest(prices, train_window=252, test_window=63)
    assert "regime_summary" in result
    assert isinstance(result["regime_summary"], pd.DataFrame)


def test_portfolio_walk_forward_returns_oos_blocks():
    rng = np.random.default_rng(9)
    dates = pd.date_range("2022-01-01", periods=700, freq="B")
    price_map = {
        "Asset A": pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.01, 700)), index=dates),
        "Asset B": pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.012, 700)), index=dates),
        "Asset C": pd.Series(100 * np.cumprod(1 + rng.normal(0.0002, 0.008, 700)), index=dates),
    }
    result = portfolio_walk_forward(price_map, {"Asset A": 0.4, "Asset B": 0.35, "Asset C": 0.25}, train_window=252, test_window=63)
    assert result["summary"]["blocks"] >= 1
    assert not result["blocks"].empty
    assert {"Portfolio", "Equal Weight Benchmark"}.issubset(result["equity"].columns)
