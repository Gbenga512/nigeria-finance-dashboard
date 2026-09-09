import numpy as np
import pandas as pd
import pytest

from analytics.backtesting import apply_transaction_costs, performance_metrics, strategy_signal, walk_forward_backtest


def test_strategy_signal_is_shifted_to_prevent_lookahead():
    prices = pd.Series(range(100, 140), dtype=float)
    signal = strategy_signal(prices, "momentum")
    assert signal.index.equals(prices.index)
    assert signal.iloc[0] == 0.0


def test_transaction_costs_reduce_returns_on_turnover():
    gross = pd.Series([0.01, 0.01, 0.01])
    signal = pd.Series([0.0, 1.0, 1.0])
    result = apply_transaction_costs(gross, signal, 0.01)
    assert result.iloc[1] == pytest.approx(0.0)
    assert result.iloc[2] == pytest.approx(0.01)


def test_performance_metrics_has_core_statistics():
    returns = pd.Series([0.01, -0.005, 0.02, 0.0])
    result = performance_metrics(returns, returns)
    assert result["observations"] == 4
    assert "sharpe" in result
    assert result["benchmark_cumulative_return"] == pytest.approx(result["cumulative_return"])


def test_walk_forward_returns_blocks_and_equity_curve():
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.01, 700)
    prices = pd.Series(100 * np.cumprod(1 + returns))
    result = walk_forward_backtest(prices, train_window=252, test_window=63, transaction_cost=0.001)
    assert result["summary"]["blocks"] >= 1
    assert not result["blocks"].empty
    assert not result["equity"].empty
    assert {"Strategy", "Benchmark"}.issubset(result["equity"].columns)


def test_walk_forward_insufficient_data_is_graceful():
    prices = pd.Series(range(100, 150), dtype=float)
    result = walk_forward_backtest(prices, train_window=100, test_window=20)
    assert result["summary"] == {}
    assert result["blocks"].empty
