from __future__ import annotations
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from services import personal_finance
from services import personal_finance_intelligence as pfi

def money(v: float, symbol: str = "₦") -> str: return f"{symbol}{v:,.2f}"

def render() -> None:
    personal_finance.ensure_schema(); s=personal_finance.settings(); symbol=s["symbol"]; today=date.today()
    st.title("👤 Personal Finance"); st.caption("Professional personal finance workspace — cash management, 50/30/20 planning, statements, net worth and financial health.")
    c1,c2,c3=st.columns(3)
    with c1: start=st.date_input("From",today.replace(day=1),key="pf_start")
    with c2: end=st.date_input("To",today,key="pf_end")
    with c3: year=st.number_input("Fiscal Year",2000,2100,int(s["fiscal_year"]),key="pf_year")
    if start>end: st.error("The start date must be before the end date."); return
    start_s,end_s=start.isoformat(),end.isoformat(); m=personal_finance.dashboard_metrics(start_s,end_s)
    cols=st.columns(5)
    for col,(label,value) in zip(cols,[("Total Income",m["income"]),("Total Expenses",m["expenses"]),("Net Savings",m["net_savings"]),("Savings / Investment",m["savings"]),("Debt Payments",m["debt_payments"])]): col.metric(label,money(value,symbol))
    if m["savings_rate"] is not None: st.caption(f"Savings rate: {m['savings_rate']:.1f}% • {m['transaction_count']} transactions")
    tabs=st.tabs(["Dashboard","Income & Expenses","Budget","Statements","Net Worth","Financial Ratios","Health Intelligence","Settings"])
    with tabs[0]:
        st.subheader("50 / 30 / 20 Allocation"); df=personal_finance.transactions(start_s,end_s); income=m["income"]
        need=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Need"),"amount"].sum()) if not df.empty else 0.0; want=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Want"),"amount"].sum()) if not df.empty else 0.0
        a,b,c=st.columns(3); a.metric("Needs",f"{need/income*100:.1f}%" if income else "—",f"Target {s['needs_target']*100:.0f}%"); b.metric("Wants",f"{want/income*100:.1f}%" if income else "—",f"Target {s['wants_target']*100:.0f}%"); c.metric("Savings / Investment",f"{m['savings']/income*100:.1f}%" if income else "—",f"Target {s['savings_target']*100:.0f}%")
        monthly=personal_finance.monthly_statement(int(year)); chart=monthly.melt(id_vars="Month",value_vars=["Income","Expenses"],var_name="Metric",value_name="Amount"); st.plotly_chart(px.bar(chart,x="Month",y="Amount",color="Metric",barmode="group",title="Monthly Income vs Expenses"),use_container_width=True)
        spend=personal_finance.spending_by_category(start_s,end_s)
        if not spend.empty: st.plotly_chart(px.pie(spend,names="category",values="amount",title="Expense Mix"),use_container_width=True)
        st.subheader("Account Balances"); balances=pfi.account_balances(end_s)
        if not balances.empty: st.dataframe(balances[["name","account_type","opening_balance","movement","balance"]],use_container_width=True,hide_index=True)
    with tabs[1]:
        st.subheader("Record Transaction"); accts=personal_finance.accounts(); opts=dict(zip(accts.name,accts.id)); typ=st.selectbox("Transaction Type",personal_finance.PERSONAL_TYPES,key="pf_type"); cat_options=personal_finance.categories(typ).name.tolist() or ["Other"]
        with st.form("pf_tx",clear_on_submit=True):
            d,desc=st.columns(2); tx_date=d.date_input("Date",today); description=desc.text_input("Description"); a,c,acc=st.columns(3); amount=a.number_input(f"Amount ({symbol})",min_value=0.01,step=100.0); category=c.selectbox("Category",cat_options); account=acc.selectbox("Account",list(opts)); payment=st.text_input("Payment Method"); ref=st.text_input("Reference"); notes=st.text_area("Notes")
            if st.form_submit_button("Save Transaction",type="primary"):
                try: personal_finance.add_transaction(tx_date.isoformat(),description,amount,typ,category,int(opts[account]),payment,ref,notes); st.success("Transaction saved."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        tx=personal_finance.transactions(start_s,end_s)
        if tx.empty: st.info("No transactions for the selected period.")
        else: st.dataframe(tx[["id","transaction_date","transaction_type","category","classification","description","amount","account_name","payment_method","reference"]],use_container_width=True,hide_index=True)
    with tabs[2]:
        st.subheader("Monthly Budget"); month=st.date_input("Budget month",today.replace(day=1),key="pf_budget_month").strftime("%Y-%m"); cats=personal_finance.categories("Expense").name.tolist(); selected=st.selectbox("Category",cats); amount=st.number_input(f"Monthly Budget ({symbol})",min_value=0.0,step=1000.0,key="pf_budget_amount")
        if st.button("Save Budget",key="pf_save_budget"): personal_finance.set_budget(month,selected,amount); st.success("Budget saved.")
        bv=personal_finance.budget_variance(month)
        if bv.empty: st.info("No budget or expense data for this month.")
        else: st.dataframe(bv,use_container_width=True,hide_index=True); st.download_button("Export Budget CSV",bv.to_csv(index=False),"personal_budget.csv","text/csv")
    with tabs[3]:
        st.subheader("Income Statement"); stmt=personal_finance.monthly_statement(int(year)); st.dataframe(stmt,use_container_width=True,hide_index=True); st.download_button("Export Income Statement CSV",stmt.to_csv(index=False),"personal_income_statement.csv","text/csv")
        st.subheader("Cash Flow Statement"); cf=pfi.monthly_cash_flow(int(year)); st.dataframe(cf,use_container_width=True,hide_index=True); st.download_button("Export Cash Flow CSV",cf.to_csv(index=False),"personal_cash_flow.csv","text/csv"); st.caption("CALCULATION: cash flow after allocations includes recorded expenses, savings/investments and debt payments. Transfers are not treated as cash creation or destruction.")
    with tabs[4]:
        st.subheader("Net Worth"); nw=personal_finance.net_worth(end_s); x,y,z=st.columns(3); x.metric("Total Assets",money(nw["assets"],symbol)); y.metric("Total Liabilities",money(nw["liabilities"],symbol)); z.metric("Net Worth",money(nw["net_worth"],symbol)); st.caption(nw["status"])
        with st.form("pf_nw"):
            name=st.text_input("Asset / Liability name"); typ_nw=st.selectbox("Type",["Asset","Liability"]); val=st.number_input(f"Balance ({symbol})",min_value=0.0,step=1000.0)
            if st.form_submit_button("Save Balance"):
                try: personal_finance.set_net_worth_item(name,typ_nw,val); st.success("Balance saved."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        with personal_finance.connect() as conn: items=pd.read_sql_query("SELECT item_name,item_type,amount,as_of_date FROM personal_net_worth ORDER BY item_type,item_name",conn)
        if not items.empty: st.dataframe(items,use_container_width=True,hide_index=True)
    with tabs[5]:
        st.subheader("Financial Ratios & KPIs"); ratios=personal_finance.financial_ratios(start_s,end_s); target={"Savings Rate":s["savings_target"],"Expense-to-Income Ratio":1-s["savings_target"],"Needs Ratio":s["needs_target"],"Wants Ratio":s["wants_target"],"Savings/Investment Ratio":s["savings_target"],"Debt Repayment Ratio":s["debt_ratio_target"],"Emergency Fund Coverage (months)":s["emergency_months_target"]}; rows=[]
        for k,v in ratios.items():
            tv=target.get(k); status="Informational" if tv is None or v is None else ("On Target" if (v>=tv if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else v<=tv) else ("Below Target" if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else "Above Target")); rows.append({"Metric":k,"Actual":v,"Target":tv,"Status":status})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    with tabs[6]:
        st.subheader("Financial Health Intelligence"); health=pfi.financial_health(start_s,end_s); st.info(health["data_quality"])
        for item in health["findings"]:
            with st.container(border=True): st.markdown(f"**{item['Metric']}** — {item['Status']}"); st.write(item["Explanation"])
        st.caption(health["recommendation_note"])
    with tabs[7]:
        st.subheader("Settings & Assumptions"); currencies=["NGN","USD","GBP","EUR"]; currency=st.selectbox("Base Currency",currencies,index=currencies.index(s["currency"]) if s["currency"] in currencies else 0); symbol_map={"NGN":"₦","USD":"$","GBP":"£","EUR":"€"}; fy=st.number_input("Fiscal Year",2000,2100,int(s["fiscal_year"])); opening=st.number_input("Opening Cash Balance",min_value=0.0,value=float(s["opening_cash"])); n=st.number_input("Needs Target (%)",0.0,1.0,float(s["needs_target"])); w=st.number_input("Wants Target (%)",0.0,1.0,float(s["wants_target"])); sv=st.number_input("Savings/Investment Target (%)",0.0,1.0,float(s["savings_target"])); dr=st.number_input("Debt Ratio Target (%)",0.0,1.0,float(s["debt_ratio_target"])); em=st.number_input("Emergency Fund Target (months)",0.0,24.0,float(s["emergency_months_target"]))
        if st.button("Save Settings",key="pf_settings"):
            if abs((n+w+sv)-1)>1e-9: st.error("Needs, Wants and Savings/Investment targets must total 100%.")
            else: personal_finance.update_settings(currency=currency,symbol=symbol_map[currency],fiscal_year=fy,opening_cash=opening,needs_target=n,wants_target=w,savings_target=sv,debt_ratio_target=dr,emergency_months_target=em); st.success("Settings saved."); st.rerun()
        st.caption("The application is a financial-management tool. Ratio targets are configurable planning assumptions, not individualized financial advice.")
