from pathlib import Path

import pytest

from services import personal_finance
from services import personal_finance_controls as controls


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    yield


def _account_id():
    return int(personal_finance.accounts().iloc[0]["id"])


def test_update_transaction_reclassifies_and_audits(isolated_db):
    tx_id = personal_finance.add_transaction(
        "2026-09-01", "Groceries", 50000, "Expense", "Food", _account_id()
    )
    controls.record_create(tx_id)
    controls.update_transaction(
        tx_id,
        transaction_date="2026-09-02",
        description="Entertainment",
        amount=25000,
        transaction_type="Expense",
        category="Entertainment",
        account_id=_account_id(),
        reason="Corrected category and amount",
    )

    tx = personal_finance.transactions()
    row = tx.loc[tx["id"] == tx_id].iloc[0]
    assert row["amount"] == 25000
    assert row["category"] == "Entertainment"
    assert row["classification"] == "Want"

    audit = controls.audit_log(tx_id)
    assert [x["action"] for x in audit] == ["UPDATE", "CREATE"]
    assert "Groceries" in audit[0]["before_json"]
    assert "Entertainment" in audit[0]["after_json"]


def test_delete_transaction_is_audited_and_removed(isolated_db):
    tx_id = personal_finance.add_transaction(
        "2026-09-03", "Old expense", 10000, "Expense", "Food", _account_id()
    )
    controls.delete_transaction(tx_id, "Duplicate entry")

    assert personal_finance.transactions().empty
    audit = controls.audit_log(tx_id)
    assert len(audit) == 1
    assert audit[0]["action"] == "DELETE"
    assert "Old expense" in audit[0]["before_json"]


def test_update_rejects_invalid_account_and_transfer(isolated_db):
    tx_id = personal_finance.add_transaction(
        "2026-09-04", "Salary", 100000, "Income", "Salary", _account_id()
    )
    with pytest.raises(ValueError, match="account"):
        controls.update_transaction(
            tx_id,
            transaction_date="2026-09-04",
            description="Salary",
            amount=100000,
            transaction_type="Income",
            category="Salary",
            account_id=99999,
        )
    with pytest.raises(ValueError, match="Transfers workspace"):
        controls.update_transaction(
            tx_id,
            transaction_date="2026-09-04",
            description="Salary",
            amount=100000,
            transaction_type="Transfer",
            category="Salary",
            account_id=_account_id(),
        )
