import pandas as pd

from analytics.data_quality import amount_anomalies, control_summary, daily_control_totals, quality_score


def sample_frame():
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-03"]),
        "account": ["Cash", "Cash", "Sales", "Sales"],
        "description": ["A", "A", "B", "C"],
        "debit": [100, 100, 0, 0],
        "credit": [0, 0, 200, 0],
        "amount": [100, 100, -200, 100],
    })


def test_quality_score_is_bounded():
    result = quality_score(sample_frame())
    assert 0 <= result["score"] <= 100
    assert result["rows"] == 4
    assert result["duplicate_rows"] == 1


def test_amount_anomaly_flags_extreme_value():
    frame = pd.DataFrame({"amount": [10, 11, 9, 10, 1000]})
    result = amount_anomalies(frame, z_threshold=3)
    assert not result.empty
    assert float(result.iloc[0]["amount"]) == 1000


def test_daily_control_totals():
    result = daily_control_totals(sample_frame())
    assert len(result) == 3
    assert int(result.iloc[0]["Transaction Count"]) == 2


def test_control_summary_returns_observations():
    result = control_summary(sample_frame())
    assert "quality" in result
    assert isinstance(result["observations"], list)
