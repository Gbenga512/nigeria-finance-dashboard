from pathlib import Path

import pytest

from services import personal_finance
from services import personal_finance_wealth as wealth
from services import personal_investment_history as history


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    history.ensure_schema()
    yield


def test_valuation_history_updates_current_value_and_preserves_observations(isolated_db):
    investment_id = wealth.add_investment(
        "Equity Fund", "Fund", 100_000, 110_000, units=10, as_of_date="2026-09-01"
    )
    history.record_valuation(investment_id, "2026-09-15", 120_000, 10)
    history.record_valuation(investment_id, "2026-09-30", 125_000, 10)

    h = history.valuation_history(investment_id)
    assert len(h) == 2
    assert float(h.iloc[-1]["current_value"]) == 125_000

    current = wealth.investments("2026-09-30")
    row = current.loc[current["id"] == investment_id].iloc[0]
    assert float(row["current_value"]) == 125_000


def test_same_valuation_date_is_upserted(isolated_db):
    investment_id = wealth.add_investment(
        "Fund", "Fund", 100_000, 100_000, as_of_date="2026-09-01"
    )
    history.record_valuation(investment_id, "2026-09-30", 105_000)
    history.record_valuation(investment_id, "2026-09-30", 108_000)

    h = history.valuation_history(investment_id)
    assert len(h) == 1
    assert float(h.iloc[0]["current_value"]) == 108_000


def test_performance_summary_calculates_gain_and_return(isolated_db):
    investment_id = wealth.add_investment(
        "Shares", "Equity", 200_000, 230_000, as_of_date="2026-09-01"
    )
    history.record_valuation(investment_id, "2026-09-30", 250_000)
    summary = history.performance_summary().set_index("investment_id")
    assert summary.loc[investment_id, "gain_loss"] == 50_000
    assert summary.loc[investment_id, "return_pct"] == 25
