import pytest

from services import sme_store


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

    # Create the minimum accounting link used by the protection rule.
    with sme_store.connect() as conn:
        conn.executescript(
            """
            CREATE TABLE journal_entries (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                source_transaction_id INTEGER UNIQUE,
                status TEXT NOT NULL
            );
            INSERT INTO journal_entries(id, business_id, source_transaction_id, status)
            VALUES (1, ?, ?, 'Posted');
            """,
        , (business_id, tx_id))

    assert sme_store.transaction_has_posted_journal(sme_store.connect(), business_id, tx_id) is True
    with pytest.raises(ValueError, match="already posted"):
        sme_store.update_transaction(business_id, tx_id, description="Changed")
    with pytest.raises(ValueError, match="already posted"):
        sme_store.delete_transaction(business_id, tx_id)
