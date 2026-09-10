from pathlib import Path
import pandas as pd

import services.sme_store as store
from services.sme_store import create_business, get_or_create_user, init_db, list_accounts
from services.sme_accounting import ensure_standard_accounts, post_journal_entry
from analytics.sme_management_accounts import management_accounts
from analytics.sme_cashflow_v2 import forecast_13_weeks
from services.sme_budget import create_budget, variance_report


def setup(tmp_path: Path):
    db = tmp_path / "test.db"
    old = store.DB_PATH; store.DB_PATH = db
    init_db(db)
    user = get_or_create_user("mgmt-user")
    bid = create_business(user, "Management Test")
    ensure_standard_accounts(bid)
    accounts = {r["name"]: int(r["id"]) for r in list_accounts(bid)}
    return db, old, bid, accounts


def test_management_accounts_calculations(tmp_path):
    db, old, bid, a = setup(tmp_path)
    try:
        post_journal_entry(bid, "2026-01-05", "Sale", [{"account_id":a["Main Bank"],"debit":200000},{"account_id":a["Sales Revenue"],"credit":200000}])
        post_journal_entry(bid, "2026-01-06", "COGS", [{"account_id":a["Cost of Goods Sold"],"debit":80000},{"account_id":a["Main Bank"],"credit":80000}])
        post_journal_entry(bid, "2026-01-07", "Rent", [{"account_id":a["Rent"],"debit":30000},{"account_id":a["Main Bank"],"credit":30000}])
        r = management_accounts(bid, "2026-01-01", "2026-01-31")["kpis"]
        assert r["revenue"] == 200000
        assert r["cogs"] == 80000
        assert r["gross_profit"] == 120000
        assert r["net_income"] == 90000
        assert r["gross_margin"] == 0.6
    finally:
        store.DB_PATH = old


def test_cash_forecast_uses_opening_cash_and_returns_13_weeks():
    tx = pd.DataFrame([
        {"transaction_date":"2026-01-02","transaction_type":"Income","amount":100000},
        {"transaction_date":"2026-01-03","transaction_type":"Expense","amount":40000},
        {"transaction_date":"2026-01-10","transaction_type":"Income","amount":120000},
        {"transaction_date":"2026-01-11","transaction_type":"Expense","amount":50000},
    ])
    result = forecast_13_weeks(tx, as_of="2026-01-15", opening_cash=500000)
    assert len(result["forecast"]) == 13
    assert result["forecast"].iloc[0]["Opening Cash"] == 500000
    assert result["status"] == "BASELINE"


def test_budget_variance(tmp_path):
    db, old, bid, a = setup(tmp_path)
    try:
        post_journal_entry(bid, "2026-02-05", "Sale", [{"account_id":a["Main Bank"],"debit":150000},{"account_id":a["Sales Revenue"],"credit":150000}])
        budget = create_budget(bid, "February Budget", "2026-02-01", "2026-02-28", [{"account_id":a["Sales Revenue"],"amount":100000}])
        vr = variance_report(bid, budget)
        assert float(vr.iloc[0]["Actual"]) == 150000
        assert float(vr.iloc[0]["Variance"]) == 50000
    finally:
        store.DB_PATH = old
