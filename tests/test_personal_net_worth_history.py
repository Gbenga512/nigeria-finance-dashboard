from pathlib import Path

import pytest

from services import personal_finance
from services import personal_finance_wealth as wealth
from services import personal_net_worth_history as history


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    history.ensure_snapshot_schema()
    yield


def test_record_snapshot_persists_historical_value(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 1_000_000, "Income", "Salary", account_id
    )
    nw = history.record_snapshot("2026-09-30", "September close")
    df = history.snapshots()
    assert len(df) == 1
    assert float(df.iloc[0]["net_worth"]) == nw["net_worth"]
    assert df.iloc[0]["notes"] == "September close"


def test_snapshot_same_date_is_updated_not_duplicated(isolated_db):
    history.record_snapshot("2026-09-30", "First")
    history.record_snapshot("2026-09-30", "Updated")
    df = history.snapshots()
    assert len(df) == 1
    assert df.iloc[0]["notes"] == "Updated"


def test_snapshot_summary_calculates_change(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    history.record_snapshot("2026-09-01")
    personal_finance.add_transaction(
        "2026-09-15", "Salary", 500_000, "Income", "Salary", account_id
    )
    history.record_snapshot("2026-09-30")
    summary = history.snapshot_summary()
    assert summary["snapshot_count"] == 2
    assert summary["change"] == 500_000
