"""Debt-payment linkage for the Personal Finance debt subledger."""
from __future__ import annotations

import math

import pandas as pd

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


def ensure_schema() -> None:
    wealth.ensure_schema()
    with pf.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_debt_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debt_id INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL UNIQUE,
                principal_amount REAL NOT NULL CHECK(principal_amount >= 0),
                interest_amount REAL NOT NULL CHECK(interest_amount >= 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(debt_id) REFERENCES personal_debts(id),
                FOREIGN KEY(transaction_id) REFERENCES personal_transactions(id),
                CHECK(principal_amount + interest_amount > 0)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_debt_payment_debt "
            "ON personal_debt_payments(debt_id)"
        )


def link_payment(
    transaction_id: int,
    debt_id: int,
    principal_amount: float,
    interest_amount: float = 0.0,
) -> None:
    ensure_schema()
    principal = float(principal_amount)
    interest = float(interest_amount)
    if not all(math.isfinite(x) and x >= 0 for x in (principal, interest)):
        raise ValueError("Principal and interest allocations must be finite and non-negative")
    with pf.connect() as conn:
        tx = conn.execute(
            """
            SELECT id, transaction_date, amount, transaction_type
            FROM personal_transactions
            WHERE id=?
            """,
            (int(transaction_id),),
        ).fetchone()
        if tx is None:
            raise ValueError("Payment transaction does not exist")
        if tx["transaction_type"] != "Debt Payment":
            raise ValueError("Only Debt Payment transactions can be linked")
        if abs((principal + interest) - float(tx["amount"])) > 0.01:
            raise ValueError("Principal plus interest must equal the transaction amount")
        if conn.execute(
            "SELECT 1 FROM personal_debt_payments WHERE transaction_id=?",
            (int(transaction_id),),
        ).fetchone():
            raise ValueError("This payment transaction is already linked to a debt")
        debt = conn.execute(
            """
            SELECT id, current_balance, as_of_date
            FROM personal_debts
            WHERE id=? AND status='Active'
            """,
            (int(debt_id),),
        ).fetchone()
        if debt is None:
            raise ValueError("Active debt does not exist")
        if tx["transaction_date"] <= debt["as_of_date"]:
            raise ValueError("Payment date must be after the debt balance as-of date")
        linked_principal = float(
            conn.execute(
                """
                SELECT COALESCE(SUM(principal_amount),0)
                FROM personal_debt_payments
                WHERE debt_id=? AND transaction_id IN (
                    SELECT id FROM personal_transactions WHERE transaction_date>?
                )
                """,
                (int(debt_id), debt["as_of_date"]),
            ).fetchone()[0]
        )
        remaining = max(0.0, float(debt["current_balance"]) - linked_principal)
        if principal > remaining + 0.01:
            raise ValueError(
                f"Principal allocation exceeds the linked debt balance "
                f"({remaining:,.2f} remaining before this payment)"
            )
        conn.execute(
            """
            INSERT INTO personal_debt_payments(
                debt_id,transaction_id,principal_amount,interest_amount
            ) VALUES (?,?,?,?)
            """,
            (int(debt_id), int(transaction_id), principal, interest),
        )


def payment_register(debt_id: int | None = None) -> pd.DataFrame:
    ensure_schema()
    sql = """
        SELECT p.id, p.debt_id, d.name AS debt_name,
               p.transaction_id, t.transaction_date, t.description,
               t.amount AS payment_amount, p.principal_amount,
               p.interest_amount
        FROM personal_debt_payments p
        JOIN personal_debts d ON d.id=p.debt_id
        JOIN personal_transactions t ON t.id=p.transaction_id
    """
    params: list[int] = []
    if debt_id is not None:
        sql += " WHERE p.debt_id=?"
        params.append(int(debt_id))
    sql += " ORDER BY t.transaction_date DESC, p.id DESC"
    with pf.connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def debt_summary(as_of: str | None = None) -> pd.DataFrame:
    ensure_schema()
    as_of = as_of or pd.Timestamp.today().strftime("%Y-%m-%d")
    debts = wealth.debts(as_of).copy()
    if debts.empty:
        return debts.assign(
            linked_principal=pd.Series(dtype=float),
            linked_interest=pd.Series(dtype=float),
            calculated_balance=pd.Series(dtype=float),
        )
    payments = payment_register()
    if payments.empty:
        debts["linked_principal"] = 0.0
        debts["linked_interest"] = 0.0
    else:
        payments = payments[
            payments["transaction_date"] <= as_of
        ]
        agg = payments.groupby("debt_id").agg(
            linked_principal=("principal_amount", "sum"),
            linked_interest=("interest_amount", "sum"),
        )
        debts = debts.merge(agg, left_on="id", right_index=True, how="left")
        debts[["linked_principal", "linked_interest"]] = debts[
            ["linked_principal", "linked_interest"]
        ].fillna(0.0)
    debts["calculated_balance"] = (
        debts["current_balance"] - debts["linked_principal"]
    ).clip(lower=0.0)
    return debts
