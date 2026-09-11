"""Bank-to-cashbook reconciliation with direction-aware matching."""
from __future__ import annotations

import pandas as pd

DATE_ALIASES = ["date", "transaction date", "value date", "posting date"]
AMOUNT_ALIASES = ["amount", "transaction amount", "value"]
DEBIT_ALIASES = ["debit", "withdrawal", "debits"]
CREDIT_ALIASES = ["credit", "deposit", "credits"]
DESCRIPTION_ALIASES = ["description", "narration", "details", "memo", "reference"]


def _find_column(df: pd.DataFrame, aliases: list[str]):
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for key, original in normalized.items():
        if any(alias in key for alias in aliases):
            return original
    return None


def _amount_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.replace("₦", "", regex=False).str.replace("NGN", "", regex=False).str.strip(), errors="coerce")


def normalize_transactions(df: pd.DataFrame, source: str) -> pd.DataFrame:
    date_col = _find_column(df, DATE_ALIASES)
    amount_col = _find_column(df, AMOUNT_ALIASES)
    debit_col = _find_column(df, DEBIT_ALIASES)
    credit_col = _find_column(df, CREDIT_ALIASES)
    desc_col = _find_column(df, DESCRIPTION_ALIASES)
    if not date_col or not (amount_col or debit_col or credit_col):
        raise ValueError(f"{source} needs identifiable Date and Amount/Debit/Credit columns.")

    if debit_col or credit_col:
        debit = _amount_series(df[debit_col]).fillna(0).abs() if debit_col else pd.Series(0.0, index=df.index)
        credit = _amount_series(df[credit_col]).fillna(0).abs() if credit_col else pd.Series(0.0, index=df.index)
        signed_amount = credit - debit
        conflict = (debit > 0) & (credit > 0)
    else:
        signed_amount = _amount_series(df[amount_col])
        conflict = pd.Series(False, index=df.index)

    out = pd.DataFrame({
        "Date": pd.to_datetime(df[date_col], errors="coerce"),
        "Amount": signed_amount,
        "Description": df[desc_col].astype(str) if desc_col else "",
        "Source": source,
    })
    out["Direction"] = out["Amount"].map(lambda x: "Inflow" if x > 0 else "Outflow" if x < 0 else "Unknown")
    out.loc[conflict, "Amount"] = pd.NA
    out.loc[conflict, "Direction"] = "Unknown"
    out = out.dropna(subset=["Date", "Amount"]).reset_index(drop=True)
    out["Amount"] = out["Amount"].round(2)
    return out


def reconcile(bank: pd.DataFrame, cashbook: pd.DataFrame, date_tolerance_days: int = 3):
    bank = bank.copy()
    cashbook = cashbook.copy()
    bank["Matched"] = False
    cashbook["Matched"] = False
    matches = []

    for b_idx, b in bank.iterrows():
        candidates = cashbook.loc[~cashbook["Matched"]].copy()
        candidates["DateDiff"] = (candidates["Date"] - b["Date"]).abs().dt.days
        candidates = candidates[(candidates["Amount"] - b["Amount"]).abs() <= 0.01]
        candidates = candidates[candidates["DateDiff"] <= date_tolerance_days]
        if b.get("Direction", "Unknown") != "Unknown":
            candidates = candidates[(candidates["Direction"] == b["Direction"]) | (candidates["Direction"] == "Unknown")]
        if candidates.empty:
            continue
        c_idx = candidates.sort_values(["DateDiff"]).index[0]
        bank.loc[b_idx, "Matched"] = True
        cashbook.loc[c_idx, "Matched"] = True
        matches.append({
            "Bank Index": b_idx,
            "Cashbook Index": c_idx,
            "Amount": b["Amount"],
            "Direction": b.get("Direction", "Unknown"),
            "Date Difference (days)": int(candidates.loc[c_idx, "DateDiff"]),
        })

    return bank, cashbook, pd.DataFrame(matches)
