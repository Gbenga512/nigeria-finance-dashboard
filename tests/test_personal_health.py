from pathlib import Path

import pytest

from analytics import personal_health
from services import personal_finance
from services import personal_finance_wealth as wealth


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    yield


def test_health_score_is_transparent_and_bounded(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 1_000_000, "Income", "Salary", account_id
    )
    personal_finance.add_transaction(
        "2026-09-05", "Rent", 200_000, "Expense", "Rent", account_id
    )
    personal_finance.add_transaction(
        "2026-09-10", "Investment", 200_000, "Investment", "Investment", account_id
    )
    result = personal_health.health_score("2026-09-01", "2026-09-30")
    assert 0 <= result["score"] <= 100
    assert len(result["components"]) == 6
    assert set(["Component", "Score", "Basis"]).issubset(result["components"].columns)
    assert result["status"].startswith("CALCULATION:")


def test_negative_cash_flow_reduces_cash_flow_component(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 100_000, "Income", "Salary", account_id
    )
    personal_finance.add_transaction(
        "2026-09-02", "Large expense", 150_000, "Expense", "Rent", account_id
    )
    result = personal_health.health_score("2026-09-01", "2026-09-30")
    row = result["components"].set_index("Component").loc["Net Cash Flow"]
    assert row["Score"] == 0
