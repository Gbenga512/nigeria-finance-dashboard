from services import personal_finance


def test_personal_finance_schema_and_50_30_20(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", tmp_path / "personal.db")
    personal_finance.ensure_schema()
    accts = personal_finance.accounts()
    main = int(accts.loc[accts["name"] == "Main Bank", "id"].iloc[0])
    personal_finance.add_transaction("2026-01-05", "Salary", 100000, "Income", "Salary", main)
    personal_finance.add_transaction("2026-01-06", "Rent", 50000, "Expense", "Rent", main)
    personal_finance.add_transaction("2026-01-07", "Entertainment", 20000, "Expense", "Entertainment", main)
    personal_finance.add_transaction("2026-01-08", "Emergency fund", 20000, "Savings", "Emergency Fund", main)
    ratios = personal_finance.financial_ratios("2026-01-01", "2026-01-31")
    assert ratios["Needs Ratio"] == 0.5
    assert ratios["Wants Ratio"] == 0.2
    assert ratios["Savings/Investment Ratio"] == 0.2
    assert personal_finance.dashboard_metrics("2026-01-01", "2026-01-31")["income"] == 100000


def test_budget_variance(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", tmp_path / "personal.db")
    personal_finance.ensure_schema()
    accts = personal_finance.accounts(); main = int(accts.iloc[0]["id"])
    personal_finance.set_budget("2026-02", "Food", 50000)
    personal_finance.add_transaction("2026-02-10", "Groceries", 60000, "Expense", "Food", main)
    out = personal_finance.budget_variance("2026-02")
    row = out.loc[out["category"] == "Food"].iloc[0]
    assert row["actual"] == 60000
    assert row["variance"] == -10000
    assert row["status"] == "Over Budget"
