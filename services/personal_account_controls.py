"""Controlled personal-account lifecycle operations."""
from __future__ import annotations

import math

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


ACCOUNT_TYPES = ("Cash", "Savings", "Investment", "Other Asset")


def _amount(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Opening balance must be finite")
    return value


def update_account(account_id: int, name: str, account_type: str, opening_balance: float) -> None:
    pf.ensure_schema()
    name = name.strip()
    if not name:
        raise ValueError("Account name is required")
    if account_type not in ACCOUNT_TYPES:
        raise ValueError("Invalid account type")
    amount = _amount(opening_balance)
    with pf.connect() as conn:
        row = conn.execute(
            "SELECT id FROM personal_accounts WHERE id=? AND active=1", (int(account_id),)
        ).fetchone()
        if row is None:
            raise ValueError("Personal account does not exist")
        duplicate = conn.execute(
            "SELECT 1 FROM personal_accounts WHERE name=? AND id<>?",
            (name, int(account_id)),
        ).fetchone()
        if duplicate:
            raise ValueError("An account with this name already exists")
        conn.execute(
            "UPDATE personal_accounts SET name=?,account_type=?,opening_balance=? WHERE id=?",
            (name, account_type, amount, int(account_id)),
        )


def account_usage(account_id: int) -> dict:
    pf.ensure_schema()
    wealth.ensure_schema()
    with pf.connect() as conn:
        transactions = int(
            conn.execute(
                "SELECT COUNT(*) FROM personal_transactions WHERE account_id=?",
                (int(account_id),),
            ).fetchone()[0]
        )
        transfers = int(
            conn.execute(
                "SELECT COUNT(*) FROM personal_transfers WHERE from_account_id=? OR to_account_id=?",
                (int(account_id), int(account_id)),
            ).fetchone()[0]
        )
        goals = int(
            conn.execute(
                "SELECT COUNT(*) FROM personal_savings_goals WHERE linked_account_id=?",
                (int(account_id),),
            ).fetchone()[0]
        )
    return {"transactions": transactions, "transfers": transfers, "goals": goals}


def deactivate_account(account_id: int) -> None:
    """Archive an unused account; accounts with activity must remain available."""
    pf.ensure_schema()
    usage = account_usage(account_id)
    if any(usage.values()):
        raise ValueError(
            "This account has recorded activity and cannot be archived. "
            "Keep it active for historical reporting."
        )
    with pf.connect() as conn:
        updated = conn.execute(
            "UPDATE personal_accounts SET active=0 WHERE id=? AND active=1",
            (int(account_id),),
        ).rowcount
        if updated != 1:
            raise ValueError("Personal account does not exist or is already archived")
