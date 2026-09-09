from pathlib import Path

import pytest

from services.sme_store import connect, create_business, get_or_create_user, init_db
from services.sme_accounting import (
    balance_sheet,
    ensure_standard_accounts,
    post_journal_entry,
    profit_and_loss,
    trial_balance,
)


def make_business(tmp_path: Path) -> int:
    db = tmp_path / "test.db"
    import services.sme_store as store
    old = store.DB_PATH
    store.DB_PATH = db
    try:
        init_db(db)
        user = get_or_create_user("test-user")
        return create_business(user, "Test Business")
    finally:
        store.DB_PATH = old


def test_balanced_journal_and_trial_balance(tmp_path):
    import services.sme_store as store
    db = tmp_path / "test.db"
    old = store.DB_PATH; store.DB_PATH = db
    try:
        init_db(db); user = get_or_create_user("u1"); business = create_business(user, "Test")
        ensure_standard_accounts(business)
        accounts = {r["name"]: r["id"] for r in store.list_accounts(business)}
        post_journal_entry(business, "2026-01-01", "Owner funding", [
            {"account_id": accounts["Main Bank"], "debit": 100000},
            {"account_id": accounts["Owner's Equity"], "credit": 100000},
        ])
        tb = trial_balance(business, "2026-01-01", "2026-01-31")
        assert round(float(tb["Debits"].sum()), 2) == round(float(tb["Credits"].sum()), 2)
        bs = balance_sheet(business, "2026-01-31")
        assert bs["Balanced"] is True
    finally:
        store.DB_PATH = old


def test_unbalanced_journal_rejected(tmp_path):
    import services.sme_store as store
    db = tmp_path / "test.db"; old = store.DB_PATH; store.DB_PATH = db
    try:
        init_db(db); user = get_or_create_user("u2"); business = create_business(user, "Test")
        ensure_standard_accounts(business)
        accounts = {r["name"]: r["id"] for r in store.list_accounts(business)}
        with pytest.raises(ValueError, match="not balanced"):
            post_journal_entry(business, "2026-01-01", "Bad entry", [
                {"account_id": accounts["Main Bank"], "debit": 100000},
                {"account_id": accounts["Owner's Equity"], "credit": 90000},
            ])
    finally:
        store.DB_PATH = old


def test_profit_and_loss(tmp_path):
    import services.sme_store as store
    db = tmp_path / "test.db"; old = store.DB_PATH; store.DB_PATH = db
    try:
        init_db(db); user = get_or_create_user("u3"); business = create_business(user, "Test")
        ensure_standard_accounts(business)
        accounts = {r["name"]: r["id"] for r in store.list_accounts(business)}
        post_journal_entry(business, "2026-02-01", "Sale", [{"account_id": accounts["Main Bank"], "debit": 200000}, {"account_id": accounts["Sales Revenue"], "credit": 200000}])
        post_journal_entry(business, "2026-02-02", "Rent", [{"account_id": accounts["Rent"], "debit": 50000}, {"account_id": accounts["Main Bank"], "credit": 50000}])
        pnl = profit_and_loss(business, "2026-02-01", "2026-02-28")
        assert pnl["Revenue"] == 200000
        assert pnl["Expenses"] == 50000
        assert pnl["Net Income"] == 150000
    finally:
        store.DB_PATH = old
