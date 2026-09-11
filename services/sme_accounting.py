"""Double-entry accounting engine for the NG Finance Pro SME workspace."""
from __future__ import annotations

from datetime import date
import pandas as pd

from services.sme_store import connect, init_db

STANDARD_ACCOUNTS = [
    ("1000", "Main Bank", "Asset"),
    ("1010", "Cash on Hand", "Asset"),
    ("1100", "Accounts Receivable", "Asset"),
    ("1200", "Inventory", "Asset"),
    ("2000", "Accounts Payable", "Liability"),
    ("2100", "Tax Payable", "Liability"),
    ("3000", "Owner's Equity", "Equity"),
    ("3100", "Retained Earnings", "Equity"),
    ("4000", "Sales Revenue", "Revenue"),
    ("5000", "Cost of Goods Sold", "Expense"),
    ("6000", "Payroll", "Expense"),
    ("6100", "Rent", "Expense"),
    ("6200", "Utilities", "Expense"),
    ("6300", "Transport", "Expense"),
    ("6400", "Bank Charges", "Expense"),
    ("6500", "Tax Expense", "Expense"),
    ("6900", "Operating Expenses", "Expense"),
]


def ensure_accounting_schema() -> None:
    init_db()
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            description TEXT NOT NULL,
            reference TEXT,
            source TEXT NOT NULL DEFAULT 'Manual',
            source_transaction_id INTEGER UNIQUE,
            status TEXT NOT NULL DEFAULT 'Posted' CHECK(status IN ('Posted','Void')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            description TEXT,
            debit REAL NOT NULL DEFAULT 0 CHECK(debit >= 0),
            credit REAL NOT NULL DEFAULT 0 CHECK(credit >= 0),
            FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
            CHECK(NOT (debit > 0 AND credit > 0)),
            CHECK(debit > 0 OR credit > 0)
        );
        CREATE INDEX IF NOT EXISTS idx_journal_business_date ON journal_entries(business_id, entry_date);
        CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON journal_lines(journal_entry_id);
        """)
        conn.commit()


def ensure_standard_accounts(business_id: int) -> None:
    """Add missing standard accounts without changing existing balances or data."""
    ensure_accounting_schema()
    with connect() as conn:
        existing = {r["name"] for r in conn.execute("SELECT name FROM accounts WHERE business_id=?", (business_id,)).fetchall()}
        rows = [(business_id, name, kind) for _, name, kind in STANDARD_ACCOUNTS if name not in existing]
        if rows:
            conn.executemany("INSERT INTO accounts(business_id,name,account_type) VALUES(?,?,?)", rows)
            conn.commit()


def _statement_type(account_type: str) -> str:
    return {
        "Cash": "Asset", "Receivable": "Asset", "Payable": "Liability",
        "Asset": "Asset", "Liability": "Liability", "Equity": "Equity",
        "Revenue": "Revenue", "Expense": "Expense",
    }.get(str(account_type), str(account_type))


def account_catalog(business_id: int) -> pd.DataFrame:
    ensure_standard_accounts(business_id)
    with connect() as conn:
        rows = conn.execute("SELECT id,name,account_type,opening_balance,active FROM accounts WHERE business_id=? AND active=1 ORDER BY name", (business_id,)).fetchall()
    out = pd.DataFrame([dict(r) for r in rows])
    if not out.empty:
        out["statement_type"] = out["account_type"].map(_statement_type)
    return out


def _assert_business_accounts(conn, business_id: int, account_ids: list[int]) -> None:
    if not account_ids:
        raise ValueError("A journal entry needs at least two account lines.")
    placeholders = ",".join("?" for _ in account_ids)
    rows = conn.execute(f"SELECT id FROM accounts WHERE business_id=? AND id IN ({placeholders})", [business_id, *account_ids]).fetchall()
    if len(rows) != len(set(account_ids)):
        raise ValueError("Every journal account must belong to the active business.")


def post_journal_entry(business_id: int, entry_date: str | date, description: str, lines: list[dict], reference: str = "", source: str = "Manual", source_transaction_id: int | None = None) -> int:
    """Atomically post a balanced journal entry; refuses any unbalanced entry."""
    ensure_accounting_schema()
    if not str(description).strip() or len(lines) < 2:
        raise ValueError("Description and at least two journal lines are required.")
    clean = []
    total_debit = total_credit = 0.0
    for line in lines:
        account_id = int(line["account_id"])
        debit = round(float(line.get("debit", 0) or 0), 2)
        credit = round(float(line.get("credit", 0) or 0), 2)
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise ValueError("Each line must contain either a positive debit or a positive credit, not both.")
        clean.append((account_id, str(line.get("description", "")), debit, credit))
        total_debit += debit; total_credit += credit
    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(f"Journal is not balanced: debits ₦{total_debit:,.2f} vs credits ₦{total_credit:,.2f}.")
    if total_debit <= 0:
        raise ValueError("Journal amount must be greater than zero.")
    try:
        date.fromisoformat(str(entry_date))
    except (TypeError, ValueError):
        raise ValueError("Journal entry date must be a valid ISO date (YYYY-MM-DD).")
    with connect() as conn:
        _assert_business_accounts(conn, business_id, [x[0] for x in clean])
        if source_transaction_id is not None:
            existing = conn.execute("SELECT id FROM journal_entries WHERE source_transaction_id=?", (source_transaction_id,)).fetchone()
            if existing:
                return int(existing["id"])
        cur = conn.execute("INSERT INTO journal_entries(business_id,entry_date,description,reference,source,source_transaction_id) VALUES(?,?,?,?,?,?)", (business_id, str(entry_date), str(description).strip(), reference, source, source_transaction_id))
        entry_id = int(cur.lastrowid)
        conn.executemany("INSERT INTO journal_lines(journal_entry_id,account_id,description,debit,credit) VALUES(?,?,?,?,?)", [(entry_id, *x) for x in clean])
        conn.commit()
        return entry_id


def journal_entries_df(business_id: int, start=None, end=None) -> pd.DataFrame:
    ensure_accounting_schema()
    sql = """SELECT je.id, je.entry_date, je.description, je.reference, je.source, je.status,
                     jl.account_id, a.name AS account, a.account_type, jl.description AS line_description,
                     jl.debit, jl.credit
              FROM journal_entries je JOIN journal_lines jl ON jl.journal_entry_id=je.id
              JOIN accounts a ON a.id=jl.account_id
              WHERE je.business_id=? AND je.status='Posted'"""
    params = [business_id]
    if start is not None: sql += " AND date(je.entry_date)>=date(?)"; params.append(str(start))
    if end is not None: sql += " AND date(je.entry_date)<=date(?)"; params.append(str(end))
    sql += " ORDER BY date(je.entry_date), je.id, jl.id"
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params, parse_dates=["entry_date"])


def trial_balance(business_id: int, start=None, end=None) -> pd.DataFrame:
    ensure_standard_accounts(business_id)
    df = journal_entries_df(business_id, start, end)
    accounts = account_catalog(business_id)[["id", "name", "statement_type", "opening_balance"]].rename(columns={"id": "account_id", "name": "Account", "statement_type": "Type"})
    if df.empty:
        out = accounts.copy(); out["Debits"] = 0.0; out["Credits"] = 0.0; out["Balance"] = out["opening_balance"].astype(float)
        return out[["account_id", "Account", "Type", "Debits", "Credits", "Balance"]]
    grouped = df.groupby("account_id", as_index=False).agg(Debits=("debit", "sum"), Credits=("credit", "sum"))
    out = accounts.merge(grouped, on="account_id", how="left").fillna({"Debits": 0.0, "Credits": 0.0})
    out["Balance"] = out["opening_balance"].astype(float) + out["Debits"] - out["Credits"]
    return out[["account_id", "Account", "Type", "Debits", "Credits", "Balance"]]


def profit_and_loss(business_id: int, start=None, end=None) -> dict:
    tb = trial_balance(business_id, start, end)
    revenue = float(tb.loc[tb["Type"] == "Revenue", "Credits"].sum() - tb.loc[tb["Type"] == "Revenue", "Debits"].sum())
    expenses = float(tb.loc[tb["Type"] == "Expense", "Debits"].sum() - tb.loc[tb["Type"] == "Expense", "Credits"].sum())
    return {"Revenue": revenue, "Expenses": expenses, "Net Income": revenue - expenses}


def balance_sheet(business_id: int, end=None) -> dict:
    tb = trial_balance(business_id, None, end)
    assets = float(tb.loc[tb["Type"] == "Asset", "Balance"].sum())
    liabilities = float(-tb.loc[tb["Type"] == "Liability", "Balance"].sum())
    equity = float(-tb.loc[tb["Type"] == "Equity", "Balance"].sum())
    pnl = profit_and_loss(business_id, None, end)
    equity_with_profit = equity + pnl["Net Income"]
    return {"Assets": assets, "Liabilities": liabilities, "Equity": equity_with_profit, "Liabilities + Equity": liabilities + equity_with_profit, "Balanced": bool(abs(assets - (liabilities + equity_with_profit)) < 0.01)}


def cash_flow(business_id: int, start=None, end=None) -> pd.DataFrame:
    """Build a direct cash-flow view and classify each cash movement by its counter-account."""
    df = journal_entries_df(business_id, start, end)
    accounts = account_catalog(business_id)
    cash_ids = set(accounts.loc[accounts["name"].isin(["Main Bank", "Cash on Hand"]), "id"].astype(int))
    type_map = {int(r["id"]): r["statement_type"] for _, r in accounts.iterrows()}
    if df.empty or not cash_ids:
        return pd.DataFrame(columns=["Section", "Cash Inflow", "Cash Outflow", "Net Cash Flow"])

    totals = {"Operating": [0.0, 0.0], "Investing": [0.0, 0.0], "Financing": [0.0, 0.0]}
    for _, entry in df.groupby("id", sort=False):
        cash_lines = entry[entry["account_id"].isin(cash_ids)]
        noncash_types = {_statement_type(type_map.get(int(account_id), "Unknown")) for account_id in entry.loc[~entry["account_id"].isin(cash_ids), "account_id"]}
        if cash_lines.empty or not noncash_types:
            continue
        if noncash_types & {"Revenue", "Expense"}:
            section = "Operating"
        elif noncash_types & {"Liability", "Equity"}:
            section = "Financing"
        elif noncash_types & {"Asset"}:
            section = "Investing"
        else:
            section = "Operating"
        totals[section][0] += float(cash_lines["debit"].sum())
        totals[section][1] += float(cash_lines["credit"].sum())

    rows = [{"Section": section, "Cash Inflow": inflow, "Cash Outflow": outflow, "Net Cash Flow": inflow - outflow} for section, (inflow, outflow) in totals.items() if inflow or outflow]
    return pd.DataFrame(rows, columns=["Section", "Cash Inflow", "Cash Outflow", "Net Cash Flow"])


def sync_transaction(business_id: int, transaction_id: int) -> int | None:
    """Convert a categorized cash transaction into a balanced journal. Transfers are deferred."""
    ensure_standard_accounts(business_id)
    with connect() as conn:
        tx = conn.execute("SELECT * FROM transactions WHERE id=? AND business_id=?", (transaction_id, business_id)).fetchone()
        if not tx:
            raise ValueError("Transaction not found for this business.")
        if tx["transaction_type"] == "Transfer":
            return None
        existing = conn.execute("SELECT id FROM journal_entries WHERE source_transaction_id=?", (transaction_id,)).fetchone()
        if existing:
            return int(existing["id"])
        accounts = {r["name"]: int(r["id"]) for r in conn.execute("SELECT id,name FROM accounts WHERE business_id=?", (business_id,)).fetchall()}
        account_row = conn.execute("SELECT name FROM accounts WHERE id=? AND business_id=?", (tx["account_id"], business_id)).fetchone()
        cash_name = account_row["name"] if account_row and account_row["name"] in {"Main Bank", "Cash on Hand"} else "Main Bank"
        cash_id = accounts[cash_name]
        category = str(tx["category"] or "").strip().lower()
        if tx["transaction_type"] in {"Income", "Receipt"}:
            counterpart = accounts["Sales Revenue"]
            lines = [{"account_id": cash_id, "debit": float(tx["amount"])}, {"account_id": counterpart, "credit": float(tx["amount"])}]
        else:
            mapping = {"payroll": "Payroll", "rent": "Rent", "utilities": "Utilities", "transport": "Transport", "bank charges": "Bank Charges", "tax": "Tax Expense", "cogs": "Cost of Goods Sold"}
            counterpart = accounts.get(next((v for k, v in mapping.items() if k in category), "Operating Expenses"), accounts["Operating Expenses"])
            lines = [{"account_id": counterpart, "debit": float(tx["amount"])}, {"account_id": cash_id, "credit": float(tx["amount"])}]
    return post_journal_entry(business_id, tx["transaction_date"], tx["description"], lines, reference=tx["reference"] or "", source="Transaction sync", source_transaction_id=transaction_id)


def sync_eligible_transactions(business_id: int) -> tuple[int, int]:
    """Sync eligible non-transfer transactions; return (posted, skipped_transfers)."""
    from services.sme_store import transactions_df
    tx = transactions_df(business_id)
    posted = skipped = 0
    for _, row in tx.iterrows():
        if str(row["transaction_type"]) == "Transfer":
            skipped += 1
            continue
        before = journal_entries_df(business_id)
        sync_transaction(business_id, int(row["id"]))
        after = journal_entries_df(business_id)
        if len(after) > len(before):
            posted += 1
    return posted, skipped
