"""Controlled lifecycle operations for personal transactions.

This module adds product-grade edit/delete controls without changing the
existing Personal Finance transaction schema. Every mutation writes an audit
record before applying the change. Hard deletion is intentionally supported
only through this controlled service so ordinary UI code does not need direct
SQL access.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date
from typing import Any

from services import personal_finance

AUDIT_ACTIONS = ("CREATE", "UPDATE", "DELETE")


def ensure_schema() -> None:
    personal_finance.ensure_schema()
    with personal_finance.connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS personal_transaction_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('CREATE','UPDATE','DELETE')),
                before_json TEXT,
                after_json TEXT,
                reason TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_pf_audit_transaction
                ON personal_transaction_audit(transaction_id);
            CREATE INDEX IF NOT EXISTS idx_pf_audit_created
                ON personal_transaction_audit(created_at);
            """
        )


def _validate_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("Transaction date must be YYYY-MM-DD") from exc


def _validate_amount(value: float) -> float:
    amount = float(value)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a finite positive number")
    return amount


def _snapshot(conn: sqlite3.Connection, transaction_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id,transaction_date,description,amount,transaction_type,"
        "category,classification,account_id,payment_method,reference,notes,created_at "
        "FROM personal_transactions WHERE id=?",
        (int(transaction_id),),
    ).fetchone()
    if row is None:
        raise ValueError("Personal transaction does not exist")
    return dict(row)


def _audit(
    conn: sqlite3.Connection,
    transaction_id: int,
    action: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    reason: str = "",
) -> None:
    if action not in AUDIT_ACTIONS:
        raise ValueError("Invalid audit action")
    conn.execute(
        "INSERT INTO personal_transaction_audit"
        "(transaction_id,action,before_json,after_json,reason) VALUES (?,?,?,?,?)",
        (
            int(transaction_id),
            action,
            json.dumps(before, default=str, sort_keys=True) if before else None,
            json.dumps(after, default=str, sort_keys=True) if after else None,
            reason.strip(),
        ),
    )


def record_create(transaction_id: int, reason: str = "Transaction created") -> None:
    """Record creation of an already-created transaction."""
    ensure_schema()
    with personal_finance.connect() as conn:
        after = _snapshot(conn, transaction_id)
        _audit(conn, transaction_id, "CREATE", None, after, reason)


def update_transaction(
    transaction_id: int,
    *,
    transaction_date: str,
    description: str,
    amount: float,
    transaction_type: str,
    category: str,
    account_id: int,
    payment_method: str = "",
    reference: str = "",
    notes: str = "",
    reason: str = "Transaction amended",
) -> None:
    """Amend a personal transaction and retain before/after audit evidence."""
    ensure_schema()
    parsed = _validate_date(transaction_date)
    amount = _validate_amount(amount)
    if transaction_type not in personal_finance.PERSONAL_TYPES:
        raise ValueError("Invalid personal transaction type")
    if transaction_type == "Transfer":
        raise ValueError("Use the Transfers workspace to amend account transfers")
    description = description.strip()
    category = category.strip()
    if not description:
        raise ValueError("Description is required")
    if not category:
        raise ValueError("Category is required")

    with personal_finance.connect() as conn:
        before = _snapshot(conn, transaction_id)
        if not conn.execute(
            "SELECT 1 FROM personal_accounts WHERE id=? AND active=1", (int(account_id),)
        ).fetchone():
            raise ValueError("Selected personal account does not exist")

        classification = conn.execute(
            "SELECT classification FROM personal_categories WHERE name=? AND active=1",
            (category,),
        ).fetchone()
        if classification is None:
            raise ValueError("Selected category does not exist")
        cls = classification[0]

        conn.execute(
            "UPDATE personal_transactions SET transaction_date=?,description=?,amount=?,"
            "transaction_type=?,category=?,classification=?,account_id=?,payment_method=?,"
            "reference=?,notes=? WHERE id=?",
            (
                parsed,
                description,
                amount,
                transaction_type,
                category,
                cls,
                int(account_id),
                payment_method.strip(),
                reference.strip(),
                notes.strip(),
                int(transaction_id),
            ),
        )
        after = _snapshot(conn, transaction_id)
        _audit(conn, transaction_id, "UPDATE", before, after, reason)


def delete_transaction(transaction_id: int, reason: str = "Transaction deleted") -> None:
    """Delete a transaction only through the controlled, audited pathway."""
    ensure_schema()
    with personal_finance.connect() as conn:
        before = _snapshot(conn, transaction_id)
        _audit(conn, transaction_id, "DELETE", before, None, reason)
        conn.execute("DELETE FROM personal_transactions WHERE id=?", (int(transaction_id),))


def audit_log(transaction_id: int | None = None) -> list[dict[str, Any]]:
    ensure_schema()
    with personal_finance.connect() as conn:
        if transaction_id is None:
            rows = conn.execute(
                "SELECT * FROM personal_transaction_audit ORDER BY id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM personal_transaction_audit "
                "WHERE transaction_id=? ORDER BY id DESC",
                (int(transaction_id),),
            ).fetchall()
    return [dict(row) for row in rows]
