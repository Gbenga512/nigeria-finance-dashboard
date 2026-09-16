"""Personal finance intelligence helpers."""
from __future__ import annotations
import pandas as pd
from services import personal_finance as pf

def account_balances(as_of=None):
    as_of = as_of or pd.Timestamp.today().strftime('%Y-%m-%d')
    accounts = pf.accounts().copy()
    tx = pf.transactions(end=as_of)
    if tx.empty:
        accounts['movement'] = 0.0
    else:
        tx = tx.copy()
        tx['movement'] = pd.to_numeric(tx['amount'], errors='coerce').fillna(0.0)
        tx.loc[tx.transaction_type.isin(['Expense','Savings','Debt Payment','Investment']), 'movement'] *= -1
        tx.loc[tx.transaction_type == 'Transfer', 'movement'] = 0.0
        mv = tx.groupby('account_id', as_index=False)['movement'].sum()
        accounts = accounts.merge(mv, left_on='id', right_on='account_id', how='left').drop(columns=['account_id'], errors='ignore')
        accounts['movement'] = accounts['movement'].fillna(0.0)
    accounts['opening_balance'] = pd.to_numeric(accounts['opening_balance'], errors='coerce').fillna(0.0)
    accounts['balance'] = accounts['opening_balance'] + accounts['movement']
    return accounts

def liquid_cash(as_of=None):
    b = account_balances(as_of)
    return float(b.loc[b.account_type.isin(['Cash','Savings']), 'balance'].sum()) if not b.empty else 0.0

def financial_health(start, end):
    s = pf.settings(); r = pf.financial_ratios(start, end); d = pf.dashboard_metrics(start, end); findings=[]
    def add(metric,status,explanation): findings.append({'Metric':metric,'Status':status,'Explanation':explanation})
    sr=r.get('Savings Rate')
    if sr is None: add('Savings Rate','FACT: insufficient income data','No recorded income exists for the selected period; the ratio cannot be calculated.')
    elif sr < s['savings_target']: add('Savings Rate','CALCULATION: below target','Recorded savings relative to income is below the configured planning target.')
    else: add('Savings Rate','CALCULATION: at/above target','Recorded savings relative to income meets or exceeds the configured planning target.')
    if r.get('Needs Ratio') is not None and r['Needs Ratio'] > s['needs_target']: add('Needs Allocation','CALCULATION: above target','Need-classified expenses exceed the configured needs allocation target.')
    if r.get('Wants Ratio') is not None and r['Wants Ratio'] > s['wants_target']: add('Wants Allocation','CALCULATION: above target','Want-classified expenses exceed the configured wants allocation target.')
    coverage=r.get('Emergency Fund Coverage (months)')
    if coverage is not None and coverage < s['emergency_months_target']: add('Emergency Fund','CALCULATION: below target','Liquid cash and savings cover fewer months of average recorded expenses than the configured target.')
    if d['net_cash_flow'] < 0: add('Cash Flow','FACT: negative after allocations','Recorded expenses, savings/investments and debt payments exceed recorded income in the selected period.')
    if not findings: add('Financial Health','CALCULATION: no configured threshold breached','No configured planning threshold was breached by the available recorded data.')
    return {'findings':findings,'data_quality':'FACT: based only on recorded personal transactions and configured balances.','recommendation_note':'RECOMMENDATION: review flagged ratios and cash commitments before changing allocations.'}

def monthly_cash_flow(fiscal_year):
    stmt=pf.monthly_statement(fiscal_year)
    out=stmt[['Month','Income','Expenses','Savings/Investment','Debt Payments','Cash Flow After Allocations']].copy()
    opening=float(pf.settings()['opening_cash']); openings=[]; closings=[]
    for _,row in out.iterrows():
        openings.append(opening); opening += float(row['Cash Flow After Allocations']); closings.append(opening)
    out['Opening Balance']=openings; out['Closing Balance']=closings
    return out[['Month','Opening Balance','Income','Expenses','Savings/Investment','Debt Payments','Cash Flow After Allocations','Closing Balance']]
