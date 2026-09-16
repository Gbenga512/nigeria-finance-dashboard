"""Explainable personal-finance intelligence for NG Finance Pro."""
from __future__ import annotations
import pandas as pd
from services import personal_finance as pf
from services import personal_finance_wealth as wealth

def account_balances(as_of=None):
    """Return balances including explicit double-sided transfers."""
    return wealth.account_balances(as_of)

def liquid_cash(as_of=None):
    return wealth.liquid_cash(as_of)

def financial_health(start, end):
    s=pf.settings(); r=pf.financial_ratios(start,end); d=pf.dashboard_metrics(start,end); findings=[]
    coverage=wealth.emergency_coverage(start,end)
    def add(metric,status,explanation): findings.append({'Metric':metric,'Status':status,'Explanation':explanation})
    sr=r.get('Savings Rate')
    if sr is None: add('Savings Rate','FACT: insufficient income data','No recorded income exists for the selected period; the ratio cannot be calculated.')
    elif sr < s['savings_target']: add('Savings Rate','CALCULATION: below target','Recorded savings and investment contributions relative to income are below the configured planning target.')
    else: add('Savings Rate','CALCULATION: at/above target','Recorded savings and investment contributions relative to income meet or exceed the configured planning target.')
    if r.get('Needs Ratio') is not None and r['Needs Ratio'] > s['needs_target']: add('Needs Allocation','CALCULATION: above target','Need-classified expenses exceed the configured planning allocation target.')
    if r.get('Wants Ratio') is not None and r['Wants Ratio'] > s['wants_target']: add('Wants Allocation','CALCULATION: above target','Want-classified expenses exceed the configured planning allocation target.')
    ec=coverage.get('essential_months')
    if ec is not None and ec < s['emergency_months_target']: add('Emergency Fund','CALCULATION: below target',f'Liquid cash and savings cover about {ec:.1f} months of average essential recorded expenses versus the configured {s["emergency_months_target"]:.1f}-month target.')
    if d['net_cash_flow'] < 0: add('Cash Flow','FACT: negative after allocations','Recorded expenses, savings/investments and debt payments exceed recorded income in the selected period.')
    if not findings: add('Financial Health','CALCULATION: no configured threshold breached','No configured planning threshold was breached by the available recorded data.')
    return {'findings':findings,'data_quality':'FACT: based only on recorded transactions, account balances and configured planning assumptions.','recommendation_note':'RECOMMENDATION: review flagged ratios, liquidity and debt commitments before changing allocations.'}

def monthly_cash_flow(fiscal_year):
    stmt=pf.monthly_statement(fiscal_year).copy()
    if 'Cash Flow After Allocations' not in stmt:
        stmt['Cash Flow After Allocations']=stmt['Income']-stmt['Expenses']-stmt['Savings/Investment']-stmt['Debt Payments']
    out=stmt[['Month','Income','Expenses','Savings/Investment','Debt Payments','Cash Flow After Allocations']].copy()
    opening=float(pf.settings()['opening_cash']); openings=[]; closings=[]
    for _,row in out.iterrows():
        openings.append(opening); opening += float(row['Cash Flow After Allocations']); closings.append(opening)
    out['Opening Balance']=openings; out['Closing Balance']=closings
    return out[['Month','Opening Balance','Income','Expenses','Savings/Investment','Debt Payments','Cash Flow After Allocations','Closing Balance']]
