"""Recurring personal-finance obligations and income rules."""
from __future__ import annotations
import calendar
import math
import sqlite3
from datetime import date, timedelta
import pandas as pd
from services import personal_finance as pf

FREQUENCIES=("Monthly","Quarterly","Yearly")

def ensure_schema():
    pf.ensure_schema()
    with pf.connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS personal_recurring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            transaction_type TEXT NOT NULL,
            category TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            frequency TEXT NOT NULL,
            next_due_date TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(account_id) REFERENCES personal_accounts(id)
        );
        CREATE TABLE IF NOT EXISTS personal_recurring_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recurring_id INTEGER NOT NULL,
            transaction_id INTEGER NOT NULL UNIQUE,
            due_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(recurring_id) REFERENCES personal_recurring(id),
            FOREIGN KEY(transaction_id) REFERENCES personal_transactions(id)
        );
        CREATE INDEX IF NOT EXISTS idx_personal_recurring_due ON personal_recurring(next_due_date);
        """)

def _date(value):
    try: return date.fromisoformat(str(value))
    except ValueError as exc: raise ValueError("Date must be YYYY-MM-DD") from exc

def _amount(value):
    value=float(value)
    if not math.isfinite(value) or value<=0: raise ValueError("Amount must be a finite positive number")
    return value

def add_rule(description, amount, transaction_type, category, account_id, frequency, next_due_date, notes=""):
    ensure_schema()
    if transaction_type not in pf.PERSONAL_TYPES: raise ValueError("Invalid transaction type")
    if frequency not in FREQUENCIES: raise ValueError("Invalid frequency")
    d=_date(next_due_date); amount=_amount(amount)
    if not description.strip(): raise ValueError("Description is required")
    with pf.connect() as conn:
        if not conn.execute("SELECT 1 FROM personal_accounts WHERE id=? AND active=1",(int(account_id),)).fetchone():
            raise ValueError("Account does not exist or is inactive")
        cur=conn.execute("""INSERT INTO personal_recurring(description,amount,transaction_type,category,account_id,frequency,next_due_date,notes)
                            VALUES (?,?,?,?,?,?,?,?)""",
                         (description.strip(),amount,transaction_type,category.strip(),int(account_id),frequency,d.isoformat(),notes.strip()))
        return int(cur.lastrowid)

def rules(active_only=True):
    ensure_schema()
    where="WHERE r.active=1" if active_only else ""
    with pf.connect() as conn:
        return pd.read_sql_query(f"""SELECT r.*,a.name account_name FROM personal_recurring r
                                     JOIN personal_accounts a ON a.id=r.account_id {where}
                                     ORDER BY r.next_due_date,r.id""",conn)

def delete_rule(rule_id):
    ensure_schema()
    with pf.connect() as conn:
        row=conn.execute("SELECT id FROM personal_recurring WHERE id=?",(int(rule_id),)).fetchone()
        if not row: raise ValueError("Recurring rule not found")
        conn.execute("UPDATE personal_recurring SET active=0 WHERE id=?",(int(rule_id),))

def _next_due(d, frequency):
    if frequency=="Monthly":
        y=d.year+(d.month//12); m=d.month%12+1
        return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
    if frequency=="Quarterly":
        total=d.year*12+(d.month-1)+3; y,m=divmod(total,12); m+=1
        return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
    return date(d.year+1,d.month,d.day if d.day<=calendar.monthrange(d.year+1,d.month)[1] else calendar.monthrange(d.year+1,d.month)[1])

def due_rules(as_of=None):
    as_of=_date(as_of or date.today().isoformat())
    df=rules()
    if df.empty: return df
    df["next_due_date"]=pd.to_datetime(df["next_due_date"]).dt.date
    return df[df["next_due_date"]<=as_of].copy()

def post_due(as_of=None):
    as_of=_date(as_of or date.today().isoformat())
    posted=[]
    for row in due_rules(as_of).itertuples():
        due=row.next_due_date
        while due<=as_of:
            with pf.connect() as conn:
                exists=conn.execute("SELECT 1 FROM personal_recurring_postings WHERE recurring_id=? AND due_date=?",(row.id,due.isoformat())).fetchone()
            if not exists:
                tx_id=pf.add_transaction(due.isoformat(),row.description,row.amount,row.transaction_type,row.category,row.account_id,notes=f"Recurring rule #{row.id}")
                with pf.connect() as conn:
                    conn.execute("INSERT INTO personal_recurring_postings(recurring_id,transaction_id,due_date) VALUES (?,?,?)",(row.id,tx_id,due.isoformat()))
                posted.append(tx_id)
            due=_next_due(due,row.frequency)
        with pf.connect() as conn:
            conn.execute("UPDATE personal_recurring SET next_due_date=? WHERE id=?",(due.isoformat(),row.id))
    return posted
