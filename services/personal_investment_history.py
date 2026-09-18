"""Historical investment valuation and performance analytics."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


def ensure_schema() -> None:
    wealth.ensure_schema()
    with pf.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_investment_valuations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investment_id INTEGER NOT NULL,
                valuation_date TEXT NOT NULL,
                current_value REAL NOT NULL CHECK(current_value >= 0),
                units REAL,
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(investment_id, valuation_date),
                FOREIGN KEY(investment_id) REFERENCES personal_investments(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_investment_valuation_date "
            "ON personal_investment_valuations(valuation_date)"
        )


def record_valuation(
    investment_id: int,
    valuation_date: str,
    current_value: float,
    units: float | None = None,
    note: str = "",
) -> None:
    ensure_schema()
    try:
        d = date.fromisoformat(valuation_date).isoformat()
    except ValueError as exc:
        raise ValueError("Valuation date must be YYYY-MM-DD") from exc
    value = float(current_value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Current value must be a finite non-negative number")
    if units is not None:
        units = float(units)
        if not math.isfinite(units) or units < 0:
            raise ValueError("Units must be finite and non-negative")
    with pf.connect() as conn:
        inv = conn.execute(
            "SELECT id FROM personal_investments WHERE id=?",
            (int(investment_id),),
        ).fetchone()
        if inv is None:
            raise ValueError("Investment does not exist")
        conn.execute(
            """
            INSERT INTO personal_investment_valuations(
                investment_id,valuation_date,current_value,units,note
            ) VALUES (?,?,?,?,?)
            ON CONFLICT(investment_id,valuation_date) DO UPDATE SET
                current_value=excluded.current_value,
                units=excluded.units,
                note=excluded.note
            """,
            (int(investment_id), d, value, units, note.strip()),
        )
        conn.execute(
            """
            UPDATE personal_investments
            SET current_value=?, units=?, as_of_date=?, notes=?
            WHERE id=?
            """,
            (value, units, d, note.strip(), int(investment_id)),
        )


def valuation_history(
    investment_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    ensure_schema()
    sql = """
        SELECT v.id, v.investment_id, i.name, i.asset_class, i.cost_basis,
               v.valuation_date, v.current_value, v.units, v.note
        FROM personal_investment_valuations v
        JOIN personal_investments i ON i.id=v.investment_id
        WHERE 1=1
    """
    params: list[object] = []
    if investment_id is not None:
        sql += " AND v.investment_id=?"
        params.append(int(investment_id))
    if start:
        sql += " AND v.valuation_date>=?"
        params.append(start)
    if end:
        sql += " AND v.valuation_date<=?"
        params.append(end)
    sql += " ORDER BY v.valuation_date, v.investment_id, v.id"
    with pf.connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def performance_summary(as_of: str | None = None) -> pd.DataFrame:
    history = valuation_history(end=as_of)
    if history.empty:
        return history.assign(
            gain_loss=pd.Series(dtype=float),
            return_pct=pd.Series(dtype=float),
        )
    rows = []
    for investment_id, group in history.groupby("investment_id"):
        group = group.sort_values("valuation_date")
        latest = group.iloc[-1]
        cost = float(latest["cost_basis"])
        value = float(latest["current_value"])
        gain = value - cost
        rows.append(
            {
                "investment_id": int(investment_id),
                "name": latest["name"],
                "asset_class": latest["asset_class"],
                "cost_basis": cost,
                "current_value": value,
                "gain_loss": gain,
                "return_pct": gain / cost * 100 if cost else None,
                "first_valuation": group.iloc[0]["valuation_date"],
                "latest_valuation": latest["valuation_date"],
                "observations": len(group),
            }
        )
    return pd.DataFrame(rows).sort_values("current_value", ascending=False)


def portfolio_history(as_of: str | None = None) -> pd.DataFrame:
    history = valuation_history(end=as_of)
    if history.empty:
        return pd.DataFrame(columns=["valuation_date", "portfolio_value"])
    return (
        history.groupby("valuation_date", as_index=False)["current_value"]
        .sum()
        .rename(columns={"current_value": "portfolio_value"})
        .sort_values("valuation_date")
    )
