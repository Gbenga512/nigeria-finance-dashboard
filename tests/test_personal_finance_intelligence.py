from services import personal_finance as pf
from services import personal_finance_intelligence as pfi
from services import personal_finance_wealth as wealth


def test_account_balances_and_liquid_cash(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    savings = int(pf.accounts().loc[pf.accounts()["name"] == "Savings", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.add_transaction("2026-01-06", "Rent", 40000, "Expense", "Rent", main)
    wealth.add_transfer("2026-01-07", "Emergency fund transfer", 20000, main, savings)
    balances = pfi.account_balances("2026-01-31").set_index("name")
    assert balances.loc["Main Bank", "balance"] == 40000
    assert balances.loc["Savings", "balance"] == 20000
    assert pfi.liquid_cash("2026-01-31") == 60000


def test_health_is_explainable(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.add_transaction("2026-01-06", "Rent", 60000, "Expense", "Rent", main)
    result = pfi.financial_health("2026-01-01", "2026-01-31")
    assert result["findings"]
    assert all("Status" in item and "Explanation" in item for item in result["findings"])
