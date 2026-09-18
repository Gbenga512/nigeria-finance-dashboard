from pathlib import Path

import pytest

from analytics import personal_allocation
from services import personal_finance


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    yield


def account_id():
    return int(personal_finance.accounts().iloc[0]["id"])


def test_three_bucket_allocation_uses_recorded_transactions(isolated_db):
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 1_000_000, "Income", "Salary", account_id()
    )
    personal_finance.add_transaction(
        "2026-09-02", "Rent", 250_000, "Expense", "Rent", account_id()
    )
    personal_finance.add_transaction(
        "2026-09-03", "Shopping", 50_000, "Expense", "Shopping", account_id()
    )
    personal_finance.add_transaction(
        "2026-09-04", "Investment", 200_000, "Investment", "Investment", account_id()
    )

    report = personal_allocation.allocation_report("2026-09-01", "2026-09-30")
    actual = dict(zip(report["Bucket"], report["Actual"]))
    assert actual["Needs"] == 250_000
    assert actual["Wants"] == 50_000
    assert actual["Savings/Investment"] == 200_000


def test_allocation_targets_use_income_and_budgets(isolated_db):
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 1_000_000, "Income", "Salary", account_id()
    )
    personal_finance.set_budget("2026-09", "Rent", 300_000)
    personal_finance.set_budget("2026-09", "Shopping", 100_000)

    report = personal_allocation.allocation_report("2026-09-01", "2026-09-30")
    rows = report.set_index("Bucket")
    assert rows.loc["Needs", "Target Amount"] == 500_000
    assert rows.loc["Wants", "Target Amount"] == 300_000
    assert rows.loc["Savings/Investment", "Target Amount"] == 200_000
    assert rows.loc["Needs", "Budgeted"] == 300_000
    assert rows.loc["Wants", "Budgeted"] == 100_000
