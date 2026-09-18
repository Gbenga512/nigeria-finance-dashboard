"""Professional personal finance reporting pack."""
from __future__ import annotations

from datetime import datetime

from services import personal_finance as pf
from services import personal_finance_wealth as wealth
from services import personal_net_worth_history as nw_history
from services import personal_debt_payments as debt_payments
from services import personal_investment_history as investment_history
from analytics import personal_allocation, personal_health, personal_data_quality
from analytics import personal_scenarios


def report_pack(start: str, end: str) -> dict:
    metrics = pf.dashboard_metrics(start, end)
    ratios = pf.financial_ratios(start, end)
    allocation = personal_allocation.allocation_report(start, end)
    health = personal_health.health_score(start, end)
    quality = personal_data_quality.data_quality_report(start, end)
    net_worth = wealth.integrated_net_worth(end)
    debts = debt_payments.debt_summary(end)
    investments = investment_history.performance_summary(end)
    statement = pf.monthly_statement(int(end[:4]))

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "period": {"start": start, "end": end},
        "metrics": metrics,
        "ratios": ratios,
        "allocation": allocation,
        "health": health,
        "data_quality": quality,
        "net_worth": net_worth,
        "debts": debts,
        "investments": investments,
        "monthly_statement": statement,
        "scenarios": personal_scenarios.compare(end, 6),
        "status": "FACT/CALCULATION: report derived from recorded Personal Finance data and configured planning assumptions.",
    }


def executive_summary(pack: dict) -> list[str]:
    m = pack["metrics"]
    nw = pack["net_worth"]
    h = pack["health"]["score"]
    q = pack["data_quality"]["status"]
    return [
        f"Income recorded: {m['income']:,.2f}. Expenses recorded: {m['expenses']:,.2f}.",
        f"Net savings before separate allocation movements: {m['net_savings']:,.2f}.",
        f"Integrated net worth at period end: {nw['net_worth']:,.2f}.",
        f"Financial Health Indicator: {h:.1f}/100.",
        f"Data-quality status: {q}.",
    ]


def report_text(pack: dict) -> str:
    s = pack["period"]
    lines = [
        "NG FINANCE PRO — PERSONAL FINANCE REPORT",
        f"Period: {s['start']} to {s['end']}",
        f"Generated: {pack['generated_at']}",
        "",
        "EXECUTIVE SUMMARY",
    ]
    lines.extend(f"- {x}" for x in executive_summary(pack))
    lines += ["", "FINANCIAL HEALTH COMPONENTS"]
    for _, row in pack["health"]["components"].iterrows():
        lines.append(f"- {row['Component']}: {row['Score']:.1f}/100 — {row['Basis']}")
    lines += ["", "DATA QUALITY"]
    for _, row in pack["data_quality"]["checks"].iterrows():
        lines.append(f"- {row['Check']}: {row['Status']} ({int(row['Count'])}) — {row['Detail']}")
    lines += [
        "",
        "DISCLOSURE",
        "This report is a financial-management summary derived from recorded user data.",
        "Planning indicators are calculations, not regulated financial advice or credit assessments.",
    ]
    return "\n".join(lines)
