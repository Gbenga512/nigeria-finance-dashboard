"""Bank-statement import and review helpers for NG Finance Pro SME Finance."""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

import pandas as pd

DATE_ALIASES = ("date", "transaction date", "trans date", "value date", "posting date")
DESC_ALIASES = ("description", "narration", "details", "transaction details", "remarks", "memo")
AMOUNT_ALIASES = ("amount", "transaction amount", "value")
DEBIT_ALIASES = ("debit", "withdrawal", "debit amount")
CREDIT_ALIASES = ("credit", "deposit", "credit amount")
REF_ALIASES = ("reference", "ref", "transaction id", "reference number")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def _find_column(columns: Iterable[object], aliases: tuple[str, ...]) -> str | None:
    normalized = {_norm(c): str(c) for c in columns}
    for alias in aliases:
        if _norm(alias) in normalized:
            return normalized[_norm(alias)]
    for col in normalized:
        if any(_norm(alias) in col for alias in aliases):
            return normalized[col]
    return None


def parse_amount(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "").replace("₦", "").replace("NGN", "")
    if not text:
        return None
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    text = text.strip("() ")
    try:
        number = abs(float(text))
    except ValueError:
        return None
    return -number if negative else number


def import_key(date: object, description: object, amount: float, reference: object = "") -> str:
    raw = f"{pd.to_datetime(date, errors='coerce')}|{str(description).strip().lower()}|{amount:.2f}|{str(reference).strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_statement(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Normalize common Nigerian bank CSV/Excel layouts without inventing data."""
    if df is None or df.empty:
        return pd.DataFrame(), ["The uploaded statement is empty."]
    date_col = _find_column(df.columns, DATE_ALIASES)
    desc_col = _find_column(df.columns, DESC_ALIASES)
    amount_col = _find_column(df.columns, AMOUNT_ALIASES)
    debit_col = _find_column(df.columns, DEBIT_ALIASES)
    credit_col = _find_column(df.columns, CREDIT_ALIASES)
    ref_col = _find_column(df.columns, REF_ALIASES)
    errors: list[str] = []
    if not date_col: errors.append("A transaction date column could not be identified.")
    if not desc_col: errors.append("A transaction description/narration column could not be identified.")
    if not amount_col and not (debit_col or credit_col): errors.append("An amount column or debit/credit columns could not be identified.")
    if errors:
        return pd.DataFrame(), errors

    out = pd.DataFrame()
    out["transaction_date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    out["description"] = df[desc_col].astype(str).str.strip()
    if amount_col:
        out["amount"] = df[amount_col].map(parse_amount)
        out["direction"] = out["amount"].map(lambda x: "Credit" if x is not None and x >= 0 else "Debit")
        out["amount"] = out["amount"].abs()
    else:
        debit = df[debit_col].map(parse_amount) if debit_col else pd.Series(0.0, index=df.index)
        credit = df[credit_col].map(parse_amount) if credit_col else pd.Series(0.0, index=df.index)
        debit = debit.abs().fillna(0)
        credit = credit.abs().fillna(0)
        out["amount"] = debit + credit
        out["direction"] = ["Debit" if d > 0 and c == 0 else "Credit" if c > 0 and d == 0 else "Unknown" for d, c in zip(debit, credit)]
    out["reference"] = df[ref_col].astype(str).str.strip() if ref_col else ""
    out["transaction_type"] = out["direction"].map({"Credit": "Receipt", "Debit": "Expense", "Unknown": "Expense"})
    out["category"] = "Uncategorized"
    out["import_key"] = [import_key(d, desc, amt, ref) for d, desc, amt, ref in zip(out["transaction_date"], out["description"], out["amount"], out["reference"])]
    out["valid"] = out["transaction_date"].notna() & out["description"].ne("") & pd.to_numeric(out["amount"], errors="coerce").gt(0)
    out["duplicate_in_file"] = out["import_key"].duplicated(keep=False)
    return out.reset_index(drop=True), errors


def categorize_description(description: str, direction: str = "") -> str:
    """Transparent starter categorizer; future user-specific rules can override it."""
    text = str(description).lower()
    rules = {
        "Payroll": ("salary", "payroll", "wages", "staff"),
        "Rent": ("rent", "lease"),
        "Utilities": ("electric", "phcn", "power", "water", "internet", "data"),
        "Bank Charges": ("bank charge", "commission", "stamp duty", "pos charge"),
        "Tax": ("tax", "vat", "paye", "withholding", "wht"),
        "Fuel & Transport": ("fuel", "diesel", "petrol", "transport"),
        "Sales / Customer Receipt": ("payment from", "customer", "sales", "invoice"),
    }
    for category, keywords in rules.items():
        if any(k in text for k in keywords):
            return category
    return "Uncategorized"


def apply_categorization(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if not result.empty:
        result["category"] = [categorize_description(d, direction) for d, direction in zip(result["description"], result["direction"])]
    return result
