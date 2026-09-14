"""IFRS-oriented AR/AP payment controls for NG Finance Pro.

The module keeps operational payment history separate from the GL and posts
only explicitly approved payments. It does not provide tax or audit advice.
"""
from __future__ import annotations

import math
from datetime import date
from services.sme_store import connect, init_db
from services.sme_accounting import ensure_standard_accounts, post_journal_entry

SCHEMA = """
CREATE TABLE IF NOT EXISTS party_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    cash_account_id INTEGER NOT NULL,
    reference TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'Recorded' CHECK(status IN ('Recorded','Posted','Voided')),
    journal_entry_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    FOREIGN KEY(invoice_id) REFERENCES party_invoices(id) ON DELETE RESTRICT,
    FOREIGN KEY(cash_account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
    FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_party_payments_invoice ON party_payments(business_id,invoice_id,payment_date);
"""

def ensure_payment_schema() -> None:
    init_db()
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()

def _money(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Payment amount must be a finite amount greater than zero.")
    return round(value, 2)

def _date(value: str | date) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("Payment date must be a valid date (YYYY-MM-DD).") from exc

def record_payment_controlled(
    business_id: int,
    invoice_id: int,
    amount: float,
    payment_date: str | date,
    cash_account_id: int,
    reference: str = "",
    notes: str = "",
) -> int:
    """Record a payment without posting it to the GL.

    Customer invoice: payment clears AR; supplier invoice: payment clears AP.
    Posting remains an explicit second action so the operational subledger and
    accounting ledger cannot silently diverge.
    """
    ensure_payment_schema(); ensure_standard_accounts(business_id)
    amount = _money(amount); payment_date = _date(payment_date)
    with connect() as conn:
        inv = conn.execute("SELECT * FROM party_invoices WHERE id=? AND business_id=?", (invoice_id, business_id)).fetchone()
        if not inv or inv["status"] == "Cancelled":
            raise ValueError("Invoice was not found or is cancelled.")
        outstanding = round(float(inv["total_amount"]) - float(inv["paid_amount"]), 2)
        if amount > outstanding + 1e-9:
            raise ValueError(f"Payment exceeds outstanding balance of ₦{outstanding:,.2f}.")
        acct = conn.execute("SELECT id,name FROM accounts WHERE id=? AND business_id=? AND active=1", (cash_account_id, business_id)).fetchone()
        if not acct or acct["name"] not in {"Main Bank", "Cash on Hand"}:
            raise ValueError("Payment cash account must be Main Bank or Cash on Hand.")
        cur = conn.execute("INSERT INTO party_payments(business_id,invoice_id,payment_date,amount,cash_account_id,reference,notes) VALUES(?,?,?,?,?,?,?)", (business_id, invoice_id, payment_date, amount, cash_account_id, reference, notes))
        payment_id = int(cur.lastrowid)
        paid = round(float(inv["paid_amount"]) + amount, 2)
        status = "Paid" if abs(paid - float(inv["total_amount"])) < 1e-9 else "Partially Paid"
        conn.execute("UPDATE party_invoices SET paid_amount=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND business_id=?", (paid, status, invoice_id, business_id))
        conn.commit()
    return payment_id

def post_payment_to_ledger(business_id: int, payment_id: int) -> int:
    """Post a recorded payment exactly once using AR/AP clearing."""
    ensure_payment_schema(); ensure_standard_accounts(business_id)
    with connect() as conn:
        p = conn.execute("SELECT pp.*,pi.invoice_number,pi.total_amount,pt.party_type,pt.name AS party_name FROM party_payments pp JOIN party_invoices pi ON pi.id=pp.invoice_id JOIN parties pt ON pt.id=pi.party_id WHERE pp.id=? AND pp.business_id=?", (payment_id, business_id)).fetchone()
        if not p:
            raise ValueError("Payment was not found for the active business.")
        if p["status"] == "Voided": raise ValueError("Voided payments cannot be posted.")
        if p["journal_entry_id"]:
            return int(p["journal_entry_id"])
        accounts = {r["name"]: int(r["id"]) for r in conn.execute("SELECT id,name FROM accounts WHERE business_id=? AND active=1", (business_id,)).fetchall()}
    amount = float(p["amount"])
    if p["party_type"] == "Customer":
        lines = [{"account_id": int(p["cash_account_id"]), "debit": amount}, {"account_id": accounts["Accounts Receivable"], "credit": amount}]
    else:
        lines = [{"account_id": accounts["Accounts Payable"], "debit": amount}, {"account_id": int(p["cash_account_id"]), "credit": amount}]
    ref = f"ARAP-PAYMENT:{payment_id}"
    journal_id = post_journal_entry(business_id, p["payment_date"], f"Payment {p['invoice_number']} — {p['party_name']}", lines, reference=ref, source="AR/AP payment")
    with connect() as conn:
        conn.execute("UPDATE party_payments SET status='Posted',journal_entry_id=? WHERE id=? AND business_id=?", (journal_id, payment_id, business_id))
        conn.commit()
    return journal_id

def payment_register(business_id: int):
    import pandas as pd
    ensure_payment_schema()
    with connect() as conn:
        return pd.read_sql_query("""SELECT pp.id,pp.payment_date,pp.amount,pp.reference,pp.status,pp.journal_entry_id,
            pi.invoice_number,pt.party_type,pt.name AS party_name,a.name AS cash_account
            FROM party_payments pp JOIN party_invoices pi ON pi.id=pp.invoice_id
            JOIN parties pt ON pt.id=pi.party_id JOIN accounts a ON a.id=pp.cash_account_id
            WHERE pp.business_id=? ORDER BY date(pp.payment_date) DESC,pp.id DESC""", conn, params=[business_id], parse_dates=["payment_date"])
