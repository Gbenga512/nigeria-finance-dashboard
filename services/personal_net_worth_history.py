"""Historical personal net-worth snapshots."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


def ensure_snapshot_schema() -> None:
    pf.ensure_schema()
    with pf.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_net_worth_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL UNIQUE,
                assets REAL NOT NULL,
                liabilities REAL NOT NULL,
                net_worth REAL NOT NULL,
                liquid_cash REAL NOT NULL,
                investments REAL NOT NULL,
                debt_register REAL NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_nw_snapshot_date "
            "ON personal_net_worth_snapshots(snapshot_date)"
        )


def record_snapshot(snapshot_date: str | None = None, notes: str = "") -> dict:
    ensure_snapshot_schema()
    d = snapshot_date or date.today().isoformat()
    try:
        date.fromisoformat(d)
    except ValueError as exc:
        raise ValueError("Snapshot date must be YYYY-MM-DD") from exc
    nw = wealth.integrated_net_worth(d)
    with pf.connect() as conn:
        conn.execute(
            """
            INSERT INTO personal_net_worth_snapshots(
                snapshot_date,assets,liabilities,net_worth,liquid_cash,
                investments,debt_register,notes
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                assets=excluded.assets,
                liabilities=excluded.liabilities,
                net_worth=excluded.net_worth,
                liquid_cash=excluded.liquid_cash,
                investments=excluded.investments,
                debt_register=excluded.debt_register,
                notes=excluded.notes
            """,
            (
                d,
                float(nw["assets"]),
                float(nw["liabilities"]),
                float(nw["net_worth"]),
                float(nw["liquid_cash"]),
                float(nw["investments"]),
                float(nw["debts"]),
                notes.strip(),
            ),
        )
    return nw


def snapshots(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    ensure_snapshot_schema()
    sql = "SELECT * FROM personal_net_worth_snapshots WHERE 1=1"
    params: list[str] = []
    if start:
        sql += " AND snapshot_date>=?"
        params.append(start)
    if end:
        sql += " AND snapshot_date<=?"
        params.append(end)
    sql += " ORDER BY snapshot_date"
    with pf.connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def snapshot_summary(start: str | None = None, end: str | None = None) -> dict:
    df = snapshots(start, end)
    if df.empty:
        return {
            "snapshot_count": 0,
            "latest_net_worth": None,
            "change": None,
            "status": "FACT/CALCULATION: no historical snapshots recorded",
        }
    latest = float(df.iloc[-1]["net_worth"])
    change = latest - float(df.iloc[0]["net_worth"]) if len(df) > 1 else None
    return {
        "snapshot_count": len(df),
        "latest_net_worth": latest,
        "change": change,
        "status": "FACT/CALCULATION: based on recorded net-worth snapshots",
    }
