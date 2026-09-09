import pandas as pd

from analytics.sme_finance import monthly_trend, period_metrics, transaction_health


def sample_transactions():
    return pd.DataFrame({
        "transaction_date": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-03"]),
        "description": ["Sale", "Rent", "Sale"],
        "amount": [100000, 30000, 50000],
        "transaction_type": ["Income", "Expense", "Receipt"],
        "category": ["Sales", "Rent", "Sales"],
        "reference": ["A", "B", "C"],
    })


def test_period_metrics_are_data_derived():
    metrics = period_metrics(sample_transactions(), "2026-09-01", "2026-09-30")
    assert metrics["revenue"] == 150000
    assert metrics["expenses"] == 30000
    assert metrics["net_profit"] == 120000


def test_monthly_trend_returns_monthly_totals():
    trend = monthly_trend(sample_transactions())
    assert trend.iloc[0]["Revenue"] == 150000
    assert trend.iloc[0]["Expenses"] == 30000
    assert trend.iloc[0]["Net Cash Flow"] == 120000


def test_transaction_health_is_transparent():
    result = transaction_health(sample_transactions())
    assert result["score"] is not None
    assert len(result["factors"]) == 2
