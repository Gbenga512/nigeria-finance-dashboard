from pathlib import Path
from services import personal_finance as pf
from services import personal_recurring as recurring
from analytics import personal_cashflow_forecast, personal_scenarios

def setup(tmp_path):
    pf.DB_PATH=Path(tmp_path)/"pf.db"
    pf.ensure_schema(); recurring.ensure_schema()
    return int(pf.accounts().iloc[0]["id"])

def test_scenarios_change_cash_outcome(tmp_path):
    aid=setup(tmp_path)
    recurring.add_rule("Salary",100000,"Income","Salary",aid,"Monthly","2026-10-01")
    recurring.add_rule("Rent",50000,"Expense","Rent",aid,"Monthly","2026-10-05")
    base=personal_scenarios.project("2026-10-01",3,personal_scenarios.Scenario("Base Case"))
    cons=personal_scenarios.project("2026-10-01",3,personal_scenarios.Scenario("Conservative",-10,10))
    assert cons.iloc[-1]["Projected Closing Cash"] < base.iloc[-1]["Projected Closing Cash"]
    assert set(base["Status"])=={"ESTIMATE / SCENARIO"}
