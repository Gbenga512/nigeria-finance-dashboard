"""Personal Finance data-quality and control diagnostics."""
from __future__ import annotations

import math
import pandas as pd

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


def data_quality_report(start: str | None = None, end: str | None = None) -> dict:
    tx = pf.transactions(start, end)
    issues = []
    checks = []

    def check(name, status, detail, count=0):
        checks.append({"Check": name, "Status": status, "Count": int(count), "Detail": detail})
        if count:
            issues.append({"Check": name, "Count": int(count), "Detail": detail})

    if tx.empty:
        check("Transaction population", "INFO", "No transactions exist in the selected period.")
    else:
        check("Transaction population", "PASS", "Transactions are available for validation.", 0)
        bad_amount = int((~pd.to_numeric(tx["amount"], errors="coerce").map(math.isfinite) | (tx["amount"] <= 0)).sum())
        check("Invalid amounts", "PASS" if bad_amount == 0 else "FAIL", "Amounts must be finite and positive.", bad_amount)
        missing_desc = int(tx["description"].fillna("").astype(str).str.strip().eq("").sum())
        check("Missing descriptions", "PASS" if missing_desc == 0 else "WARN", "Every transaction should have a meaningful description.", missing_desc)
        missing_category = int(tx["category"].fillna("").astype(str).str.strip().eq("").sum())
        check("Missing categories", "PASS" if missing_category == 0 else "WARN", "Every transaction should have a category.", missing_category)
        unknown_class = int(~tx["classification"].isin(pf.CLASSIFICATIONS).sum())
        check("Invalid classifications", "PASS" if unknown_class == 0 else "FAIL", "Classification must be Need, Want or Savings.", unknown_class)
        orphan_accounts = int(tx["account_id"].isna().sum())
        check("Missing account links", "PASS" if orphan_accounts == 0 else "FAIL", "Every transaction must link to an account.", orphan_accounts)

        duplicate_keys = int(tx.duplicated(
            subset=["transaction_date", "description", "amount", "transaction_type", "account_id", "reference"],
            keep=False
        ).sum())
        check("Potential duplicate transactions", "PASS" if duplicate_keys == 0 else "WARN", "Rows with identical core fields should be reviewed for duplication.", duplicate_keys)

    accounts = pf.accounts()
    negative_balances = 0
    if not accounts.empty:
        balances = wealth.account_balances(end)
        negative_balances = int((balances["balance"] < 0).sum())
    check(
        "Negative account balances",
        "PASS" if negative_balances == 0 else "WARN",
        "Negative balances may be valid overdrafts; review them before relying on liquidity metrics.",
        negative_balances,
    )

    inv = wealth.investments(end)
    stale = 0
    if not inv.empty:
        dates = pd.to_datetime(inv["as_of_date"], errors="coerce")
        cutoff = pd.Timestamp(end or pd.Timestamp.today().date()) - pd.Timedelta(days=90)
        stale = int((dates < cutoff).sum())
    check(
        "Stale investment valuations",
        "PASS" if stale == 0 else "WARN",
        "Investment valuations older than 90 days should be reviewed for freshness.",
        stale,
    )

    status = "PASS" if not issues else "REVIEW"
    return {
        "status": status,
        "checks": pd.DataFrame(checks),
        "issues": pd.DataFrame(issues),
        "status_note": "CALCULATION: diagnostics are deterministic checks against recorded Personal Finance data.",
    }
