from pathlib import Path
from services import personal_finance as pf
from services import personal_recurring as recurring
from analytics import personal_cashflow_forecast

def setup(tmp_path):
    pf.DB_PATH=Path(tmp_path)/"pf.db"
    pf.ensure_schema(); recurring.ensure_schema()
    aid=int(pf.accounts().iloc[0]["id"])
    return aid

def test_forecast_uses_recurring_income_and_expense(tmp_path):
    aid=setup(tmp_path)
    recurring.add_rule("Salary",100000,"Income","Salary",aid,"Monthly","2026-10-01")
    recurring.add_rule("Rent",30000,"Expense","Rent",aid,"Monthly","2026-10-05")
    out=personal_cashflow_forecast.forecast("2026-10-01",3)
    assert len(out)==3
    assert out.iloc[0]["Forecast Income"]==100000
    assert out.iloc[0]["Forecast Outflows"]==30000
    assert out.iloc[0]["Forecast Net Cash Flow"]==70000
    assert out.iloc[0]["Status"]=="ESTIMATE"
