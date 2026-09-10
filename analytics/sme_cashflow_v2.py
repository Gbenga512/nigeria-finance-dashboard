"""Deterministic 13-week SME cash-flow forecasting using ledger opening cash."""
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd

def forecast_13_weeks(transactions: pd.DataFrame, as_of=None, history_weeks: int = 13, opening_cash: float = 0.0) -> dict:
    as_of = pd.Timestamp(as_of or date.today()).normalize()
    empty = pd.DataFrame(columns=["Week","Opening Cash","Expected Inflow","Expected Outflow","Net Cash Flow","Closing Cash"])
    if transactions is None or transactions.empty:
        return {"forecast": empty, "status": "INSUFFICIENT DATA", "assumption": "No transaction history available."}
    df = transactions.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    historical = df.dropna(subset=["transaction_date"])
    historical = historical[historical["transaction_date"] <= as_of]
    historical = historical[historical["transaction_date"] > as_of - pd.Timedelta(weeks=history_weeks)].copy()
    if historical.empty:
        return {"forecast": empty, "status": "INSUFFICIENT DATA", "assumption": "No dated transactions exist in the trailing history window."}
    historical["week"] = historical["transaction_date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    inflow = historical.loc[historical["transaction_type"].isin({"Income", "Receipt"})].groupby("week")["amount"].sum()
    outflow = historical.loc[historical["transaction_type"].isin({"Expense", "Supplier Payment"})].groupby("week")["amount"].sum()
    expected_in = float(inflow.median()) if not inflow.empty else 0.0
    expected_out = float(outflow.median()) if not outflow.empty else 0.0
    status = "LOW DATA" if len(historical) < 4 else "BASELINE"
    cash = float(opening_cash)
    rows = []
    for i in range(13):
        week = (as_of + timedelta(days=1) + timedelta(weeks=i)).date().isoformat()
        net = expected_in - expected_out
        rows.append({"Week": week, "Opening Cash": cash, "Expected Inflow": expected_in, "Expected Outflow": expected_out, "Net Cash Flow": net, "Closing Cash": cash + net})
        cash += net
    return {"forecast": pd.DataFrame(rows), "status": status, "assumption": "Expected weekly inflow/outflow uses the median observed weekly values from the trailing history window. Future commitments are not assumed."}
