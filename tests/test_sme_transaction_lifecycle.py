import pytest

from services import sme_store
from services import sme_accounting


def test_unposted_transaction_can_be_updated_and_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("test-user")
    business_id = sme_store.create_business(user_id, "Test Business")
    account_id = sme_store.list_accounts(business_id)[0]["id"]

    tx_id = sme_store.add_transaction(
        business_id,
        "2026-09-01",
        "Office supplies",
        5000,
        "Expense",
        account_id=account_id,
        category="Office",
    )
    sme_store.update_transaction(
        business_id,
        tx_id,
        description="Office supplies updated",
        amount=6500,
        category="Admin",
    )
    row = sme_store.transactions_df(business_id).iloc[0]
    assert row["description"] == "Office supplies updated"
    assert float(row["amount"]) == 6500

    sme_store.delete_transaction(business_id, tx_id)
    assert sme_store.transactions_df(business_id).empty


def test_posted_transaction_is_locked(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("test-user")
    business_id = sme_store.create_business(user_id, "Test Business")
    tx_id = sme_store.add_transaction(business_id, "2026-09-01", "Sale", 10000, "Income")

    # Use the real accounting engine rather than recreating a partial schema.
    sme_accounting.ensure_standard_accounts(business_id)
    accounts = sme_accounting.account_catalog(business_id)
    bank_id = int(accounts.loc[accounts["name"] == "Main Bank", "id"].iloc[0])
    revenue_id = int(accounts.loc[accounts["name"] == "Sales Revenue", "id"].iloc[0])
    journal_id = sme_accounting.post_journal_entry(
        business_id,
        "2026-09-01",
        "Sale",
        [
            {"account_id": bank_id, "debit": 10000},
            {"account_id": revenue_id, "credit": 10000},
        ],
        source="Transaction sync",
        source_transaction_id=tx_id,
    )
    assert journal_id > 0

    with sme_store.connect() as conn:
        assert sme_store.transaction_has_posted_journal(conn, business_id, tx_id) is True

    with pytest.raises(ValueError, match="already posted"):
        sme_store.update_transaction(business_id, tx_id, description="Changed")
    with pytest.raises(ValueError, match="already posted"):
        sme_store.delete_transaction(business_id, tx_id)
