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

    tx = personal_finance.transactions("2026-03-01", "2026-03-31")
    need = float(tx.loc[(tx["transaction_type"] == "Expense") & (tx["classification"] == "Need"), "amount"].sum())
    want = float(tx.loc[(tx["transaction_type"] == "Expense") & (tx["classification"] == "Want"), "amount"].sum())
    savings = float(tx.loc[(tx["classification"] == "Savings") | (tx["transaction_type"].isin(["Savings", "Investment"])), "amount"].sum())
    assert need == 80000
    assert want == 20000
    assert savings == 50000
    assert need / 200000 == 0.4
    assert want / 200000 == 0.1
    assert savings / 200000 == 0.25


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
