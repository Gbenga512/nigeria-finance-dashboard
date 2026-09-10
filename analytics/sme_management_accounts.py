"""Management-account analytics built from posted SME double-entry journals."""
from __future__ import annotations

import pandas as pd

from services.sme_accounting import balance_sheet, cash_flow, profit_and_loss, trial_balance


def _ratio(numerator: float, denominator: float):
    return round(float(numerator) / float(denominator), 4) if denominator else None


def management_accounts(business_id: int, start, end) -> dict:
    """Return transparent management KPIs; values are actuals from posted journals."""
    pnl = profit_and_loss(business_id, start, end)
    bs = balance_sheet(business_id, end)
    tb = trial_balance(business_id, None, end)
    cf = cash_flow(business_id, start, end)

    revenue = pnl["Revenue"]
    expenses = pnl["Expenses"]
    net_income = pnl["Net Income"]
    cogs = float(tb.loc[(tb["Type"] == "Expense") & (tb["Account"].str.contains("Cost of Goods Sold", case=False, na=False)), "Debits"].sum()) if not tb.empty else 0.0
    gross_profit = revenue - cogs
    operating_expenses = max(0.0, expenses - cogs)
    cash = float(tb.loc[tb["Account"].isin(["Main Bank", "Cash on Hand"]), "Balance"].sum()) if not tb.empty else 0.0
    current_assets = float(tb.loc[(tb["Type"] == "Asset") & (tb["Account"].isin(["Main Bank", "Cash on Hand", "Accounts Receivable", "Inventory"])), "Balance"].sum()) if not tb.empty else 0.0
    current_liabilities = float(-tb.loc[(tb["Type"] == "Liability") & (tb["Account"].isin(["Accounts Payable", "Tax Payable"])), "Balance"].sum()) if not tb.empty else 0.0
    quick_assets = current_assets - float(tb.loc[(tb["Account"] == "Inventory"), "Balance"].sum()) if not tb.empty else current_assets

    risks = []
    if revenue <= 0:
        risks.append({"Risk": "No recorded revenue", "WHY": "No posted revenue was found in the selected period; profitability ratios are not meaningful."})
    if net_income < 0:
        risks.append({"Risk": "Loss position", "WHY": "Recorded expenses exceed recorded revenue for the selected period."})
    if current_liabilities > 0 and current_assets < current_liabilities:
        risks.append({"Risk": "Weak current coverage", "WHY": "Recorded current assets are below recorded current liabilities."})
    if not bs["Balanced"]:
        risks.append({"Risk": "Balance sheet imbalance", "WHY": "The accounting equation does not reconcile; investigate journals before relying on management reports."})
    if not risks:
        risks.append({"Risk": "No critical rule-based flag", "WHY": "The available posted ledger data did not trigger the configured management-risk rules."})

    recommendations = []
    if net_income < 0:
        recommendations.append("Review the largest expense accounts and test whether costs are recurring, discretionary or directly linked to revenue generation.")
    if current_liabilities > 0 and current_assets < current_liabilities:
        recommendations.append("Prioritise short-term liquidity planning and supplier/tax payment scheduling.")
    if not recommendations:
        recommendations.append("Maintain monthly close discipline and monitor revenue concentration, margins and liquidity as transaction history grows.")

    return {
        "period": {"start": str(start), "end": str(end)},
        "kpis": {"revenue": revenue, "cogs": cogs, "gross_profit": gross_profit, "gross_margin": _ratio(gross_profit, revenue), "operating_expenses": operating_expenses, "net_income": net_income, "net_margin": _ratio(net_income, revenue), "cash": cash, "current_assets": current_assets, "current_liabilities": current_liabilities, "working_capital": current_assets - current_liabilities, "current_ratio": _ratio(current_assets, current_liabilities), "quick_ratio": _ratio(quick_assets, current_liabilities), "cash_flow": float(cf["Net Cash Flow"].sum()) if not cf.empty else 0.0},
        "balance_sheet": bs,
        "risks": risks,
        "recommendations": recommendations,
        "data_labels": {"actuals": "FACT: sourced from posted double-entry journals.", "ratios": "CALCULATION: derived from the posted ledger.", "forecast": "ESTIMATE: modelled separately and never presented as an actual.", "recommendation": "RECOMMENDATION: decision-support, not professional advice."},
    }


def account_performance(business_id: int, start, end) -> pd.DataFrame:
    tb = trial_balance(business_id, start, end)
    if tb.empty:
        return pd.DataFrame(columns=["Account", "Type", "Amount"])
    out = tb[["Account", "Type", "Balance"]].copy()
    out["Amount"] = out["Balance"].abs()
    return out[["Account", "Type", "Amount"]].sort_values("Amount", ascending=False).reset_index(drop=True)
