from pathlib import Path

from services import personal_finance
from services import personal_finance_wealth as wealth
from analytics import personal_report


def test_report_pack_contains_core_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "pf.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    result = personal_report.report_pack("2026-09-01", "2026-09-30")
    assert set(["metrics", "ratios", "allocation", "health", "data_quality", "net_worth", "debts", "investments"]).issubset(result)
    assert result["status"].startswith("FACT/CALCULATION:")


def test_report_text_is_reproducible_from_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "pf.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    pack = personal_report.report_pack("2026-09-01", "2026-09-30")
    text = personal_report.report_text(pack)
    assert "NG FINANCE PRO — PERSONAL FINANCE REPORT" in text
    assert "EXECUTIVE SUMMARY" in text
    assert "DATA QUALITY" in text
    assert "DISCLOSURE" in text
