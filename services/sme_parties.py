"""Customer, supplier and receivable/payable operational subledger services."""
from __future__ import annotations

import math
import sqlite3
from datetime import date
from typing import Any

from services.sme_store import connect, init_db


PARTY_TYPES = {"Customer", "Supplier"}
INVOICE_STATUSES = {"Draft", "Open", "Partially Paid", "Paid", "Overdue", "Cancelled"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    party_type TEXT NOT NULL CHECK(party_type IN ('Customer','Supplier')),
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    tax_id TEXT,
    credit_limit REAL NOT NULL DEFAULT 0 CHECK(credit_limit >= 0),
    payment_terms_days INTEGER NOT NULL DEFAULT 30 CHECK(payment_terms_days >= 0),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    UNIQUE(business_id, party_type, name)
);
CREATE INDEX IF NOT EXISTS idx_parties_business_type ON parties(business_id, party_type);

CREATE TABLE IF NOT EXISTS party_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    party_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    description TEXT NOT NULL,
    subtotal REAL NOT NULL CHECK(subtotal > 0),
    tax_amount REAL NOT NULL DEFAULT 0 CHECK(tax_amount >= 0),
    total_amount REAL NOT NULL CHECK(total_amount > 0),
    paid_amount REAL NOT NULL DEFAULT 0 CHECK(paid_amount >= 0),
    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Draft','Open','Partially Paid','Paid','Overdue','Cancelled')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE RESTRICT,
    UNIQUE(business_id, invoice_number)
);
CREATE INDEX IF NOT EXISTS idx_party_invoices_due ON party_invoices(business_id, due_date, status);
CREATE INDEX IF NOT EXISTS idx_party_invoices_party ON party_invoices(party_id, invoice_date);
"""


def ensure_schema() -> None:
    init_db()
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _validate_date(value: str, label: str) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid date (YYYY-MM-DD).") from exc
    return parsed.isoformat()


def _validate_money(value: float, label: str, positive: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(f"{label} must be {'greater than zero' if positive else 'finite and non-negative'}.")
    return number


def list_parties(business_id: int, party_type: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
    ensure_schema()
    if party_type is not None and party_type not in PARTY_TYPES:
        raise ValueError("Unsupported party type.")
    where = ["business_id=?"]
    params: list[Any] = [business_id]
    if party_type:
        where.append("party_type=?")
        params.append(party_type)
    if active_only:
        where.append("active=1")
    with connect() as conn:
        return [dict(row) for row in conn.execute(f"SELECT * FROM parties WHERE {' AND '.join(where)} ORDER BY name", params).fetchall()]


def create_party(business_id: int, party_type: str, name: str, **fields: Any) -> int:
    ensure_schema()
    if party_type not in PARTY_TYPES:
        raise ValueError("Party type must be Customer or Supplier.")
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Party name is required.")
    terms = int(fields.get("payment_terms_days", 30))
    if terms < 0:
        raise ValueError("Payment terms cannot be negative.")
    credit_limit = _validate_money(fields.get("credit_limit", 0), "Credit limit")
    allowed = {"contact_name", "email", "phone", "address", "tax_id"}
    data = {k: fields.get(k) for k in allowed}
    with connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO parties(business_id,party_type,name,contact_name,email,phone,address,tax_id,credit_limit,payment_terms_days) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (business_id, party_type, clean_name, data["contact_name"], data["email"], data["phone"], data["address"], data["tax_id"], credit_limit, terms),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("A party with this name already exists for this business and type.") from exc
        return int(cur.lastrowid)


def create_invoice(business_id: int, party_id: int, invoice_number: str, invoice_date: str, description: str, subtotal: float, tax_amount: float = 0, due_date: str | None = None, notes: str = "") -> int:
    ensure_schema()
    clean_number = str(invoice_number).strip()
    clean_description = str(description).strip()
    if not clean_number or not clean_description:
        raise ValueError("Invoice number and description are required.")
    invoice_date = _validate_date(invoice_date, "Invoice date")
    subtotal = _validate_money(subtotal, "Subtotal", positive=True)
    tax_amount = _validate_money(tax_amount, "Tax amount")
    if due_date is None:
        with connect() as conn:
            party = conn.execute("SELECT payment_terms_days FROM parties WHERE id=? AND business_id=? AND active=1", (party_id, business_id)).fetchone()
            if not party:
                raise ValueError("Party was not found for the active business.")
            due = date.fromisoformat(invoice_date)
            from datetime import timedelta
            due_date = (due + timedelta(days=int(party["payment_terms_days"]))).isoformat()
    due_date = _validate_date(due_date, "Due date")
    if date.fromisoformat(due_date) < date.fromisoformat(invoice_date):
        raise ValueError("Due date cannot be before the invoice date.")
    total = subtotal + tax_amount
    with connect() as conn:
        party = conn.execute("SELECT id FROM parties WHERE id=? AND business_id=? AND active=1", (party_id, business_id)).fetchone()
        if not party:
            raise ValueError("Party was not found for the active business.")
        try:
            cur = conn.execute(
                "INSERT INTO party_invoices(business_id,party_id,invoice_number,invoice_date,due_date,description,subtotal,tax_amount,total_amount,status,notes) VALUES(?,?,?,?,?,?,?,?,?,'Open',?)",
                (business_id, party_id, clean_number, invoice_date, due_date, clean_description, subtotal, tax_amount, total, notes),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Invoice number already exists for this business.") from exc
        return int(cur.lastrowid)


def invoice_register(business_id: int, party_type: str | None = None):
    """Return invoice register with calculated outstanding balance and ageing."""
    import pandas as pd
    ensure_schema()
    query = """
        SELECT i.*, p.party_type, p.name AS party_name
        FROM party_invoices i JOIN parties p ON p.id=i.party_id
        WHERE i.business_id=?
    """
    params: list[Any] = [business_id]
    if party_type:
        if party_type not in PARTY_TYPES:
            raise ValueError("Unsupported party type.")
        query += " AND p.party_type=?"
        params.append(party_type)
    query += " ORDER BY i.due_date, i.id"
    with connect() as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["invoice_date", "due_date"])
    if df.empty:
        return df
    today = pd.Timestamp(date.today())
    df["outstanding"] = (df["total_amount"] - df["paid_amount"]).clip(lower=0)
    df["days_overdue"] = ((today - df["due_date"]).dt.days).clip(lower=0)
    df["age_bucket"] = pd.cut(df["days_overdue"], bins=[-1, 0, 30, 60, 90, float("inf")], labels=["Current", "1–30", "31–60", "61–90", "90+"])
    return df


def record_payment(business_id: int, invoice_id: int, amount: float) -> None:
    """Record an operational payment against an invoice; accounting posting is intentionally separate."""
    ensure_schema()
    amount = _validate_money(amount, "Payment amount", positive=True)
    with connect() as conn:
        row = conn.execute("SELECT total_amount, paid_amount, status FROM party_invoices WHERE id=? AND business_id=?", (invoice_id, business_id)).fetchone()
        if not row:
            raise ValueError("Invoice was not found for the active business.")
        if row["status"] == "Cancelled":
            raise ValueError("Cancelled invoices cannot receive payments.")
        outstanding = float(row["total_amount"]) - float(row["paid_amount"])
        if amount > outstanding + 1e-9:
            raise ValueError(f"Payment exceeds the outstanding invoice balance of ₦{outstanding:,.2f}.")
        paid = float(row["paid_amount"]) + amount
        status = "Paid" if abs(paid - float(row["total_amount"])) < 1e-9 else "Partially Paid"
        conn.execute("UPDATE party_invoices SET paid_amount=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND business_id=?", (paid, status, invoice_id, business_id))
        conn.commit()


def ar_ap_summary(business_id: int) -> dict[str, float]:
    ar = invoice_register(business_id, "Customer")
    ap = invoice_register(business_id, "Supplier")
    return {
        "accounts_receivable": float(ar["outstanding"].sum()) if not ar.empty else 0.0,
        "accounts_payable": float(ap["outstanding"].sum()) if not ap.empty else 0.0,
        "overdue_receivables": float(ar.loc[ar["days_overdue"] > 0, "outstanding"].sum()) if not ar.empty else 0.0,
        "overdue_payables": float(ap.loc[ap["days_overdue"] > 0, "outstanding"].sum()) if not ap.empty else 0.0,
    }
