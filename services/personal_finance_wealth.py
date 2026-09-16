"""Wealth-management layer for NG Finance Pro personal finance.

This module keeps transfers, savings goals, debts and investments as explicit
subledgers instead of overloading single-sided cash transactions.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date

import pandas as pd

from services import personal_finance as pf


def _positive(value: float, label: str = "Amount") -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return value


def _iso(value: str, label: str = "Date") -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label} must be YYYY-MM-DD") from exc


def ensure_schema() -> None:
    pf.ensure_schema()
    with pf.connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS personal_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            from_account_id INTEGER NOT NULL,
            to_account_id INTEGER NOT NULL,
            reference TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(from_account_id) REFERENCES personal_accounts(id),
            FOREIGN KEY(to_account_id) REFERENCES personal_accounts(id),
            CHECK(from_account_id <> to_account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_personal_transfer_date ON personal_transfers(transaction_date);
        CREATE TABLE IF NOT EXISTS personal_savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            target_amount REAL NOT NULL CHECK(target_amount > 0),
            target_date TEXT,
            linked_account_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(linked_account_id) REFERENCES personal_accounts(id)
        );
        CREATE TABLE IF NOT EXISTS personal_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            principal REAL NOT NULL CHECK(principal >= 0),
            current_balance REAL NOT NULL CHECK(current_balance >= 0),
            interest_rate REAL NOT NULL DEFAULT 0 CHECK(interest_rate >= 0),
            minimum_payment REAL NOT NULL DEFAULT 0 CHECK(minimum_payment >= 0),
            due_day INTEGER,
            status TEXT NOT NULL DEFAULT 'Active',
            as_of_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS personal_investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            asset_class TEXT NOT NULL,
            cost_basis REAL NOT NULL CHECK(cost_basis >= 0),
            current_value REAL NOT NULL CHECK(current_value >= 0),
            units REAL,
            as_of_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)


def add_transfer(transaction_date: str, description: str, amount: float,
                 from_account_id: int, to_account_id: int,
                 reference: str = "", notes: str = "") -> int:
    ensure_schema(); d = _iso(transaction_date); amount = _positive(amount)
    if not description.strip(): raise ValueError("Transfer description is required")
    if int(from_account_id) == int(to_account_id): raise ValueError("Source and destination accounts must differ")
    with pf.connect() as conn:
        ids = [int(from_account_id), int(to_account_id)]
        rows = conn.execute("SELECT id FROM personal_accounts WHERE active=1 AND id IN (?,?)", ids).fetchall()
        if len(rows) != 2: raise ValueError("Both transfer accounts must exist and be active")
        cur = conn.execute("INSERT INTO personal_transfers(transaction_date,description,amount,from_account_id,to_account_id,reference,notes) VALUES (?,?,?,?,?,?,?)", (d, description.strip(), amount, from_account_id, to_account_id, reference.strip(), notes.strip()))
        return int(cur.lastrowid)


def transfers(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    ensure_schema(); sql = """
        SELECT t.*, fa.name AS from_account, ta.name AS to_account
        FROM personal_transfers t
        JOIN personal_accounts fa ON fa.id=t.from_account_id
        JOIN personal_accounts ta ON ta.id=t.to_account_id WHERE 1=1
    """; params=[]
    if start: sql += " AND t.transaction_date>=?"; params.append(start)
    if end: sql += " AND t.transaction_date<=?"; params.append(end)
    sql += " ORDER BY t.transaction_date DESC,t.id DESC"
    with pf.connect() as conn: return pd.read_sql_query(sql, conn, params=params)


def delete_transfer(transfer_id: int) -> None:
    ensure_schema()
    with pf.connect() as conn: conn.execute("DELETE FROM personal_transfers WHERE id=?", (int(transfer_id),))


def add_savings_goal(name: str, target_amount: float, target_date: str | None = None, linked_account_id: int | None = None) -> int:
    ensure_schema(); name=name.strip(); target_amount=_positive(target_amount,"Target amount")
    if not name: raise ValueError("Savings goal name is required")
    td = _iso(target_date,"Target date") if target_date else None
    with pf.connect() as conn:
        if linked_account_id is not None and not conn.execute("SELECT 1 FROM personal_accounts WHERE id=? AND active=1",(linked_account_id,)).fetchone(): raise ValueError("Linked account does not exist")
        cur=conn.execute("INSERT INTO personal_savings_goals(name,target_amount,target_date,linked_account_id) VALUES (?,?,?,?)",(name,target_amount,td,linked_account_id)); return int(cur.lastrowid)


def savings_goals(as_of: str | None = None) -> pd.DataFrame:
    ensure_schema(); as_of=as_of or date.today().isoformat()
    with pf.connect() as conn: goals=pd.read_sql_query("SELECT g.*,a.name AS linked_account FROM personal_savings_goals g LEFT JOIN personal_accounts a ON a.id=g.linked_account_id ORDER BY g.name",conn)
    if goals.empty: return goals.assign(current_amount=pd.Series(dtype=float), progress_pct=pd.Series(dtype=float))
    balances = account_balances(as_of).set_index("id")["balance"] if not account_balances(as_of).empty else pd.Series(dtype=float)
    goals["current_amount"] = goals["linked_account_id"].map(balances).fillna(0.0).clip(lower=0)
    goals["progress_pct"] = (goals["current_amount"] / goals["target_amount"] * 100).clip(upper=100)
    return goals


def add_debt(name: str, principal: float, current_balance: float, interest_rate: float = 0,
             minimum_payment: float = 0, due_day: int | None = None,
             as_of_date: str | None = None, notes: str = "") -> int:
    ensure_schema(); name=name.strip(); principal=float(principal); current_balance=float(current_balance); interest_rate=float(interest_rate); minimum_payment=float(minimum_payment)
    if not name: raise ValueError("Debt name is required")
    if not all(math.isfinite(x) and x >= 0 for x in [principal,current_balance,interest_rate,minimum_payment]): raise ValueError("Debt values must be finite and non-negative")
    if due_day is not None and not 1 <= int(due_day) <= 31: raise ValueError("Due day must be between 1 and 31")
    d=_iso(as_of_date or date.today().isoformat(),"As-of date")
    with pf.connect() as conn:
        cur=conn.execute("INSERT INTO personal_debts(name,principal,current_balance,interest_rate,minimum_payment,due_day,as_of_date,notes) VALUES (?,?,?,?,?,?,?,?)",(name,principal,current_balance,interest_rate,minimum_payment,due_day,d,notes.strip())); return int(cur.lastrowid)


def debts(as_of: str | None = None) -> pd.DataFrame:
    ensure_schema(); as_of=as_of or date.today().isoformat()
    with pf.connect() as conn: return pd.read_sql_query("SELECT * FROM personal_debts WHERE as_of_date<=? ORDER BY current_balance DESC,name",conn,params=[as_of])


def add_investment(name: str, asset_class: str, cost_basis: float, current_value: float,
                   units: float | None = None, as_of_date: str | None = None, notes: str = "") -> int:
    ensure_schema(); name=name.strip(); asset_class=asset_class.strip(); cost_basis=float(cost_basis); current_value=float(current_value)
    if not name or not asset_class: raise ValueError("Investment name and asset class are required")
    if not all(math.isfinite(x) and x >= 0 for x in [cost_basis,current_value]): raise ValueError("Investment values must be finite and non-negative")
    if units is not None and (not math.isfinite(float(units)) or float(units) < 0): raise ValueError("Units must be non-negative")
    d=_iso(as_of_date or date.today().isoformat(),"As-of date")
    with pf.connect() as conn:
        cur=conn.execute("INSERT INTO personal_investments(name,asset_class,cost_basis,current_value,units,as_of_date,notes) VALUES (?,?,?,?,?,?,?)",(name,asset_class,cost_basis,current_value,units,d,notes.strip())); return int(cur.lastrowid)


def investments(as_of: str | None = None) -> pd.DataFrame:
    ensure_schema(); as_of=as_of or date.today().isoformat()
    with pf.connect() as conn: return pd.read_sql_query("SELECT * FROM personal_investments WHERE as_of_date<=? ORDER BY current_value DESC,name",conn,params=[as_of])


def account_balances(as_of: str | None = None) -> pd.DataFrame:
    ensure_schema(); as_of=as_of or date.today().isoformat(); accts=pf.accounts().copy()
    if accts.empty: return accts.assign(balance=pd.Series(dtype=float))
    tx=pf.transactions(end=as_of)
    accts["opening_balance"]=pd.to_numeric(accts["opening_balance"],errors="coerce").fillna(0.0)
    movement=pd.Series(0.0,index=accts.index)
    if not tx.empty:
        signed=tx["amount"].astype(float).copy()
        signed.loc[tx["transaction_type"].isin(["Expense","Debt Payment","Investment"])] *= -1
        # Legacy single-sided Savings/Transfer rows are intentionally excluded;
        # new transfers are represented in personal_transfers below.
        signed.loc[tx["transaction_type"].isin(["Savings","Transfer"])] = 0.0
        tmp=pd.DataFrame({"account_id":tx["account_id"],"movement":signed}).groupby("account_id")["movement"].sum()
        movement=accts["id"].map(tmp).fillna(0.0)
    tr=transfers(end=as_of)
    if not tr.empty:
        outflow=tr.groupby("from_account_id")["amount"].sum(); inflow=tr.groupby("to_account_id")["amount"].sum()
        movement += accts["id"].map(inflow).fillna(0.0) - accts["id"].map(outflow).fillna(0.0)
    accts["movement"]=movement.astype(float); accts["balance"]=accts["opening_balance"]+accts["movement"]
    return accts


def liquid_cash(as_of: str | None = None) -> float:
    b=account_balances(as_of)
    return float(b.loc[b["account_type"].isin(["Cash","Savings"]),"balance"].sum()) if not b.empty else 0.0


def integrated_net_worth(as_of: str | None = None) -> dict:
    as_of=as_of or date.today().isoformat(); balances=account_balances(as_of)
    liquid=float(balances.loc[balances["account_type"].isin(["Cash","Savings"]),"balance"].sum()) if not balances.empty else 0.0
    # Investment-type cash accounts are excluded here because their valuation is
    # represented by the investment register, avoiding double counting.
    inv=investments(as_of); investment_value=float(inv["current_value"].sum()) if not inv.empty else 0.0
    nw=pf.net_worth(as_of)
    with pf.connect() as conn: manual=pd.read_sql_query("SELECT item_name,item_type,amount FROM personal_net_worth",conn)
    manual_assets=float(manual.loc[manual.item_type=="Asset","amount"].sum()) if not manual.empty else 0.0
    manual_liabilities=float(manual.loc[manual.item_type=="Liability","amount"].sum()) if not manual.empty else 0.0
    # Manual entries are retained for non-cash/non-investment assets and liabilities.
    assets=liquid+investment_value+manual_assets; liabilities=manual_liabilities
    debts_df=debts(as_of); debt_register=float(debts_df["current_balance"].sum()) if not debts_df.empty else 0.0
    liabilities += debt_register
    return {"assets":assets,"liabilities":liabilities,"net_worth":assets-liabilities,"liquid_cash":liquid,"investments":investment_value,"debts":debt_register,"manual_assets":manual_assets,"manual_liabilities":manual_liabilities,"status":"CALCULATION: cash/savings balances + investment register + recorded assets/liabilities + debt register"}


def emergency_coverage(start: str, end: str) -> dict:
    tx=pf.transactions(start,end)
    months=max(1,(pd.Timestamp(end)-pd.Timestamp(start)).days/30.4375)
    essential=float(tx.loc[(tx.transaction_type=="Expense")&(tx.classification=="Need"),"amount"].sum()) if not tx.empty else 0.0
    total=float(tx.loc[tx.transaction_type=="Expense","amount"].sum()) if not tx.empty else 0.0
    avg_essential=essential/months; avg_total=total/months; cash=liquid_cash(end)
    return {"liquid_cash":cash,"average_monthly_essential_expense":avg_essential,"average_monthly_total_expense":avg_total,"essential_months":cash/avg_essential if avg_essential else None,"total_expense_months":cash/avg_total if avg_total else None,"status":"CALCULATION: based on recorded liquid cash and selected-period expenses"}
