from pathlib import Path

from services import personal_finance
from services import personal_finance_wealth as wealth
from analytics import personal_data_quality


def test_data_quality_passes_clean_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "pf.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    result = personal_data_quality.data_quality_report()
    assert result["status"] == "PASS"


def test_data_quality_flags_duplicate_transactions(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "pf.db")
    personal_finance.ensure_schema()
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction("2026-09-01", "Salary", 100000, "Income", "Salary", account_id, reference="PAY1")
    personal_finance.add_transaction("2026-09-01", "Salary", 100000, "Income", "Salary", account_id, reference="PAY1")
    result = personal_data_quality.data_quality_report("2026-09-01", "2026-09-30")
    assert result["status"] == "REVIEW"
    assert "Potential duplicate transactions" in result["issues"]["Check"].tolist()
