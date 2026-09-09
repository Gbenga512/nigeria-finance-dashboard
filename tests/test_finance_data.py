import pandas as pd

from analytics.finance_data import (
    CANONICAL_COLUMNS,
    classify_dataset,
    normalize_finance_data,
    suggest_column_mapping,
    validate_finance_data,
)


def test_column_mapping_recognizes_common_finance_headers():
    mapping = suggest_column_mapping(["Transaction Date", "GL Account", "Narration", "Debit", "Credit", "Ref"])
    assert mapping["date"] == "Transaction Date"
    assert mapping["account"] == "GL Account"
    assert mapping["description"] == "Narration"
    assert mapping["reference"] == "Ref"


def test_normalize_finance_data_creates_canonical_schema_and_amount():
    raw = pd.DataFrame({
        "Transaction Date": ["2026-01-02"],
        "GL Account": ["Cash"],
        "Narration": ["Customer receipt"],
        "Debit": [0],
        "Credit": [150000],
        "Currency": ["NGN"],
    })
    normalized = normalize_finance_data(raw)
    assert list(normalized.columns) == CANONICAL_COLUMNS
    assert normalized.loc[0, "amount"] == 150000
    assert pd.notna(normalized.loc[0, "date"])


def test_validation_detects_invalid_dates_and_duplicates():
    frame = pd.DataFrame({
        "date": [pd.Timestamp("2026-01-01"), pd.NaT, pd.NaT],
        "account": ["Cash", "Cash", "Cash"],
        "description": ["A", "B", "B"],
        "debit": [0, 0, 0],
        "credit": [100, 200, 200],
        "amount": [100, 200, 200],
        "currency": ["NGN"] * 3,
        "category": ["Income"] * 3,
        "reference": ["1", "2", "2"],
        "entity": ["Main"] * 3,
    })
    result = validate_finance_data(frame)
    assert result.valid is False
    assert result.missing_dates == 2
    assert result.duplicate_rows == 1


def test_classifies_bank_statement_from_transaction_headers():
    profile = classify_dataset(["Transaction Date", "Narration", "Debit", "Credit", "Balance", "Reference"])
    assert profile.dataset_type == "bank_statement"
    assert profile.confidence >= 50
    assert "Bank Reconciliation" in profile.route


def test_classifies_general_ledger_from_gl_headers():
    profile = classify_dataset(["Posting Date", "GL Account", "Description", "Debit", "Credit"])
    assert profile.dataset_type == "general_ledger"
    assert "Financial Statement Analyzer" in profile.route


def test_classifies_budget_from_budget_headers():
    profile = classify_dataset(["Period", "Category", "Budget Amount", "Actual", "Variance"])
    assert profile.dataset_type == "budget"
    assert "Budget Analysis" in profile.route


def test_dataset_specific_validation_requires_ledger_account():
    frame = pd.DataFrame({
        "date": [pd.Timestamp("2026-01-01")], "account": [pd.NA], "description": ["Expense"],
        "debit": [100], "credit": [0], "amount": [-100], "currency": ["NGN"],
        "category": ["Expense"], "reference": ["1"], "entity": ["Main"],
    })
    result = validate_finance_data(frame, "general_ledger")
    assert result.valid is False
    assert any("account field" in error.lower() for error in result.errors)
