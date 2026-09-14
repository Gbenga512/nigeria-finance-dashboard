import pytest
from services import sme_store
from services.sme_parties import create_party, create_invoice, post_invoice_to_ledger, invoice_register
from services.sme_accounting import journal_entries_df, trial_balance

def test_sales_invoice_posts_balanced_to_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user=sme_store.get_or_create_user("arap-test")
    bid=sme_store.create_business(user,"Test Business")
    customer=create_party(bid,"Customer","ACME Ltd")
    iid=create_invoice(bid,customer,"INV-001","2026-09-01","Consulting",100000,7500,"2026-09-30")
    jid=post_invoice_to_ledger(bid,iid)
    assert jid > 0
    tb=trial_balance(bid)
    assert round(float(tb.Debits.sum()),2)==round(float(tb.Credits.sum()),2)
    entries=journal_entries_df(bid)
    assert set(entries["account"]) >= {"Accounts Receivable","Sales Revenue","Tax Payable"}
    assert post_invoice_to_ledger(bid,iid)==jid

def test_purchase_invoice_posts_balanced_to_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user=sme_store.get_or_create_user("arap-test")
    bid=sme_store.create_business(user,"Test Business")
    supplier=create_party(bid,"Supplier","Vendor Ltd")
    iid=create_invoice(bid,supplier,"BILL-001","2026-09-01","Supplies",50000,3750,"2026-09-30")
    post_invoice_to_ledger(bid,iid)
    tb=trial_balance(bid)
    assert round(float(tb.Debits.sum()),2)==round(float(tb.Credits.sum()),2)
    assert float(invoice_register(bid,"Supplier").iloc[0]["outstanding"]) == 53750

def test_invoice_rejects_due_date_before_invoice_date(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user=sme_store.get_or_create_user("arap-test")
    bid=sme_store.create_business(user,"Test Business")
    customer=create_party(bid,"Customer","ACME Ltd")
    with pytest.raises(ValueError, match="Due date"):
        create_invoice(bid,customer,"INV-002","2026-09-10","Consulting",1000,0,"2026-09-01")
