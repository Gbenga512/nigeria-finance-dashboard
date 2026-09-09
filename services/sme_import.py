"""Safe bank-statement import primitives for the SME finance module.

The importer parses CSV/XLSX into a canonical review dataframe. It deliberately
never posts rows to the ledger; the UI must explicitly confirm posting.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

import pandas as pd

DATE_ALIASES = ["date", "transaction date", "value date", "posting date"]
DESC_ALIASES = ["description", "narration", "details", "transaction details", "memo"]
AMOUNT_ALIASES = ["amount", "transaction amount", "value"]
DEBIT_ALIASES = ["debit", "withdrawal", "debits"]
CREDIT_ALIASES = ["credit", "deposit", "credits"]
REF_ALIASES = ["reference", "transaction id", "transaction reference", "ref"]


def _normalise(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _find_column(columns, aliases):
    normalised = {_normalise(c): c for c in columns}
    for alias in aliases:
        if alias in normalised:
            return normalised[alias]
    return None


def _parse_amount(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("₦", "", regex=False).str.replace("NGN", "", regex=False).str.strip(),
        errors="coerce",
    )


def parse_statement(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV/XLSX into a review dataframe without touching the ledger."""
    name = filename.lower()
    if name.endswith(".csv"):
        raw = pd.read_csv(io.BytesIO(file_bytes))
    elif name.endswith((".xlsx", ".xls")):
        raw = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError("Supported bank statement formats are CSV and Excel.")
    if raw.empty:
        return pd.DataFrame(columns=["transaction_date", "description", "amount", "reference", "import_key", "category", "transaction_type", "duplicate"])

    date_col = _find_column(raw.columns, DATE_ALIASES)
    desc_col = _find_column(raw.columns, DESC_ALIASES)
    amount_col = _find_column(raw.columns, AMOUNT_ALIASES)
    debit_col = _find_column(raw.columns, DEBIT_ALIASES)
    credit_col = _find_column(raw.columns, CREDIT_ALIASES)
    ref_col = _find_column(raw.columns, REF_ALIASES)
    if not date_col or not desc_col or not (amount_col or debit_col or credit_col):
        raise ValueError("Could not identify required date, description and amount/debit/credit columns.")

    out = pd.DataFrame()
    out["transaction_date"] = pd.to_datetime(raw[date_col], errors="coerce").dt.date.astype("string")
    out["description"] = raw[desc_col].astype(str).str.strip()
    if amount_col:
        out["amount"] = _parse_amount(raw[amount_col]).abs()
        signed = _parse_amount(raw[amount_col])
    else:
        debit = _parse_amount(raw[debit_col]).fillna(0) if debit_col else pd.Series(0, index=raw.index)
        credit = _parse_amount(raw[credit_col]).fillna(0) if credit_col else pd.Series(0, index=raw.index)
        out["amount"] = (debit.abs() + credit.abs())
        signed = credit.abs() - debit.abs()
    out["reference"] = raw[ref_col].astype(str).str.strip() if ref_col else ""
    out["transaction_type"] = signed.map(lambda x: "Income" if x > 0 else "Expense" if x < 0 else "Transfer")
    out["category"] = ""
    out["import_key"] = out.apply(lambda r: hashlib.sha256(f"{r['transaction_date']}|{r['description']}|{r['amount']:.2f}|{r['reference']}".encode()).hexdigest(), axis=1)
    out["duplicate"] = out["import_key"].duplicated(keep=False)
    out["valid"] = out["transaction_date"].notna() & (out["description"].str.len() > 0) & out["amount"].notna() & (out["amount"] > 0)
    return out.reset_index(drop=True)


def detect_existing_duplicates(review: pd.DataFrame, existing: pd.DataFrame) -> pd.DataFrame:
    """Mark rows matching the existing ledger using the same deterministic key."""
    out = review.copy()
    if existing is None or existing.empty:
        out["existing_duplicate"] = False
        return out
    keys = set()
    for _, row in existing.iterrows():
        key = hashlib.sha256(f"{pd.to_datetime(row['transaction_date']).date()}|{row['description']}|{float(row['amount']):.2f}|{row.get('reference', '')}".encode()).hexdigest()
        keys.add(key)
    out["existing_duplicate"] = out["import_key"].isin(keys)
    return out


def suggest_categories(review: pd.DataFrame, history: pd.DataFrame | None = None) -> pd.DataFrame:
    """Suggest categories from prior user classifications, then conservative keywords."""
    out = review.copy()
    learned = {}
    if history is not None and not history.empty:
        for _, row in history.dropna(subset=["category"]).iterrows():
            key = str(row.get("description", "")).strip().lower()
            if key and str(row.get("category", "")).strip():
                learned[key] = str(row["category"]).strip()
    rules = [("salary", "Payroll"), ("wage", "Payroll"), ("rent", "Rent"), ("fuel", "Transport"), ("diesel", "Utilities"), ("electric", "Utilities"), ("internet", "Utilities"), ("bank charge", "Bank Charges"), ("transfer fee", "Bank Charges"), ("tax", "Tax")]
    def suggest(desc):
        d = str(desc).lower().strip()
        if d in learned: return learned[d]
        for token, category in rules:
            if token in d: return category
        return ""
    out["suggested_category"] = out.apply(lambda r: suggest(r["description"]), axis=1)
    return out
