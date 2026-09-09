import pandas as pd
from io import BytesIO

from services.sme_import import parse_statement, suggest_categories


def test_parse_csv_does_not_post_and_detects_duplicates():
    raw = b"Date,Description,Debit,Credit,Reference\n2026-01-01,Rent,50000,,R1\n2026-01-02,Customer payment,,120000,R2\n2026-01-02,Customer payment,,120000,R2\n"
    out = parse_statement(raw, "bank.csv")
    assert len(out) == 3
    assert out["duplicate"].sum() == 2
    assert out.loc[0, "transaction_type"] == "Expense"
    assert out.loc[1, "transaction_type"] == "Income"


def test_category_learning_precedes_keyword_rules():
    review = pd.DataFrame({"description": ["ACME monthly payment"], "amount": [1000]})
    history = pd.DataFrame({"description": ["ACME monthly payment"], "category": ["Sales Receipt"]})
    out = suggest_categories(review, history)
    assert out.loc[0, "suggested_category"] == "Sales Receipt"


def test_rejects_unrecognised_format():
    try:
        parse_statement(b"x", "statement.pdf")
        assert False
    except ValueError as exc:
        assert "CSV and Excel" in str(exc)
