from services import personal_finance as pf
from services import personal_finance_intelligence as pfi


def test_savings_movement_is_not_double_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    savings = int(pf.accounts().loc[pf.accounts()["name"] == "Savings", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.add_transaction("2026-01-06", "Emergency fund", 20000, "Savings", "Emergency Fund", savings)
    balances = pfi.account_balances("2026-01-31").set_index("name")
    assert balances.loc["Main Bank", "balance"] == 100000
    assert balances.loc["Savings", "balance"] == -20000


def test_net_worth_includes_liquid_cash_once(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.set_net_worth_item("Vehicle", "Asset", 500000, "2026-01-31")
    nw = pf.net_worth("2026-01-31")
    assert nw["cash"] == 100000
    assert nw["assets"] == 600000


def test_health_contains_semantic_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    result = pfi.financial_health("2026-01-01", "2026-01-31")
    assert result["data_quality"].startswith("FACT:")
    assert result["recommendation_note"].startswith("RECOMMENDATION:")
    assert all(item["Status"].split(":", 1)[0] in {"FACT", "CALCULATION", "ESTIMATE", "RECOMMENDATION"} for item in result["findings"])
