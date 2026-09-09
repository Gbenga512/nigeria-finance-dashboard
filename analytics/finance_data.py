"""Core finance data ingestion, classification, and validation utilities."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import BinaryIO

import pandas as pd


CANONICAL_COLUMNS = [
    "date",
    "account",
    "description",
    "debit",
    "credit",
    "amount",
    "currency",
    "category",
    "reference",
    "entity",
]

COLUMN_ALIASES = {
    "date": {"date", "transaction date", "posting date", "value date", "period", "month"},
    "account": {"account", "account name", "gl account", "ledger account", "account code", "gl code"},
    "description": {"description", "details", "narration", "memo", "particulars", "transaction details"},
    "debit": {"debit", "debits", "withdrawal", "withdrawals", "dr"},
    "credit": {"credit", "credits", "deposit", "deposits", "cr"},
    "amount": {"amount", "transaction amount", "value", "balance movement", "net amount", "actual", "budget amount"},
    "currency": {"currency", "ccy"},
    "category": {"category", "type", "classification", "cost centre", "cost center", "department"},
    "reference": {"reference", "ref", "transaction reference", "transaction id", "id"},
    "entity": {"entity", "business unit", "company", "subsidiary", "branch"},
}

DATASET_TYPES = {
    "bank_statement": "Bank Statement",
    "general_ledger": "General Ledger",
    "budget": "Budget",
    "transactions": "Transaction Export",
    "financial_statement": "Financial Statement",
    "unknown": "Unknown / Review",
}

ROUTE_BY_DATASET = {
    "bank_statement": "Bank Reconciliation + Treasury",
    "general_ledger": "Financial Statement Analyzer + Management Reports",
    "budget": "Budget Analysis + Variance Intelligence",
    "transactions": "Financial Health + Intelligence Centre",
    "financial_statement": "Financial Statement Analyzer + Ratios",
    "unknown": "Finance Data Workspace",
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    rows: int
    columns: int
    duplicate_rows: int
    missing_dates: int
    numeric_issues: int


@dataclass
class DatasetProfile:
    dataset_type: str
    label: str
    confidence: int
    route: str
    reasons: list[str]
    required_fields: list[str]
    missing_required_fields: list[str]


def _normalise_name(value: object) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def suggest_column_mapping(columns: list[str]) -> dict[str, str]:
    """Suggest canonical mappings without modifying the source dataframe."""
    normalised = {_normalise_name(column): column for column in columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                mapping[canonical] = normalised[alias]
                break
    return mapping


def _has_any(mapping: dict[str, str], *fields: str) -> bool:
    return any(field in mapping for field in fields)


def classify_dataset(columns: list[str]) -> DatasetProfile:
    """Classify a source dataset using explainable header signals."""
    mapping = suggest_column_mapping(columns)
    names = {_normalise_name(column) for column in columns}
    scores = {key: 0 for key in DATASET_TYPES if key != "unknown"}
    reasons: dict[str, list[str]] = {key: [] for key in scores}

    if _has_any(mapping, "debit", "credit") and "balance" in names:
        scores["bank_statement"] += 5
        reasons["bank_statement"].append("Debit/credit and balance-style fields detected")
    elif _has_any(mapping, "debit", "credit"):
        scores["bank_statement"] += 2
        reasons["bank_statement"].append("Debit/credit transaction fields detected")

    if "account" in mapping:
        scores["general_ledger"] += 4
        reasons["general_ledger"].append("Ledger/account field detected")
    if "gl account" in names or "ledger account" in names or "gl code" in names:
        scores["general_ledger"] += 3
        reasons["general_ledger"].append("GL-specific header detected")

    if "budget" in names or "budget amount" in names or "budgeted" in names:
        scores["budget"] += 6
        reasons["budget"].append("Budget-specific header detected")
    if "actual" in names or "variance" in names:
        scores["budget"] += 2
        reasons["budget"].append("Actual/variance field detected")

    if "description" in mapping and "amount" in mapping:
        scores["transactions"] += 3
        reasons["transactions"].append("Transaction description and amount detected")
    if "reference" in mapping:
        scores["transactions"] += 1
        reasons["transactions"].append("Transaction reference detected")

    statement_terms = {"revenue", "sales", "expenses", "assets", "liabilities", "equity", "profit", "loss", "income statement", "balance sheet"}
    if names & statement_terms:
        scores["financial_statement"] += 5
        reasons["financial_statement"].append("Financial-statement terminology detected")
    if "account" in mapping and "amount" in mapping and "date" not in mapping:
        scores["financial_statement"] += 1

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_type, best_score = ranked[0]
    second_score = ranked[1][1]
    if best_score < 3 or best_score == second_score:
        best_type = "unknown"
        confidence = 0
    else:
        confidence = min(98, 50 + best_score * 7 + min(10, max(0, best_score - second_score) * 4))

    required_by_type = {
        "bank_statement": ["date", "description"],
        "general_ledger": ["date", "account"],
        "budget": ["account", "category", "amount"],
        "transactions": ["date", "description", "amount"],
        "financial_statement": ["account", "amount"],
        "unknown": [],
    }
    required = required_by_type[best_type]
    missing = [field for field in required if field not in mapping]
    if best_type != "unknown" and missing:
        confidence = max(0, confidence - len(missing) * 12)
        reasons[best_type].append("Missing expected field(s): " + ", ".join(missing))

    return DatasetProfile(
        dataset_type=best_type,
        label=DATASET_TYPES[best_type],
        confidence=confidence,
        route=ROUTE_BY_DATASET[best_type],
        reasons=reasons.get(best_type, ["No sufficiently strong dataset signature detected"]),
        required_fields=required,
        missing_required_fields=missing,
    )


def normalize_finance_data(frame: pd.DataFrame, mapping: dict[str, str] | None = None) -> pd.DataFrame:
    """Convert an uploaded financial dataframe to the NG Finance canonical schema."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    source = frame.copy()
    mapping = mapping or suggest_column_mapping(source.columns.tolist())
    rename = {source_column: canonical for canonical, source_column in mapping.items() if source_column in source.columns}
    source = source.rename(columns=rename)

    for column in CANONICAL_COLUMNS:
        if column not in source.columns:
            source[column] = pd.NA

    source = source[CANONICAL_COLUMNS].copy()
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    for column in ["debit", "credit", "amount"]:
        source[column] = pd.to_numeric(
            source[column].astype(str).str.replace(",", "", regex=False).str.replace("₦", "", regex=False).str.strip(),
            errors="coerce",
        )
    for column in ["account", "description", "currency", "category", "reference", "entity"]:
        source[column] = source[column].astype("string").str.strip()

    source["amount"] = source["amount"].fillna(source["credit"].fillna(0) - source["debit"].fillna(0))
    return source


