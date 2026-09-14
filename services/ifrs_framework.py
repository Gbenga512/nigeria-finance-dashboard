"""IFRS-oriented accounting controls used by NG Finance Pro.

This module provides explicit accounting-policy metadata and deterministic
classification helpers. It does not claim entity-level IFRS compliance;
final treatment depends on the entity's facts, elections and applicable
reporting framework.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IFRSRule:
    standard: str
    area: str
    principle: str
    status: str = "CONTROL"


IFRS_RULES = (
    IFRSRule("IAS 1", "Presentation", "Financial statements are presented consistently with material and faithfully represented information."),
    IFRSRule("IAS 7", "Cash flows", "Cash flows are classified as operating, investing or financing based on their nature."),
    IFRSRule("IFRS 15", "Revenue", "Revenue is recognised when performance obligations are satisfied, subject to the contract facts."),
    IFRSRule("IAS 2", "Inventory", "Inventory is measured at the lower of cost and net realisable value, subject to applicable requirements."),
    IFRSRule("IAS 16", "Property, plant and equipment", "PPE is recognised and subsequently measured using an applicable cost or revaluation model, with depreciation and impairment considered."),
    IFRSRule("IFRS 9", "Financial instruments", "Financial assets and liabilities are classified and measured according to their contractual cash-flow and business-model characteristics, with impairment requirements where applicable."),
    IFRSRule("IFRS 16", "Leases", "A lessee generally recognises a right-of-use asset and lease liability for leases within the standard's scope, subject to exemptions."),
    IFRSRule("IAS 12", "Income taxes", "Current and deferred tax are recognised and measured according to the applicable tax accounting requirements."),
    IFRSRule("IAS 37", "Provisions", "A provision is recognised only when the recognition criteria are satisfied; contingencies are disclosed where required."),
    IFRSRule("IAS 8", "Policies, estimates and errors", "Accounting policies, changes in estimates and errors are treated according to their respective requirements."),
    IFRSRule("IAS 21", "Foreign currency", "Foreign-currency transactions are initially recognised using the applicable spot exchange rate and subsequently treated according to the standard."),
    IFRSRule("IAS 36", "Impairment", "Assets are assessed for impairment when required and impairment losses are recognised subject to the standard."),
)


def framework_summary() -> list[dict[str, str]]:
    """Return IFRS control metadata suitable for a UI or report."""
    return [
        {"Standard": r.standard, "Area": r.area, "Principle": r.principle, "Status": r.status}
        for r in IFRS_RULES
    ]


def classify_cash_flow(counterpart_types: set[str]) -> str:
    """Classify a cash movement for IAS 7-style presentation.

    The classification is based on the nature of the non-cash counter-account;
    the caller remains responsible for entity-specific policy judgements.
    """
    types = {str(value) for value in counterpart_types}
    if types & {"Revenue", "Expense"}:
        return "Operating"
    if types & {"Asset"}:
        return "Investing"
    if types & {"Liability", "Equity"}:
        return "Financing"
    return "Operating"


def supplier_tax_treatment(tax_amount: float, recoverable: bool) -> tuple[str, float]:
    """Return the appropriate account concept for supplier tax.

    Recoverable input VAT is an asset/receivable rather than an expense.
    Non-recoverable tax remains part of the related cost/expense. The function
    intentionally requires an explicit recoverability decision.
    """
    amount = float(tax_amount)
    if amount < 0:
        raise ValueError("Tax amount cannot be negative.")
    return ("VAT Recoverable" if recoverable else "Related Cost / Expense", amount)


def invoice_tax_control(tax_amount: float, is_sales: bool, recoverable_input_tax: bool = True) -> dict[str, object]:
    """Return the controlled tax-side account treatment for an invoice."""
    amount = float(tax_amount)
    if amount < 0:
        raise ValueError("Tax amount cannot be negative.")
    if amount == 0:
        return {"account": None, "amount": 0.0, "classification": "No tax"}
    if is_sales:
        return {"account": "Tax Payable", "amount": amount, "classification": "Liability"}
    account, _ = supplier_tax_treatment(amount, recoverable_input_tax)
    return {"account": account, "amount": amount, "classification": "Asset" if recoverable_input_tax else "Expense"}
