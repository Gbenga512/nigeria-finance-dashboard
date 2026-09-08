import pandas as pd

from analytics.ratios import calculate_ratios
from analytics.reconciliation import normalize_transactions, reconcile
from analytics.financial_health import financial_health_score


def test_ratios_and_health_score():
    bs = {"Cash & Cash Equivalents": 100, "Inventory": 50, "Current Assets": 300, "Current Liabilities": 150, "Total Assets": 1000, "Total Liabilities": 400, "Total Equity": 600, "Total Debt": 250}
    pnl = {"Revenue": 1000, "Gross Profit": 400, "Operating Profit": 200, "Net Income": 120, "Interest Expense": 40}
    cf = {"Operating Cash Flow": 180}
    ratios = calculate_ratios(bs, pnl, cf)
    score, detail = financial_health_score(ratios)
    assert ratios.loc[ratios["Ratio"] == "Current Ratio", "Value"].iloc[0] == 2.0
    assert score is not None and 0 <= score <= 100
    assert len(detail) == 5


def test_reconciliation_matches_once():
    bank = normalize_transactions(pd.DataFrame({"Date": ["2026-01-01", "2026-01-03"], "Amount": [100, 200]}), "Bank")
    cash = normalize_transactions(pd.DataFrame({"Date": ["2026-01-02", "2026-01-10"], "Amount": [100, 300]}), "Cashbook")
    bank_out, cash_out, matches = reconcile(bank, cash, 3)
    assert len(matches) == 1
    assert int(bank_out["Matched"].sum()) == 1
    assert int(cash_out["Matched"].sum()) == 1
