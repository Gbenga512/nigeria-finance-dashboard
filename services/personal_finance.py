"""Personal finance tracking engine for NG Finance Pro.

This module is intentionally separate from SME double-entry accounting. It stores
personal cash-management records that can later feed budgeting, savings, debt,
net-worth and investment views without contaminating a business ledger.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/ng_finance_pro.db")
PERSONAL_TYPES = ("Income", "Expense", "Transfer", "Savings", "Debt Payment", "Investment")

DEFAULT_CATEGORIES = {
    "Income": ["Salary", "Business Income", "Freelance", "Interest", "Dividend", "Other Income"],
    "Expense": ["Food", "Housing", "Transport", "Utilities", "Education", "Healthcare", "Family", "Entertainment", "Other Expense"],
    "Savings": ["Emergency Fund", "Short-Term Savings", "Long-Term Savings"],
    "Debt Payment": ["Loan Principal", "Loan Interest", "Credit Payment"],
    "Investment": ["Equities", "Money Market", "Bonds", "Treasury Bills", "Mutual Funds", "Other Investment"],
    "Transfer": ["Account Transfer"],
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS personal_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL DEFAULT 'Cash',
                opening_balance REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS personal_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                reference TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(account_id) REFERENCES personal_accounts(id)
            );
            CREATE TABLE IF NOT EXISTS personal_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                UNIQUE(month, category)
            );
            CREATE INDEX IF NOT EXISTS idx_personal_txn_date ON personal_transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_personal_txn_type ON personal_transactions(transaction_type);
            """
        )
        if conn.execute("SELECT COUNT(*) FROM personal_accounts").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO personal_accounts(name, account_type) VALUES (?, ?)",
                [("Main Bank", "Cash"), ("Cash Wallet", "Cash"), ("Savings", "Savings"), ("Investments", "Investment")],
            )


def accounts() -> pd.DataFrame:
    ensure_schema()
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM personal_accounts WHERE active=1 ORDER BY name", conn)


def add_transaction(transaction_date: str, description: str, amount: float, transaction_type: str,
                    category: str, account_id: int, reference: str = "", notes: str = "") -> int:
    ensure_schema()
    if transaction_type not in PERSONAL_TYPES:
        raise ValueError("Invalid personal transaction type")
    try:
        parsed = date.fromisoformat(transaction_date)
    except ValueError as exc:
        raise ValueError("Transaction date must be YYYY-MM-DD") from exc
    if not description.strip():
        raise ValueError("Description is required")
    amount = float(amount)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a finite positive number")
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM personal_accounts WHERE id=? AND active=1", (account_id,)).fetchone()
        if not exists:
            raise ValueError("Selected personal account does not exist")
        cur = conn.execute(
            """INSERT INTO personal_transactions
               (transaction_date, description, amount, transaction_type, category, account_id, reference, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (parsed.isoformat(), description.strip(), amount, transaction_type, category.strip(), account_id, reference.strip(), notes.strip()),
        )
        return int(cur.lastrowid)


def transactions(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    ensure_schema()
    sql = """SELECT t.*, a.name AS account_name
             FROM personal_transactions t JOIN personal_accounts a ON a.id=t.account_id
             WHERE 1=1"""
    params: list[str] = []
    if start:
        sql += " AND t.transaction_date >= ?"; params.append(start)
    if end:
        sql += " AND t.transaction_date <= ?"; params.append(end)
    sql += " ORDER BY t.transaction_date DESC, t.id DESC"
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def dashboard_metrics(start: str, end: str) -> dict:
    df = transactions(start, end)
    income = float(df.loc[df.transaction_type == "Income", "amount"].sum()) if not df.empty else 0.0
    expenses = float(df.loc[df.transaction_type == "Expense", "amount"].sum()) if not df.empty else 0.0
    savings = float(df.loc[df.transaction_type == "Savings", "amount"].sum()) if not df.empty else 0.0
    investments = float(df.loc[df.transaction_type == "Investment", "amount"].sum()) if not df.empty else 0.0
    debt = float(df.loc[df.transaction_type == "Debt Payment", "amount"].sum()) if not df.empty else 0.0
    return {
        "income": income,
        "expenses": expenses,
        "net_cash_flow": income - expenses - savings - investments - debt,
        "savings": savings,
        "investments": investments,
        "debt_payments": debt,
        "savings_rate": (savings / income * 100) if income else None,
        "transaction_count": int(len(df)),
    }


def spending_by_category(start: str, end: str) -> pd.DataFrame:
    df = transactions(start, end)
    if df.empty:
        return pd.DataFrame(columns=["category", "amount"])
    out = df[df.transaction_type == "Expense"].groupby("category", as_index=False)["amount"].sum()
    return out.sort_values("amount", ascending=False)


def net_worth() -> dict:
    ensure_schema()
    # Phase 1 tracks cash/savings/investment contributions and debt payments.
    # Asset/debt opening balances will be added when the full Excel specification is mapped.
    df = transactions()
    cash_movement = 0.0
    if not df.empty:
        cash_movement = float(df.loc[df.transaction_type == "Income", "amount"].sum())
        cash_movement -= float(df.loc[df.transaction_type.isin(["Expense", "Savings", "Investment", "Debt Payment"]), "amount"].sum())
    return {"tracked_cash_movement": cash_movement, "status": "CALCULATION: transaction-based; opening balances/assets/liabilities not yet configured"}
