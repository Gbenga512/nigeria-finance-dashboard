"""Persistent local store for the NG Finance Pro SME finance module."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "ng_finance_sme.db"
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, external_id TEXT UNIQUE, email TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, industry TEXT, business_type TEXT, cac_number TEXT, tin TEXT, location TEXT, employees INTEGER, financial_year_end TEXT, revenue_range TEXT, accounting_basis TEXT NOT NULL DEFAULT 'Accrual', currency TEXT NOT NULL DEFAULT 'NGN', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, name TEXT NOT NULL, account_type TEXT NOT NULL, opening_balance REAL NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE, UNIQUE(business_id, name));
CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, transaction_date TEXT NOT NULL, description TEXT NOT NULL, amount REAL NOT NULL, transaction_type TEXT NOT NULL CHECK(transaction_type IN ('Income','Expense','Transfer','Receipt','Supplier Payment')), category TEXT, account_id INTEGER, counterparty TEXT, reference TEXT, payment_method TEXT, tax_amount REAL, notes TEXT, attachment_path TEXT, import_key TEXT, source TEXT NOT NULL DEFAULT 'Manual', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE, FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS idx_business_transactions_date ON transactions(business_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_business_transactions_type ON transactions(business_id, transaction_type);
CREATE INDEX IF NOT EXISTS idx_business_transactions_import ON transactions(business_id, import_key);
"""

def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(path: Path | str = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        # Backward-compatible additions for databases created by Phase 1.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()}
        if "import_key" not in cols: conn.execute("ALTER TABLE transactions ADD COLUMN import_key TEXT")
        if "source" not in cols: conn.execute("ALTER TABLE transactions ADD COLUMN source TEXT NOT NULL DEFAULT 'Manual'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_business_transactions_import ON transactions(business_id, import_key)")
        conn.commit()

def get_or_create_user(external_id: str = "local-user", email: str = "") -> int:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE external_id=?", (external_id,)).fetchone()
        if row: return int(row["id"])
        return int(conn.execute("INSERT INTO users(external_id,email) VALUES(?,?)", (external_id,email)).lastrowid)

def list_businesses(user_id: int) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn: return [dict(r) for r in conn.execute("SELECT * FROM businesses WHERE user_id=? ORDER BY name", (user_id,)).fetchall()]

def create_business(user_id: int, name: str, **fields: Any) -> int:
    init_db(); clean_name=name.strip()
    if not clean_name: raise ValueError("Business name is required.")
    allowed={"industry","business_type","cac_number","tin","location","employees","financial_year_end","revenue_range","accounting_basis","currency"}; data={k:v for k,v in fields.items() if k in allowed}
    columns=["user_id","name"]+list(data); values=[user_id,clean_name]+[data[k] for k in data]
    with connect() as conn:
        cur=conn.execute(f"INSERT INTO businesses({','.join(columns)}) VALUES({','.join('?' for _ in values)})", values); business_id=int(cur.lastrowid)
        conn.executemany("INSERT OR IGNORE INTO accounts(business_id,name,account_type) VALUES(?,?,?)", [(business_id,"Main Bank","Cash"),(business_id,"Cash on Hand","Cash"),(business_id,"Accounts Receivable","Receivable"),(business_id,"Accounts Payable","Payable")]); return business_id

def list_accounts(business_id: int) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn: return [dict(r) for r in conn.execute("SELECT * FROM accounts WHERE business_id=? AND active=1 ORDER BY name", (business_id,)).fetchall()]

def add_transaction(business_id: int, transaction_date: str, description: str, amount: float, transaction_type: str, **fields: Any) -> int:
    if transaction_type not in {"Income","Expense","Transfer","Receipt","Supplier Payment"}: raise ValueError("Unsupported transaction type.")
    if not description.strip() or amount<=0: raise ValueError("A description and positive transaction amount are required.")
    allowed={"category","account_id","counterparty","reference","payment_method","tax_amount","notes","attachment_path","import_key","source"}; data={k:v for k,v in fields.items() if k in allowed}
    columns=["business_id","transaction_date","description","amount","transaction_type"]+list(data); values=[business_id,transaction_date,description.strip(),float(amount),transaction_type]+[data[k] for k in data]
    with connect() as conn:
        if data.get("import_key"):
            existing=conn.execute("SELECT id FROM transactions WHERE business_id=? AND import_key=?", (business_id,data["import_key"])).fetchone()
            if existing: return int(existing["id"])
        return int(conn.execute(f"INSERT INTO transactions({','.join(columns)}) VALUES({','.join('?' for _ in values)})", values).lastrowid)

def transactions_df(business_id: int):
    import pandas as pd
    init_db()
    with connect() as conn: return pd.read_sql_query("SELECT * FROM transactions WHERE business_id=? ORDER BY transaction_date DESC,id DESC", conn, params=(business_id,), parse_dates=["transaction_date"])

def bulk_add_transactions(business_id: int, rows: list[dict[str, Any]]) -> int:
    """Post only explicitly reviewed rows; duplicate import keys are ignored."""
    posted=0
    for row in rows:
        try:
            before=transactions_df(business_id)
            add_transaction(business_id, row["transaction_date"], row["description"], float(row["amount"]), row["transaction_type"], category=row.get("category",""), reference=row.get("reference",""), import_key=row.get("import_key"), source="Bank statement")
            after=transactions_df(business_id)
            posted += max(0, len(after)-len(before))
        except (KeyError, ValueError, TypeError):
            continue
    return posted
