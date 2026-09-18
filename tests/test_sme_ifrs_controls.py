from pathlib import Path
from services import sme_store
from services import sme_accounting
from services import sme_parties
from services import ifrs_payment_controls


def setup(tmp_path):
    sme_store.DB_PATH = Path(tmp_path) / "sme.db"
    uid = sme_store.get_or_create_user()
    bid = sme_store.create_business(
        uid,
        "IFRS Test",
        industry="Services",
        location="Lagos",
        currency="NGN",
    )
    sme_accounting.ensure_standard_accounts(bid)
    return bid


def test_supplier_recoverable_vat_posts_to_asset(tmp_path):
    bid = setup(tmp_path)
    pid = sme_parties.create_party(bid, "Supplier", "Supplier A")
    inv = sme_parties.create_invoice(
        bid, pid, "SUP-1", "2026-09-01", "Services", 100000, 7500, "2026-09-30"
    )
    sme_parties.post_invoice_to_ledger(bid, inv)
    tb = sme_accounting.trial_balance(bid)
    row = tb[tb["Account"] == "VAT Recoverable"].iloc[0]
    assert float(row["Debits"]) == 7500
    assert float(row["Credits"]) == 0


def test_controlled_payment_records_then_posts(tmp_path):
    bid = setup(tmp_path)
    pid = sme_parties.create_party(bid, "Customer", "Customer A")
    inv = sme_parties.create_invoice(
        bid, pid, "INV-1", "2026-09-01", "Sale", 100000, 7500, "2026-09-30"
    )
    cash = int(
        sme_accounting.account_catalog(bid).query("name == 'Main Bank'").iloc[0]["id"]
    )
    payment = ifrs_payment_controls.record_payment_controlled(
        bid, inv, 50000, "2026-09-15", cash, "REF-1"
    )
    reg = ifrs_payment_controls.payment_register(bid)
    assert reg.iloc[0]["status"] == "Recorded"
    journal = ifrs_payment_controls.post_payment_to_ledger(bid, payment)
    assert journal > 0
    reg = ifrs_payment_controls.payment_register(bid)
    assert reg.iloc[0]["status"] == "Posted"
