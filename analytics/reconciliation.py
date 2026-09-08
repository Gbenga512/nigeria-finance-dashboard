import pandas as pd

DATE_ALIASES = ["date", "transaction date", "value date", "posting date"]
AMOUNT_ALIASES = ["amount", "transaction amount", "value", "debit", "credit"]
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


def normalize_transactions(df: pd.DataFrame, source: str) -> pd.DataFrame:
    date_col = _find_column(df, DATE_ALIASES)
    amount_col = _find_column(df, AMOUNT_ALIASES)
    desc_col = _find_column(df, DESCRIPTION_ALIASES)
    if not date_col or not amount_col:
        raise ValueError(f"{source} needs identifiable Date and Amount columns.")

    out = pd.DataFrame({
        "Date": pd.to_datetime(df[date_col], errors="coerce"),
        "Amount": pd.to_numeric(df[amount_col], errors="coerce"),
        "Description": df[desc_col].astype(str) if desc_col else "",
        "Source": source,
    })
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
        if candidates.empty:
            continue
        c_idx = candidates.sort_values(["DateDiff"]).index[0]
        bank.loc[b_idx, "Matched"] = True
        cashbook.loc[c_idx, "Matched"] = True
        matches.append({
            "Bank Index": b_idx,
            "Cashbook Index": c_idx,
            "Amount": b["Amount"],
            "Date Difference (days)": int(candidates.loc[c_idx, "DateDiff"]),
        })

    return bank, cashbook, pd.DataFrame(matches)
