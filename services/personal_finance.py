"""Personal finance engine for NG Finance Pro.

The web/mobile product is based on the Professional Personal Finance workbook:
settings, chart of accounts, income/expense ledgers, 50/30/20 classification,
budgeting, statements, net worth and financial ratios.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/ng_finance_pro.db")
PERSONAL_TYPES = ("Income", "Expense", "Transfer", "Savings", "Debt Payment", "Investment")
CLASSIFICATIONS = ("Need", "Want", "Savings")
DEFAULT_SETTINGS = {"currency": "NGN", "symbol": "₦", "fiscal_year": date.today().year,
                    "opening_cash": 0.0, "needs_target": 0.50, "wants_target": 0.30,
                    "savings_target": 0.20, "debt_ratio_target": 0.15, "emergency_months_target": 3.0}
DEFAULT_CATEGORIES = {
    "Income": [("Salary", "Income"), ("Business", "Income"), ("Freelance", "Income"), ("Gift", "Income"), ("Investment", "Income"), ("Bonus", "Income"), ("Other", "Income")],
    "Expense": [("Food", "Need"), ("Transport", "Need"), ("Rent", "Need"), ("Utilities", "Need"), ("Internet", "Need"), ("Entertainment", "Want"), ("Shopping", "Want"), ("Health", "Need"), ("Education", "Need"), ("Family", "Need"), ("Savings", "Savings"), ("Investment", "Savings"), ("Debt Repayment", "Need"), ("Miscellaneous", "Want")],
    "Savings": [("Emergency Fund", "Savings"), ("Short-Term Savings", "Savings"), ("Long-Term Savings", "Savings")],
    "Debt Payment": [("Debt Repayment", "Need")],
    "Investment": [("Investment", "Savings")],
    "Transfer": [("Account Transfer", "Savings")],
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema() -> None:
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS personal_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS personal_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            category_type TEXT NOT NULL, classification TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS personal_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL DEFAULT 'Cash', opening_balance REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS personal_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_date TEXT NOT NULL,
            description TEXT NOT NULL, amount REAL NOT NULL CHECK(amount > 0),
            transaction_type TEXT NOT NULL, category TEXT NOT NULL, classification TEXT NOT NULL,
            account_id INTEGER NOT NULL, payment_method TEXT DEFAULT '', reference TEXT DEFAULT '',
            notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(account_id) REFERENCES personal_accounts(id)
        );
        CREATE TABLE IF NOT EXISTS personal_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT NOT NULL, category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0), UNIQUE(month, category)
        );
        CREATE TABLE IF NOT EXISTS personal_net_worth (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT NOT NULL,
            item_type TEXT NOT NULL, amount REAL NOT NULL DEFAULT 0,
            as_of_date TEXT NOT NULL, UNIQUE(item_name, item_type)
        );
        CREATE INDEX IF NOT EXISTS idx_personal_txn_date ON personal_transactions(transaction_date);
        CREATE INDEX IF NOT EXISTS idx_personal_txn_type ON personal_transactions(transaction_type);
        CREATE INDEX IF NOT EXISTS idx_personal_txn_class ON personal_transactions(classification);
        """)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO personal_settings(key,value) VALUES (?,?)", (key, str(value)))
        if conn.execute("SELECT COUNT(*) FROM personal_categories").fetchone()[0] == 0:
            rows = [(name, typ, cls) for typ, vals in DEFAULT_CATEGORIES.items() for name, cls in vals]
            conn.executemany("INSERT INTO personal_categories(name,category_type,classification) VALUES (?,?,?)", rows)
        if conn.execute("SELECT COUNT(*) FROM personal_accounts").fetchone()[0] == 0:
            conn.executemany("INSERT INTO personal_accounts(name,account_type) VALUES (?,?)", [("Main Bank","Cash"),("Cash Wallet","Cash"),("Savings","Savings"),("Investments","Investment")])


def settings() -> dict:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute("SELECT key,value FROM personal_settings").fetchall()
    out = dict(DEFAULT_SETTINGS)
    for k, v in rows:
        if k in {"fiscal_year"}: out[k] = int(float(v))
        elif k in {"opening_cash","needs_target","wants_target","savings_target","debt_ratio_target","emergency_months_target"}: out[k] = float(v)
        else: out[k] = v
    return out


def update_settings(**values) -> None:
    ensure_schema()
    allowed = set(DEFAULT_SETTINGS)
    with connect() as conn:
        for key, value in values.items():
            if key in allowed: conn.execute("INSERT OR REPLACE INTO personal_settings(key,value) VALUES (?,?)", (key, str(value)))


def categories(category_type: str | None = None) -> pd.DataFrame:
    ensure_schema()
    sql = "SELECT * FROM personal_categories WHERE active=1"; params=[]
    if category_type: sql += " AND category_type=?"; params.append(category_type)
    sql += " ORDER BY name"
    with connect() as conn: return pd.read_sql_query(sql, conn, params=params)


