from pathlib import Path
from analytics import personal_scenarios
from services import personal_finance as pf
from services import personal_recurring as recurring

def setup(tmp_path):
    pf.DB_PATH=Path(tmp_path)/"pf.db"
    pf.ensure_schema(); recurring.ensure_schema()
    aid=int(pf.accounts().iloc[0]["id"])
    return aid

def test_report_scenarios_are_included(tmp_path):
    aid=setup(tmp_path)
    recurring.add_rule("Salary",100000,"Income","Salary",aid,"Monthly","2026-10-01")
    recurring.add_rule("Rent",50000,"Expense","Rent",aid,"Monthly","2026-10-05")
    out=personal_scenarios.compare("2026-10-01",3)
    assert set(out["Scenario"])=={"Base Case","Conservative"}
    assert out.groupby("Scenario").size().to_dict()=={"Base Case":3,"Conservative":3}
