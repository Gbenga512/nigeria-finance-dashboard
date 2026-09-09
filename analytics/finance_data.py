"""Core finance data ingestion and validation utilities for NG Finance Pro."""

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
    "date": {"date", "transaction date", "posting date", "value date"},
    "account": {"account", "account name", "gl account", "ledger account"},
    "description": {"description", "details", "narration", "memo"},
    "debit": {"debit", "debits", "withdrawal", "withdrawals"},
    "credit": {"credit", "credits", "deposit", "deposits"},
    "amount": {"amount", "transaction amount", "value", "balance movement"},
    "currency": {"currency", "ccy"},
    "category": {"category", "type", "classification"},
    "reference": {"reference", "ref", "transaction reference", "transaction id"},
    "entity": {"entity", "business unit", "company", "subsidiary"},
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

    # If amount is absent but debit/credit are available, derive signed amount.
    source["amount"] = source["amount"].fillna(source["credit"].fillna(0) - source["debit"].fillna(0))
    return source


def validate_finance_data(frame: pd.DataFrame) -> ValidationResult:
    """Validate a canonical finance dataframe for common ingestion problems."""
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
    if missing_dates:
        errors.append(f"{missing_dates} row(s) have an invalid or missing date.")
    if numeric_issues:
        warnings.append(f"{numeric_issues} numeric field(s) are missing or non-numeric.")
    if duplicate_rows:
        warnings.append(f"{duplicate_rows} duplicate row(s) detected.")
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
