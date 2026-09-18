"""Forward personal cash-flow forecast using recorded history and recurring rules."""
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
from services import personal_finance as pf
from services import personal_recurring as recurring
from services import personal_finance_wealth as wealth

def _period_months(start: date, months: int):
    out=[]; y,m=start.year,start.month
    for _ in range(months):
        out.append(date(y,m,1))
        m+=1
        if m==13: y+=1; m=1
    return out

def forecast(start: str, months: int = 6) -> pd.DataFrame:
    start_d=date.fromisoformat(start)
    rules=recurring.rules()
    tx=pf.transactions()
    opening=float(wealth.liquid_cash(start_d.isoformat()))
    rows=[]
    for month in _period_months(start_d,months):
        end=(pd.Timestamp(month)+pd.offsets.MonthEnd(1)).date()
        hist=tx[(pd.to_datetime(tx["transaction_date"]).dt.month==month.month)&(pd.to_datetime(tx["transaction_date"]).dt.year<month.year)] if not tx.empty else tx
        income=float(hist.loc[hist.transaction_type=="Income","amount"].mean()) if not hist.empty else 0.0
        expense=float(hist.loc[hist.transaction_type=="Expense","amount"].mean()) if not hist.empty else 0.0
        savings=float(hist.loc[hist.transaction_type.isin(["Savings","Investment"]),"amount"].mean()) if not hist.empty else 0.0
        debt=float(hist.loc[hist.transaction_type=="Debt Payment","amount"].mean()) if not hist.empty else 0.0
        rin=rout=0.0
        for r in rules.itertuples():
            due=date.fromisoformat(str(r.next_due_date))
            while due < month: due=recurring._next_due(due,r.frequency)
            while due<=end:
                if due>=month:
                    if r.transaction_type=="Income": rin+=r.amount
                    elif r.transaction_type in ("Expense","Savings","Debt Payment","Investment"): rout+=r.amount
                due=recurring._next_due(due,r.frequency)
        forecast_income=income+rin
        forecast_outflow=expense+savings+debt+rout
        net=forecast_income-forecast_outflow
        opening=opening if rows else opening
        closing=opening+net
        rows.append({"Month":month.strftime("%Y-%m"),"Opening Cash":opening,"Forecast Income":forecast_income,
                     "Forecast Outflows":forecast_outflow,"Forecast Net Cash Flow":net,"Closing Cash":closing,
                     "Recurring Impact":rin-rout,"Status":"ESTIMATE"})
        opening=closing
    return pd.DataFrame(rows)
