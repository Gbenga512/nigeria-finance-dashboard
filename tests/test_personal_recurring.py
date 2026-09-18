from datetime import date
from pathlib import Path
from services import personal_finance as pf
from services import personal_recurring as recurring

def setup(tmp_path):
    pf.DB_PATH=Path(tmp_path)/"pf.db"
    pf.ensure_schema(); recurring.ensure_schema()
    return pf.accounts().iloc[0]["id"], pf.categories("Expense").iloc[0]["name"]

def test_add_and_due_rule(tmp_path):
    aid,cat=setup(tmp_path)
    rid=recurring.add_rule("Rent",100000,"Expense",cat,int(aid),"Monthly","2026-01-15")
    assert rid>0
    assert len(recurring.due_rules("2026-02-01"))==1

def test_post_due_is_idempotent(tmp_path):
    aid,cat=setup(tmp_path)
    recurring.add_rule("Rent",100000,"Expense",cat,int(aid),"Monthly","2026-01-15")
    first=recurring.post_due("2026-01-20")
    second=recurring.post_due("2026-01-20")
    assert len(first)==1
    assert second==[]
    assert len(pf.transactions())==1