def validate_finance_data(frame: pd.DataFrame, dataset_type: str = "unknown") -> ValidationResult:
    """Validate a canonical finance dataframe, with optional dataset-specific rules."""
    errors: list[str] = []
    warnings: list[str] = []
    if frame is None:
        return ValidationResult(False, ["No dataset was supplied."], [], 0, 0, 0, 0, 0)

    rows, columns = frame.shape
    missing_columns = [column for column in CANONICAL_COLUMNS if column not in frame.columns]
    if missing_columns:
        errors.append("Missing canonical columns: " + ", ".join(missing_columns))
        return ValidationResult(False, errors, warnings, rows, columns, 0, 0, 0)

    duplicate_rows = int(frame.duplicated().sum())
    missing_dates = int(frame["date"].isna().sum())
    numeric_issues = int(frame[["debit", "credit", "amount"]].apply(pd.to_numeric, errors="coerce").isna().sum().sum())

    if rows == 0:
        errors.append("The dataset contains no rows.")
    if missing_dates and dataset_type in {"bank_statement", "general_ledger", "transactions"}:
        errors.append(f"{missing_dates} row(s) have an invalid or missing date.")
    elif missing_dates:
        warnings.append(f"{missing_dates} row(s) have an invalid or missing date.")
    if numeric_issues:
        warnings.append(f"{numeric_issues} numeric field(s) are missing or non-numeric.")
    if duplicate_rows:
        warnings.append(f"{duplicate_rows} duplicate row(s) detected.")
    if dataset_type == "bank_statement" and frame["amount"].notna().sum() == 0:
        errors.append("Bank statements require an amount movement or debit/credit values.")
    if dataset_type == "general_ledger" and frame["account"].isna().all():
        errors.append("General ledgers require an account field.")
    if frame["amount"].notna().any() and (frame["amount"].abs() > 1e15).any():
        warnings.append("One or more amounts exceed ₦1 quadrillion equivalent; review source data.")

    valid = not errors
    return ValidationResult(valid, errors, warnings, rows, columns, duplicate_rows, missing_dates, numeric_issues)


def read_uploaded_file(file: BinaryIO, filename: str) -> pd.DataFrame:
    """Read CSV/XLSX uploads using the file extension."""
    data = file.read()
    lower = filename.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if lower.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(data))
    raise ValueError("Unsupported file type. Upload a CSV or XLSX file.")
