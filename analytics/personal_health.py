"""Transparent personal financial-health diagnostics.

The score is a planning indicator, not a credit score or regulated financial advice.
Every component is derived from recorded data and explicit configured thresholds.
"""
from __future__ import annotations

import pandas as pd

from services import personal_finance as pf
from services import personal_finance_wealth as wealth


def health_score(start: str, end: str) -> dict:
    settings = pf.settings()
    ratios = pf.financial_ratios(start, end)
    metrics = pf.dashboard_metrics(start, end)
    coverage = wealth.emergency_coverage(start, end)

    components = []

    def component(name, score, basis):
        components.append({"Component": name, "Score": round(float(score), 1), "Basis": basis})

    savings = ratios.get("Savings Rate")
    target = float(settings["savings_target"])
    component(
        "Savings / Investment",
        0 if savings is None else min(100, max(0, savings / target * 100)) if target else 100,
        "Actual savings/investment contributions versus configured target.",
    )

    needs = ratios.get("Needs Ratio")
    needs_target = float(settings["needs_target"])
    component(
        "Needs Allocation",
        100 if needs is None else min(100, max(0, (needs_target / needs) * 100)) if needs > 0 else 100,
        "Need-classified spending versus configured allocation target.",
    )

    wants = ratios.get("Wants Ratio")
    wants_target = float(settings["wants_target"])
    component(
        "Wants Allocation",
        100 if wants is None else min(100, max(0, (wants_target / wants) * 100)) if wants > 0 else 100,
        "Want-classified spending versus configured allocation target.",
    )

    emergency = coverage.get("essential_months")
    emergency_target = float(settings["emergency_months_target"])
    component(
        "Emergency Coverage",
        0 if emergency is None else min(100, max(0, emergency / emergency_target * 100)) if emergency_target else 100,
        "Liquid cash/savings divided by average monthly essential recorded expenses.",
    )

    income = float(metrics["income"])
    debt_ratio = ratios.get("Debt Repayment Ratio")
    debt_target = float(settings["debt_ratio_target"])
    component(
        "Debt Repayment Load",
        100 if debt_ratio is None else min(100, max(0, (debt_target / debt_ratio) * 100)) if debt_ratio > 0 else 100,
        "Recorded debt payments relative to income versus configured planning target.",
    )

    cash_flow_score = 100 if metrics["net_cash_flow"] >= 0 else 0
    component(
        "Net Cash Flow",
        cash_flow_score,
        "Income less recorded expenses, savings/investments and debt payments.",
    )

    score = round(sum(x["Score"] for x in components) / len(components), 1)
    return {
        "score": score,
        "components": pd.DataFrame(components),
        "label": (
            "Strong planning position" if score >= 80
            else "Watch planning position" if score >= 60
            else "Needs attention"
        ),
        "status": (
            "CALCULATION: transparent planning score derived from six recorded-data components."
        ),
    }
