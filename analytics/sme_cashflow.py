"""Deterministic 13-week SME cash-flow forecasting."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd


def forecast_13_weeks(transactions: pd.DataFrame, as_of=None, history_weeks: int = 13) -> dict:
    """Forecast weekly cash movements from observed history only.

    The baseline uses the median weekly inflow/outflow, reducing sensitivity to one-off
    transactions. It is an estimate and does not invent invoices, commitments or financing.
    """
    as_of = pd.Timestamp(as_of or date.today()).normalize()
    if transactions is None or transactions.empty:
        return {"forecast": pd.DataFrame(columns=["Week","Opening Cash","Expected Inflow","Expected Outflow","Net Cash Flow","Closing Cash"]), "status": "INSUFFICIENT DATA", "assumption": "No transaction history available."}
    df = transactions.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["transaction_date"])
    historical = df[df["transaction_date"] <= as_of].copy()
    if historical.empty:
        return {"forecast": pd.DataFrame(), "status": "INSUFFICIENT DATA", "assumption": "No dated transactions exist on or before the forecast date."}
    cutoff = as_of - pd.Timedelta(weeks=history_weeks)
    historical = historical[historical["transaction_date"] > cutoff]
    historical["week"] = historical["transaction_date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    inflow_types = {"Income", "Receipt"}
    outflow_types = {"Expense", "Supplier Payment"}
    weekly_in = historical.loc[historical["transaction_type"].isin(inflow_types)].groupby("week")["amount"].sum()
    weekly_out = historical.loc[historical["transaction_type"].isin(outflow_types)].groupby("week")["amount"].sum()
    if len(historical) < 4:
        status = "LOW DATA"
    else:
        status = "BASELINE"
    expected_in = float(weekly_in.median()) if not weekly_in.empty else 0.0
    expected_out = float(weekly_out.median()) if not weekly_out.empty else 0.0
    # Current cash is derived from net historical cash movement in the available transaction layer.
    cash = float(weekly_in.sum() - weekly_out.sum())
    rows = []
    for i in range(13):
        week_start = (as_of + timedelta(days=1) + timedelta(weeks=i)).normalize()
        net = expected_in - expected_out
        rows.append({"Week": week_start.date().isoformat(), "Opening Cash": cash, "Expected Inflow": expected_in, "Expected Outflow": expected_out, "Net Cash Flow": net, "Closing Cash": cash + net})
        cash += net
    return {"forecast": pd.DataFrame(rows), "status": status, "assumption": "Expected weekly inflow/outflow = median observed weekly values over the trailing history window. No future commitments are assumed."}
