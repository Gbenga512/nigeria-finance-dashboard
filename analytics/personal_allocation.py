"""Personal 50/30/20 allocation analytics.

Commercial presentation uses exactly three buckets:
Needs, Wants, and Savings/Investment.
"""
from __future__ import annotations

import pandas as pd

from services import personal_finance as pf


BUCKETS = ("Needs", "Wants", "Savings/Investment")


def allocation_report(start: str, end: str) -> pd.DataFrame:
    tx = pf.transactions(start, end)
    settings = pf.settings()
    income = float(tx.loc[tx["transaction_type"] == "Income", "amount"].sum()) if not tx.empty else 0.0

    actual = {bucket: 0.0 for bucket in BUCKETS}
    if not tx.empty:
        expense = tx[tx["transaction_type"].isin(["Expense", "Debt Payment"])].copy()
        if not expense.empty:
            actual["Needs"] = float(
                expense.loc[expense["classification"] == "Need", "amount"].sum()
            )
            actual["Wants"] = float(
                expense.loc[expense["classification"] == "Want", "amount"].sum()
            )
        actual["Savings/Investment"] = float(
            tx.loc[tx["transaction_type"].isin(["Savings", "Investment"]), "amount"].sum()
        )

    month_start = pd.Timestamp(start).strftime("%Y-%m")
    month_end = pd.Timestamp(end).strftime("%Y-%m")
    with pf.connect() as conn:
        budgets = pd.read_sql_query(
            """
            SELECT b.category, b.amount, c.classification
            FROM personal_budgets b
            LEFT JOIN personal_categories c ON c.name=b.category
            WHERE b.month BETWEEN ? AND ?
            """,
            conn,
            params=[month_start, month_end],
        )

    planned = {bucket: 0.0 for bucket in BUCKETS}
    if not budgets.empty:
        for _, row in budgets.iterrows():
            cls = str(row["classification"] or "")
            bucket = (
                "Needs" if cls == "Need"
                else "Wants" if cls == "Want"
                else "Savings/Investment" if cls == "Savings"
                else None
            )
            if bucket:
                planned[bucket] += float(row["amount"])

    targets = {
        "Needs": float(settings["needs_target"]),
        "Wants": float(settings["wants_target"]),
        "Savings/Investment": float(settings["savings_target"]),
    }

    rows = []
    for bucket in BUCKETS:
        actual_amount = actual[bucket]
        planned_amount = planned[bucket]
        target_amount = income * targets[bucket]
        rows.append(
            {
                "Bucket": bucket,
                "Actual": actual_amount,
                "Actual % of Income": actual_amount / income * 100 if income else None,
                "Target %": targets[bucket] * 100,
                "Target Amount": target_amount,
                "Budgeted": planned_amount,
                "Budget Variance": actual_amount - planned_amount if planned_amount else None,
                "Target Variance": actual_amount - target_amount if income else None,
            }
        )
    return pd.DataFrame(rows)


def allocation_summary(start: str, end: str) -> dict:
    report = allocation_report(start, end)
    income = float(pf.transactions(start, end).loc[
        lambda d: d["transaction_type"] == "Income", "amount"
    ].sum())
    return {
        "income": income,
        "report": report,
        "data_quality": (
            "FACT/CALCULATION: actual allocations are derived from recorded transactions; "
            "targets are configurable planning assumptions."
        ),
    }
