"""IFRS-oriented primary financial statement presentation layer."""
from __future__ import annotations
import pandas as pd
from services.sme_accounting import trial_balance, profit_and_loss, balance_sheet, cash_flow

PRIMARY_STATEMENTS=("Statement of Profit or Loss","Statement of Financial Position","Statement of Cash Flows","Statement of Changes in Equity")

def statement_pack(business_id:int,start=None,end=None)->dict:
    tb=trial_balance(business_id,start,end); pnl=profit_and_loss(business_id,start,end); bs=balance_sheet(business_id,end); cf=cash_flow(business_id,start,end)
    cogs=float(tb.loc[(tb["Type"]=="Expense")&(tb["Account"]=="Cost of Goods Sold"),"Debits"].sum())
    eq=tb[tb["Type"]=="Equity"]; opening=float(-eq["Balance"].sum()) if not eq.empty else 0.0
    return {"profit_and_loss":{**pnl,"Gross Profit":pnl["Revenue"]-cogs},"financial_position":bs,"cash_flows":cf,"changes_in_equity":pd.DataFrame([{"Component":"Opening / recorded equity","Amount":opening},{"Component":"Profit / (loss) for period","Amount":pnl["Net Income"]},{"Component":"Closing equity","Amount":opening+pnl["Net Income"]}]),"trial_balance":tb,"status":"FACT/CALCULATION: derived from posted journals"}

def statement_notes()->list[str]:
    return ["Amounts are derived from posted double-entry records.","Presentation is IFRS-oriented; entity-specific accounting policies and disclosures must be configured.","Material judgements, estimates, tax, impairment, leases and financial instruments require entity-specific review.","This report is not an audit opinion or tax advice."]
