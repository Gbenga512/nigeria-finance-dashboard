"""Pure analytics for the SME finance operating layer."""
from __future__ import annotations

import pandas as pd


def _sum(df: pd.DataFrame, types: set[str]) -> float:
    if df.empty:
        return 0.0
    return float(df.loc[df["transaction_type"].isin(types), "amount"].sum())


def period_metrics(transactions: pd.DataFrame, start, end) -> dict:
    if transactions is None or transactions.empty:
        return {"revenue":0.0,"expenses":0.0,"gross_profit":None,"net_profit":None,"cash_flow":0.0,"receivables":0.0,"payables":0.0,"cash_balance":0.0,"count":0}
    df = transactions.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df[(df["transaction_date"] >= pd.Timestamp(start)) & (df["transaction_date"] <= pd.Timestamp(end))]
    revenue = _sum(df, {"Income","Receipt"})
    expenses = _sum(df, {"Expense","Supplier Payment"})
    cash_flow = revenue - expenses
    # These are transaction-derived management indicators. Receivable/payable balances
    # remain unavailable until invoice/open-item subledgers are introduced in Phase 2+.
    return {"revenue":revenue,"expenses":expenses,"gross_profit":None,"net_profit":cash_flow,"cash_flow":cash_flow,"receivables":None,"payables":None,"cash_balance":cash_flow,"count":len(df)}


def monthly_trend(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=["Month","Revenue","Expenses","Net Cash Flow"])
    df = transactions.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["transaction_date"])
    df["Month"] = df["transaction_date"].dt.to_period("M").astype(str)
    revenue = df[df["transaction_type"].isin(["Income","Receipt"])].groupby("Month")["amount"].sum()
    expenses = df[df["transaction_type"].isin(["Expense","Supplier Payment"])].groupby("Month")["amount"].sum()
    out = pd.DataFrame({"Revenue":revenue,"Expenses":expenses}).fillna(0)
    out["Net Cash Flow"] = out["Revenue"] - out["Expenses"]
    return out.reset_index()


def transaction_health(transactions: pd.DataFrame) -> dict:
    if transactions is None or transactions.empty:
        return {"score": None, "factors": []}
    total = len(transactions)
    uncategorized = int(transactions["category"].isna().sum() + (transactions["category"].astype(str).str.strip() == "").sum())
    duplicates = int(transactions.duplicated(subset=["transaction_date","description","amount","transaction_type","reference"], keep=False).sum())
    categorized_score = max(0, 100 - (uncategorized / total) * 40)
    duplicate_score = max(0, 100 - (duplicates / total) * 60)
    score = round((categorized_score + duplicate_score) / 2, 1)
    return {"score": score, "factors": [{"Factor":"Categorization completeness","Score":round(categorized_score,1),"Explanation":f"{uncategorized} of {total} transaction rows lack a category."},{"Factor":"Duplicate control","Score":round(duplicate_score,1),"Explanation":f"{duplicates} rows participate in duplicate transaction keys."}]}
