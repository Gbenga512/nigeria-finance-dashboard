import pytest

from services import sme_parties, sme_store


def test_customer_invoice_and_payment_are_business_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("party-test")
    business_id = sme_store.create_business(user_id, "Test Business")
    customer_id = sme_parties.create_party(business_id, "Customer", "Acme Ltd", payment_terms_days=30)
    invoice_id = sme_parties.create_invoice(
        business_id, customer_id, "INV-001", "2026-09-01", "Consulting", 100000, 7500, "2026-10-01"
    )
    register = sme_parties.invoice_register(business_id, "Customer")
    assert float(register.loc[register["id"] == invoice_id, "outstanding"].iloc[0]) == 107500
    sme_parties.record_payment(business_id, invoice_id, 50000)
    register = sme_parties.invoice_register(business_id, "Customer")
    row = register.loc[register["id"] == invoice_id].iloc[0]
    assert float(row["paid_amount"]) == 50000
    assert float(row["outstanding"]) == 57500
    assert row["status"] == "Partially Paid"


def test_payment_cannot_exceed_outstanding(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("party-test")
    business_id = sme_store.create_business(user_id, "Test Business")
    supplier_id = sme_parties.create_party(business_id, "Supplier", "Vendor Ltd")
    invoice_id = sme_parties.create_invoice(business_id, supplier_id, "BILL-001", "2026-09-01", "Inventory", 25000)
    with pytest.raises(ValueError, match="exceeds"):
        sme_parties.record_payment(business_id, invoice_id, 25001)


def test_duplicate_party_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("party-test")
    business_id = sme_store.create_business(user_id, "Test Business")
    sme_parties.create_party(business_id, "Customer", "Same Name")
    with pytest.raises(ValueError, match="already exists"):
        sme_parties.create_party(business_id, "Customer", "Same Name")


def test_invoice_defaults_due_date_from_payment_terms(tmp_path, monkeypatch):
    monkeypatch.setattr(sme_store, "DB_PATH", tmp_path / "sme.db")
    user_id = sme_store.get_or_create_user("party-test")
    business_id = sme_store.create_business(user_id, "Test Business")
    customer_id = sme_parties.create_party(business_id, "Customer", "Acme", payment_terms_days=14)
    invoice_id = sme_parties.create_invoice(business_id, customer_id, "INV-002", "2026-09-01", "Service", 10000)
    register = sme_parties.invoice_register(business_id, "Customer")
    assert str(register.loc[register["id"] == invoice_id, "due_date"].iloc[0].date()) == "2026-09-15"
