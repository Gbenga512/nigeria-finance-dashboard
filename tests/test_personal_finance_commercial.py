from services import personal_finance


def test_three_commercial_categories_are_calculated(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", tmp_path / "personal.db")
    personal_finance.ensure_schema()
    accounts = personal_finance.accounts()
    main = int(accounts.loc[accounts["name"] == "Main Bank", "id"].iloc[0])
    personal_finance.add_transaction("2026-03-01", "Salary", 200000, "Income", "Salary", main)
    personal_finance.add_transaction("2026-03-02", "Rent", 80000, "Expense", "Rent", main)
    personal_finance.add_transaction("2026-03-03", "Dining", 20000, "Expense", "Entertainment", main)
    personal_finance.add_transaction("2026-03-04", "Emergency fund", 30000, "Savings", "Emergency Fund", main)
    personal_finance.add_transaction("2026-03-05", "Investment", 20000, "Investment", "Investment", main)

    out = personal_finance.classification_summary("2026-03-01", "2026-03-31").set_index("Classification")
    assert out.loc["Need", "Amount"] == 80000
    assert out.loc["Want", "Amount"] == 20000
    assert out.loc["Savings", "Amount"] == 50000
    assert out.loc["Need", "Share of Income"] == 0.4
    assert out.loc["Want", "Share of Income"] == 0.1
    assert out.loc["Savings", "Share of Income"] == 0.25


def test_savings_and_investment_are_not_treated_as_expenses(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", tmp_path / "personal.db")
    personal_finance.ensure_schema()
    main = int(personal_finance.accounts().iloc[0]["id"])
    personal_finance.add_transaction("2026-04-01", "Salary", 100000, "Income", "Salary", main)
    personal_finance.add_transaction("2026-04-02", "Food", 30000, "Expense", "Food", main)
    personal_finance.add_transaction("2026-04-03", "Savings", 20000, "Savings", "Emergency Fund", main)
    personal_finance.add_transaction("2026-04-04", "Fund", 10000, "Investment", "Investment", main)
    metrics = personal_finance.dashboard_metrics("2026-04-01", "2026-04-30")
    assert metrics["expenses"] == 30000
    assert metrics["net_savings"] == 70000
    assert metrics["savings"] == 30000
