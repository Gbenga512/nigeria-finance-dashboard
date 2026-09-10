"""SME budget storage and actual-vs-budget variance calculations."""
from __future__ import annotations

import pandas as pd

from services.sme_store import connect, init_db
from services.sme_accounting import trial_balance

SCHEMA = """
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Draft','Active','Closed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS budget_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    FOREIGN KEY(budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
    UNIQUE(budget_id, account_id)
);
CREATE INDEX IF NOT EXISTS idx_budget_business_period ON budgets(business_id, period_start, period_end);
"""


def ensure_budget_schema() -> None:
    init_db()
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def create_budget(business_id: int, name: str, period_start, period_end, lines: list[dict], status: str = "Active") -> int:
    ensure_budget_schema()
    if not str(name).strip() or pd.Timestamp(period_end) < pd.Timestamp(period_start):
        raise ValueError("Budget name and a valid reporting period are required.")
    if status not in {"Draft", "Active", "Closed"}:
        raise ValueError("Unsupported budget status.")
    with connect() as conn:
        account_ids = [int(x["account_id"]) for x in lines]
        if account_ids:
            placeholders = ",".join("?" for _ in account_ids)
            valid = conn.execute(f"SELECT id FROM accounts WHERE business_id=? AND id IN ({placeholders})", [business_id, *account_ids]).fetchall()
            if len(valid) != len(set(account_ids)):
                raise ValueError("Every budget account must belong to the active business.")
        cur = conn.execute("INSERT INTO budgets(business_id,name,period_start,period_end,status) VALUES(?,?,?,?,?)", (business_id, str(name).strip(), str(period_start), str(period_end), status))
        budget_id = int(cur.lastrowid)
        conn.executemany("INSERT INTO budget_lines(budget_id,account_id,amount) VALUES(?,?,?)", [(budget_id, int(x["account_id"]), float(x["amount"])) for x in lines])
        conn.commit()
        return budget_id


def list_budgets(business_id: int) -> pd.DataFrame:
    ensure_budget_schema()
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM budgets WHERE business_id=? ORDER BY period_start DESC,id DESC", conn, params=(business_id,))


def variance_report(business_id: int, budget_id: int) -> pd.DataFrame:
    ensure_budget_schema()
    with connect() as conn:
        budget = conn.execute("SELECT * FROM budgets WHERE id=? AND business_id=?", (budget_id, business_id)).fetchone()
        if not budget:
            raise ValueError("Budget not found for this business.")
        lines = pd.read_sql_query("SELECT bl.account_id, a.name AS Account, a.account_type, bl.amount AS Budget FROM budget_lines bl JOIN accounts a ON a.id=bl.account_id WHERE bl.budget_id=? ORDER BY a.name", conn, params=(budget_id,))
    tb = trial_balance(business_id, budget["period_start"], budget["period_end"])
    actual = tb[["account_id", "Balance", "Type"]].copy() if not tb.empty else pd.DataFrame(columns=["account_id", "Balance", "Type"])
    actual["Actual"] = actual["Balance"].abs() if not actual.empty else pd.Series(dtype=float)
    out = lines.merge(actual[["account_id", "Actual", "Type"]], on="account_id", how="left").fillna({"Actual": 0.0})
    out["Variance"] = out["Actual"] - out["Budget"]
    out["Variance %"] = out.apply(lambda r: (r["Variance"] / r["Budget"] * 100) if r["Budget"] else None, axis=1)
    out["Direction"] = out.apply(lambda r: "Over budget" if r["Variance"] > 0 else ("Under budget" if r["Variance"] < 0 else "On budget"), axis=1)
    return out[["account_id", "Account", "Type", "Budget", "Actual", "Variance", "Variance %", "Direction"]]
