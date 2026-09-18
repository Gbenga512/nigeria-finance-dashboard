from pathlib import Path

import pytest

from services import personal_account_controls as controls
from services import personal_finance
from services import personal_finance_wealth as wealth


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    yield


def test_update_account_validates_and_persists(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    controls.update_account(account_id, "Primary Bank", "Cash", 125000)
    row = personal_finance.accounts().loc[
        personal_finance.accounts()["id"] == account_id
    ].iloc[0]
    assert row["name"] == "Primary Bank"
    assert row["opening_balance"] == 125000


def test_duplicate_account_name_is_rejected(isolated_db):
    accts = personal_finance.accounts()
    second = int(accts.iloc[1]["id"])
    with pytest.raises(ValueError, match="already exists"):
        controls.update_account(
            second, str(accts.iloc[0]["name"]), "Cash", 0
        )


def test_active_account_with_transactions_cannot_be_archived(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction(
        "2026-09-01", "Salary", 100000, "Income", "Salary", account_id
    )
    with pytest.raises(ValueError, match="recorded activity"):
        controls.deactivate_account(account_id)
    assert account_id in personal_finance.accounts()["id"].tolist()


def test_unused_account_can_be_archived(isolated_db):
    account_id = personal_finance.add_account("Old Wallet", "Cash", 0)
    controls.deactivate_account(account_id)
    assert account_id not in personal_finance.accounts()["id"].tolist()
