from services import personal_finance as pf
from services import personal_finance_intelligence as pfi
from services import personal_finance_wealth as wealth


def test_double_sided_transfer_balances(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    savings = int(pf.accounts().loc[pf.accounts()["name"] == "Savings", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    wealth.add_transfer("2026-01-06", "Emergency fund transfer", 20000, main, savings)
    balances = pfi.account_balances("2026-01-31").set_index("name")
    assert balances.loc["Main Bank", "balance"] == 80000
    assert balances.loc["Savings", "balance"] == 20000
    assert pfi.liquid_cash("2026-01-31") == 100000


def test_integrated_net_worth_includes_cash_investments_and_debt(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.set_net_worth_item("Vehicle", "Asset", 500000, "2026-01-31")
    wealth.add_investment("Treasury Portfolio", "Fixed Income", 200000, 210000, as_of_date="2026-01-31")
    wealth.add_debt("Personal Loan", 100000, 80000, interest_rate=15, minimum_payment=10000, as_of_date="2026-01-31")
    nw = wealth.integrated_net_worth("2026-01-31")
    assert nw["liquid_cash"] == 100000
    assert nw["investments"] == 210000
    assert nw["debts"] == 80000
    assert nw["assets"] == 810000
    assert nw["liabilities"] == 80000
    assert nw["net_worth"] == 730000


def test_savings_goal_progress_uses_linked_account_balance(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    savings = int(pf.accounts().loc[pf.accounts()["name"] == "Savings", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    wealth.add_transfer("2026-01-06", "Emergency fund", 25000, main, savings)
    wealth.add_savings_goal("Emergency Fund", 100000, "2026-12-31", savings)
    goals = wealth.savings_goals("2026-01-31")
    row = goals.iloc[0]
    assert row["current_amount"] == 25000
    assert row["progress_pct"] == 25


def test_emergency_coverage_is_based_on_liquid_cash_and_essential_expenses(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    pf.add_transaction("2026-01-06", "Rent", 20000, "Expense", "Rent", main)
    coverage = wealth.emergency_coverage("2026-01-01", "2026-01-31")
    assert coverage["liquid_cash"] == 80000
    assert coverage["essential_months"] > 3


def test_health_contains_semantic_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DB_PATH", tmp_path / "personal.db")
    pf.ensure_schema()
    main = int(pf.accounts().loc[pf.accounts()["name"] == "Main Bank", "id"].iloc[0])
    pf.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    result = pfi.financial_health("2026-01-01", "2026-01-31")
    assert result["data_quality"].startswith("FACT:")
    assert result["recommendation_note"].startswith("RECOMMENDATION:")
    assert all(item["Status"].split(":", 1)[0] in {"FACT", "CALCULATION", "ESTIMATE", "RECOMMENDATION"} for item in result["findings"])
