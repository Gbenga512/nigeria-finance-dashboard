import pandas as pd
import pytest

from analytics.research_lab import methodology_record, research_metrics, research_summary, run_research_experiment


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


def test_empty_summary():
    assert "No research result" in research_summary(pd.DataFrame(), 0.95)
