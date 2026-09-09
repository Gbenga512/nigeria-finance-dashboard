import pandas as pd
import pytest

from analytics.research_lab import (
    methodology_record,
    research_metrics,
    research_summary,
    rolling_volatility,
    run_research_experiment,
    scenario_loss,
    scenario_matrix,
)


def test_research_metrics_contains_validation_outputs():
    prices = pd.Series([100, 102, 99, 101, 98, 100, 97, 99], dtype=float)
    result = research_metrics(prices, 0.95, 3)
    assert result["observations"] == 7
    assert "historical_var" in result
    assert "monte_carlo_es" in result
    assert result["backtest_observations"] == 4


def test_run_research_experiment_multiple_assets():
    data = {
        "USD/NGN": pd.Series([100, 101, 100, 102, 103], dtype=float),
        "Gold": pd.Series([200, 198, 201, 202, 204], dtype=float),
    }
    results = run_research_experiment(data, 0.95, 2)
    assert list(results["Asset"]) == ["USD/NGN", "Gold"]
    assert len(results) == 2


def test_methodology_record_is_reproducible():
    record = methodology_record(0.95, "2y", 252)
    assert record["reproducibility_seed"] == 42
    assert record["annualization"] == "252 trading days"
    assert "scenario_analysis" in record


def test_scenario_analysis_is_deterministic():
    prices = pd.Series([100, 101, 99], dtype=float)
    assert scenario_loss(prices, -0.10) == pytest.approx(0.10)
    assert scenario_loss(prices, 0.10) is None
    matrix = scenario_matrix({"USD/NGN": prices}, [-0.05, -0.10])
    assert len(matrix) == 2
    assert set(matrix["Asset"]) == {"USD/NGN"}


def test_rolling_volatility_returns_series():
    prices = pd.Series(range(100, 140), dtype=float)
    result = rolling_volatility(prices, window=5)
    assert isinstance(result, pd.Series)
    assert result.notna().sum() > 0


def test_empty_summary():
    assert "No research result" in research_summary(pd.DataFrame(), 0.95)