def accounts() -> pd.DataFrame:
    ensure_schema()
    with connect() as conn: return pd.read_sql_query("SELECT * FROM personal_accounts WHERE active=1 ORDER BY name", conn)


def add_account(name: str, account_type: str = "Cash", opening_balance: float = 0) -> int:
    ensure_schema(); name = name.strip(); amount = float(opening_balance)
    if not name or not math.isfinite(amount): raise ValueError("Valid account name and opening balance are required")
    with connect() as conn:
        cur = conn.execute("INSERT INTO personal_accounts(name,account_type,opening_balance) VALUES (?,?,?)", (name, account_type, amount))
        return int(cur.lastrowid)


def _classification(category: str) -> str:
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT classification FROM personal_categories WHERE name=? AND active=1", (category,)).fetchone()
    return row[0] if row else "Want"


def add_transaction(transaction_date: str, description: str, amount: float, transaction_type: str,
                    category: str, account_id: int, payment_method: str = "", reference: str = "", notes: str = "") -> int:
    ensure_schema()
    if transaction_type not in PERSONAL_TYPES: raise ValueError("Invalid personal transaction type")
    try: parsed = date.fromisoformat(transaction_date)
    except ValueError as exc: raise ValueError("Transaction date must be YYYY-MM-DD") from exc
    if not description.strip(): raise ValueError("Description is required")
    amount = float(amount)
    if not math.isfinite(amount) or amount <= 0: raise ValueError("Amount must be a finite positive number")
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM personal_accounts WHERE id=? AND active=1", (account_id,)).fetchone(): raise ValueError("Selected personal account does not exist")
        cls = _classification(category)
        cur = conn.execute("INSERT INTO personal_transactions(transaction_date,description,amount,transaction_type,category,classification,account_id,payment_method,reference,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (parsed.isoformat(), description.strip(), amount, transaction_type, category.strip(), cls, account_id, payment_method.strip(), reference.strip(), notes.strip()))
        return int(cur.lastrowid)


def transactions(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    ensure_schema(); sql = "SELECT t.*, a.name AS account_name FROM personal_transactions t JOIN personal_accounts a ON a.id=t.account_id WHERE 1=1"; params=[]
    if start: sql += " AND t.transaction_date>=?"; params.append(start)
    if end: sql += " AND t.transaction_date<=?"; params.append(end)
    sql += " ORDER BY t.transaction_date DESC,t.id DESC"
    with connect() as conn: return pd.read_sql_query(sql, conn, params=params)


def monthly_statement(fiscal_year: int | None = None) -> pd.DataFrame:
    year = fiscal_year or settings()["fiscal_year"]; df = transactions(f"{year}-01-01", f"{year}-12-31")
    rows=[]
    for month in range(1,13):
        m = df[pd.to_datetime(df["transaction_date"]).dt.month.eq(month)] if not df.empty else df
        income=float(m.loc[m.transaction_type=="Income","amount"].sum()) if not m.empty else 0.0
        expense=float(m.loc[m.transaction_type=="Expense","amount"].sum()) if not m.empty else 0.0
        savings=float(m.loc[m.transaction_type.isin(["Savings","Investment"]),"amount"].sum()) if not m.empty else 0.0
        debt=float(m.loc[m.transaction_type=="Debt Payment","amount"].sum()) if not m.empty else 0.0
        rows.append({"Month":pd.Timestamp(year,month,1).strftime("%B"),"Income":income,"Expenses":expense,"Net Savings":income-expense,"Savings/Investment":savings,"Debt Payments":debt,"Savings Rate":(income-expense)/income if income else None})
    return pd.DataFrame(rows)


def budget_variance(month: str | None = None) -> pd.DataFrame:
    ensure_schema(); month = month or pd.Timestamp.today().strftime("%Y-%m")
    with connect() as conn: budget=pd.read_sql_query("SELECT category,amount AS budget FROM personal_budgets WHERE month=?",conn,params=[month])
    start=f"{month}-01"; end=(pd.Timestamp(start)+pd.offsets.MonthEnd(1)).strftime("%Y-%m-%d")
    tx=transactions(start,end); actual=tx[tx.transaction_type=="Expense"].groupby("category",as_index=False)["amount"].sum().rename(columns={"amount":"actual"}) if not tx.empty else pd.DataFrame(columns=["category","actual"])
    cats=pd.DataFrame({"category":sorted(set(budget.category.tolist()+actual.category.tolist()))}) if not budget.empty or not actual.empty else pd.DataFrame(columns=["category"])
    out=cats.merge(budget,on="category",how="left").merge(actual,on="category",how="left").fillna(0); out["variance"]=out["budget"]-out["actual"]; out["variance_pct"]=out.apply(lambda r:r.variance/r.budget if r.budget else None,axis=1); out["status"]=out.apply(lambda r:"No Budget Set" if r.budget==0 else ("Over Budget" if r.actual>r.budget else ("Near Limit" if r.actual>0.9*r.budget else "Within Budget")),axis=1); return out.sort_values("actual",ascending=False)


def set_budget(month: str, category: str, amount: float) -> None:
    ensure_schema(); amount=float(amount)
    if not math.isfinite(amount) or amount<0: raise ValueError("Budget must be a non-negative finite amount")
    with connect() as conn: conn.execute("INSERT INTO personal_budgets(month,category,amount) VALUES (?,?,?) ON CONFLICT(month,category) DO UPDATE SET amount=excluded.amount",(month,category,amount))


def net_worth(as_of: str | None = None) -> dict:
    ensure_schema(); as_of=as_of or date.today().isoformat()
    with connect() as conn: nw=pd.read_sql_query("SELECT item_name,item_type,amount FROM personal_net_worth",conn)
    if nw.empty: return {"assets":0.0,"liabilities":0.0,"net_worth":0.0,"status":"CALCULATION: no asset/liability balances configured"}
    assets=float(nw.loc[nw.item_type=="Asset","amount"].sum()); liabilities=float(nw.loc[nw.item_type=="Liability","amount"].sum())
    return {"assets":assets,"liabilities":liabilities,"net_worth":assets-liabilities,"status":"CALCULATION: recorded assets and liabilities"}


def set_net_worth_item(item_name: str, item_type: str, amount: float, as_of_date: str | None = None) -> None:
    ensure_schema(); amount=float(amount); as_of_date=as_of_date or date.today().isoformat()
    if item_type not in ("Asset","Liability"): raise ValueError("Item type must be Asset or Liability")
    if not math.isfinite(amount) or amount<0: raise ValueError("Amount must be a non-negative finite number")
    with connect() as conn: conn.execute("INSERT INTO personal_net_worth(item_name,item_type,amount,as_of_date) VALUES (?,?,?,?) ON CONFLICT(item_name,item_type) DO UPDATE SET amount=excluded.amount,as_of_date=excluded.as_of_date",(item_name.strip(),item_type,amount,as_of_date))


def financial_ratios(start: str, end: str) -> dict:
    s=settings(); df=transactions(start,end); income=float(df.loc[df.transaction_type=="Income","amount"].sum()) if not df.empty else 0.0; expense=float(df.loc[df.transaction_type=="Expense","amount"].sum()) if not df.empty else 0.0
    needs=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Need"),"amount"].sum()) if not df.empty else 0.0; wants=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Want"),"amount"].sum()) if not df.empty else 0.0; savings=float(df.loc[(df.transaction_type.isin(["Savings","Investment"]))|(df.classification=="Savings"),"amount"].sum()) if not df.empty else 0.0; debt=float(df.loc[df.transaction_type=="Debt Payment","amount"].sum()) if not df.empty else 0.0
    nw=net_worth(); avg_monthly_exp=expense/max(1,(pd.Timestamp(end)-pd.Timestamp(start)).days/30.4375)
    cash_assets=nw["assets"] if nw["assets"] else s["opening_cash"]
    return {"Savings Rate": savings/income if income else None,"Expense-to-Income Ratio":expense/income if income else None,"Needs Ratio":needs/income if income else None,"Wants Ratio":wants/income if income else None,"Savings/Investment Ratio":savings/income if income else None,"Debt Repayment Ratio":debt/income if income else None,"Emergency Fund Coverage (months)":cash_assets/avg_monthly_exp if avg_monthly_exp else None,"Net Worth":nw["net_worth"]}


def dashboard_metrics(start: str, end: str) -> dict:
    df=transactions(start,end); income=float(df.loc[df.transaction_type=="Income","amount"].sum()) if not df.empty else 0.0; expenses=float(df.loc[df.transaction_type=="Expense","amount"].sum()) if not df.empty else 0.0; savings=float(df.loc[df.transaction_type.isin(["Savings","Investment"]),"amount"].sum()) if not df.empty else 0.0; debt=float(df.loc[df.transaction_type=="Debt Payment","amount"].sum()) if not df.empty else 0.0
    return {"income":income,"expenses":expenses,"net_cash_flow":income-expenses-savings-debt,"savings":savings,"investments":float(df.loc[df.transaction_type=="Investment","amount"].sum()) if not df.empty else 0.0,"debt_payments":debt,"savings_rate":savings/income*100 if income else None,"transaction_count":int(len(df))}


def spending_by_category(start: str, end: str) -> pd.DataFrame:
    df=transactions(start,end)
    if df.empty: return pd.DataFrame(columns=["category","amount","classification"])
    out=df[df.transaction_type=="Expense"].groupby(["category","classification"],as_index=False)["amount"].sum(); return out.sort_values("amount",ascending=False)
