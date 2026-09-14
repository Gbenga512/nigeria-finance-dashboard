"""IFRS-oriented period-end adjustment controls.

Adjustments require explicit finance-user inputs and are posted only after review.
"""
from __future__ import annotations
import math
from datetime import date
from services.sme_store import connect, init_db
from services.sme_accounting import ensure_standard_accounts, post_journal_entry

ADJUSTMENT_TYPES = {"Accrual", "Prepayment", "Depreciation", "Provision", "Inventory/COGS", "Tax"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS ifrs_adjustments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL,
 adjustment_type TEXT NOT NULL, adjustment_date TEXT NOT NULL,
 description TEXT NOT NULL, amount REAL NOT NULL CHECK(amount > 0),
 debit_account_id INTEGER NOT NULL, credit_account_id INTEGER NOT NULL,
 reference TEXT, status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Posted','Voided')),
 journal_entry_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,
 FOREIGN KEY(debit_account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
 FOREIGN KEY(credit_account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
 FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_ifrs_adjustments_business_date ON ifrs_adjustments(business_id,adjustment_date,status);
"""

def ensure_adjustment_schema() -> None:
    init_db()
    with connect() as conn: conn.executescript(SCHEMA); conn.commit()

def _amount(value: float) -> float:
    x=float(value)
    if not math.isfinite(x) or x<=0: raise ValueError("Adjustment amount must be a finite amount greater than zero.")
    return round(x,2)

def _date(value: str|date) -> str:
    try: return date.fromisoformat(str(value)).isoformat()
    except (TypeError,ValueError) as exc: raise ValueError("Adjustment date must be a valid date (YYYY-MM-DD).") from exc

def create_adjustment(business_id:int, adjustment_type:str, adjustment_date:str|date, description:str, amount:float, debit_account_id:int, credit_account_id:int, reference:str="") -> int:
    ensure_adjustment_schema(); ensure_standard_accounts(business_id)
    if adjustment_type not in ADJUSTMENT_TYPES: raise ValueError("Unsupported IFRS adjustment type.")
    if not str(description).strip(): raise ValueError("Adjustment description is required.")
    if int(debit_account_id)==int(credit_account_id): raise ValueError("Debit and credit accounts must be different.")
    amount=_amount(amount); adjustment_date=_date(adjustment_date)
    with connect() as conn:
        ids={int(r["id"]) for r in conn.execute("SELECT id FROM accounts WHERE business_id=? AND active=1",(business_id,)).fetchall()}
        if debit_account_id not in ids or credit_account_id not in ids: raise ValueError("Adjustment accounts must belong to the active business.")
        cur=conn.execute("INSERT INTO ifrs_adjustments(business_id,adjustment_type,adjustment_date,description,amount,debit_account_id,credit_account_id,reference) VALUES(?,?,?,?,?,?,?,?)",(business_id,adjustment_type,adjustment_date,str(description).strip(),amount,debit_account_id,credit_account_id,reference))
        conn.commit(); return int(cur.lastrowid)

def post_adjustment(business_id:int, adjustment_id:int) -> int:
    ensure_adjustment_schema()
    with connect() as conn:
        row=conn.execute("SELECT * FROM ifrs_adjustments WHERE id=? AND business_id=?",(adjustment_id,business_id)).fetchone()
        if not row: raise ValueError("Adjustment was not found for the active business.")
        if row["status"]=="Voided": raise ValueError("Voided adjustments cannot be posted.")
        if row["journal_entry_id"]: return int(row["journal_entry_id"])
    jid=post_journal_entry(business_id,row["adjustment_date"],row["description"],[{"account_id":row["debit_account_id"],"debit":row["amount"]},{"account_id":row["credit_account_id"],"credit":row["amount"]}],reference=row["reference"] or f"IFRS-ADJ:{adjustment_id}",source=f"IFRS adjustment: {row['adjustment_type']}")
    with connect() as conn:
        conn.execute("UPDATE ifrs_adjustments SET status='Posted',journal_entry_id=? WHERE id=? AND business_id=?",(jid,adjustment_id,business_id)); conn.commit()
    return jid

def adjustment_register(business_id:int):
    import pandas as pd
    ensure_adjustment_schema()
    with connect() as conn:
        return pd.read_sql_query("""SELECT ia.id,ia.adjustment_type,ia.adjustment_date,ia.description,ia.amount,da.name AS debit_account,ca.name AS credit_account,ia.reference,ia.status,ia.journal_entry_id FROM ifrs_adjustments ia JOIN accounts da ON da.id=ia.debit_account_id JOIN accounts ca ON ca.id=ia.credit_account_id WHERE ia.business_id=? ORDER BY date(ia.adjustment_date) DESC,ia.id DESC""",conn,params=[business_id],parse_dates=["adjustment_date"])
