from pathlib import Path

import pytest

from services import personal_debt_payments as debt_payments
from services import personal_finance
from services import personal_finance_wealth as wealth


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_finance, "DB_PATH", Path(tmp_path) / "personal.db")
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    debt_payments.ensure_schema()
    yield


def test_link_debt_payment_reconciles_and_reduces_calculated_balance(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    debt_id = wealth.add_debt("Car Loan", 1_000_000, 800_000, as_of_date="2026-09-01")
    tx_id = personal_finance.add_transaction("2026-09-15", "Loan payment", 120_000, "Debt Payment", "Debt Repayment", account_id)
    debt_payments.link_payment(tx_id, debt_id, 100_000, 20_000)
    summary = debt_payments.debt_summary("2026-09-30").set_index("id")
    assert summary.loc[debt_id, "linked_principal"] == 100_000
    assert summary.loc[debt_id, "linked_interest"] == 20_000
    assert summary.loc[debt_id, "calculated_balance"] == 700_000


def test_payment_must_reconcile_to_transaction_amount(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    debt_id = wealth.add_debt("Loan", 500_000, 500_000, as_of_date="2026-09-01")
    tx_id = personal_finance.add_transaction("2026-09-10", "Payment", 50_000, "Debt Payment", "Debt Repayment", account_id)
    with pytest.raises(ValueError, match="equal the transaction amount"):
        debt_payments.link_payment(tx_id, debt_id, 40_000, 0)


def test_payment_cannot_be_linked_twice(isolated_db):
    account_id = int(personal_finance.accounts().iloc[0]["id"])
    debt_id = wealth.add_debt("Loan", 500_000, 500_000, as_of_date="2026-09-01")
    tx_id = personal_finance.add_transaction("2026-09-10", "Payment", 50_000, "Debt Payment", "Debt Repayment", account_id)
    debt_payments.link_payment(tx_id, debt_id, 50_000, 0)
    with pytest.raises(ValueError, match="already linked"):
        debt_payments.link_payment(tx_id, debt_id, 50_000, 0)