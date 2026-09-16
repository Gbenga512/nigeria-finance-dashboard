from __future__ import annotations
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from services import personal_finance
from services import personal_finance_intelligence as pfi
from services import personal_finance_wealth as wealth


def money(v: float, symbol: str = "₦") -> str:
    return f"{symbol}{float(v):,.2f}"


def render() -> None:
    personal_finance.ensure_schema(); wealth.ensure_schema(); s=personal_finance.settings(); symbol=s["symbol"]; today=date.today()
    st.title("👤 Personal Finance")
    st.caption("Professional personal finance workspace — cash management, budgeting, statements, wealth tracking and explainable financial health.")
    c1,c2,c3=st.columns(3)
    with c1: start=st.date_input("From",today.replace(day=1),key="pf_start")
    with c2: end=st.date_input("To",today,key="pf_end")
    with c3: year=st.number_input("Fiscal Year",2000,2100,int(s["fiscal_year"]),key="pf_year")
    if start>end: st.error("The start date must be before the end date."); return
    start_s,end_s=start.isoformat(),end.isoformat(); m=personal_finance.dashboard_metrics(start_s,end_s); nw=wealth.integrated_net_worth(end_s)
    cols=st.columns(5)
    for col,(label,value) in zip(cols,[("Total Income",m["income"]),("Total Expenses",m["expenses"]),("Net Savings",m["net_savings"]),("Savings / Investment",m["savings"]),("Net Worth",nw["net_worth"])]): col.metric(label,money(value,symbol))
    if m["savings_rate"] is not None: st.caption(f"Net savings rate: {m['savings_rate']:.1f}% • {m['transaction_count']} transactions")

    tabs=st.tabs(["Dashboard","Income & Expenses","Transfers","Budget","Statements","Net Worth","Savings Goals","Debt","Investments","Financial Ratios","Health Intelligence","Settings"])
    with tabs[0]:
        st.subheader("50 / 30 / 20 Allocation"); df=personal_finance.transactions(start_s,end_s); income=m["income"]
        need=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Need"),"amount"].sum()) if not df.empty else 0.0; want=float(df.loc[(df.transaction_type=="Expense")&(df.classification=="Want"),"amount"].sum()) if not df.empty else 0.0
        a,b,c=st.columns(3); a.metric("Needs",f"{need/income*100:.1f}%" if income else "—",f"Target {s['needs_target']*100:.0f}%"); b.metric("Wants",f"{want/income*100:.1f}%" if income else "—",f"Target {s['wants_target']*100:.0f}%"); c.metric("Savings / Investment",f"{m['savings']/income*100:.1f}%" if income else "—",f"Target {s['savings_target']*100:.0f}%")
        monthly=personal_finance.monthly_statement(int(year)); chart=monthly.melt(id_vars="Month",value_vars=["Income","Expenses"],var_name="Metric",value_name="Amount"); st.plotly_chart(px.bar(chart,x="Month",y="Amount",color="Metric",barmode="group",title="Monthly Income vs Expenses"),use_container_width=True)
        spend=personal_finance.spending_by_category(start_s,end_s)
        if not spend.empty: st.plotly_chart(px.pie(spend,names="category",values="amount",title="Expense Mix"),use_container_width=True)
        st.subheader("Account Balances"); balances=pfi.account_balances(end_s)
        if not balances.empty: st.dataframe(balances[["name","account_type","opening_balance","movement","balance"]],use_container_width=True,hide_index=True)
        st.caption("FACT/CALCULATION: balances include recorded account movements and explicit two-sided transfers. Legacy single-sided Transfer/Savings rows are not treated as cash movements.")

    with tabs[1]:
        st.subheader("Record Transaction"); accts=personal_finance.accounts(); opts=dict(zip(accts.name,accts.id)); typ=st.selectbox("Transaction Type",[x for x in personal_finance.PERSONAL_TYPES if x not in ["Transfer"]],key="pf_type"); cat_options=personal_finance.categories(typ).name.tolist() or ["Other"]
        with st.form("pf_tx",clear_on_submit=True):
            d,desc=st.columns(2); tx_date=d.date_input("Date",today); description=desc.text_input("Description"); a,c,acc=st.columns(3); amount=a.number_input(f"Amount ({symbol})",min_value=0.01,step=100.0); category=c.selectbox("Category",cat_options); account=acc.selectbox("Account",list(opts)); payment=st.text_input("Payment Method"); ref=st.text_input("Reference"); notes=st.text_area("Notes")
            if st.form_submit_button("Save Transaction",type="primary"):
                try: personal_finance.add_transaction(tx_date.isoformat(),description,amount,typ,category,int(opts[account]),payment,ref,notes); st.success("Transaction saved."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        tx=personal_finance.transactions(start_s,end_s)
        if tx.empty: st.info("No transactions for the selected period.")
        else: st.dataframe(tx[["id","transaction_date","transaction_type","category","classification","description","amount","account_name","payment_method","reference"]],use_container_width=True,hide_index=True)

    with tabs[2]:
        st.subheader("Double-Sided Account Transfers")
        st.caption("Transfers move value between accounts without changing total liquid wealth. Use this instead of a single-sided Savings or Transfer transaction.")
        accts=personal_finance.accounts(); opts=dict(zip(accts.name,accts.id)); names=list(opts)
        if len(names)>=2:
            with st.form("pf_transfer",clear_on_submit=True):
                d,desc=st.columns(2); td=d.date_input("Date",today); description=desc.text_input("Description",value="Account transfer")
                f,t,a=st.columns(3); frm=f.selectbox("From account",names,key="pf_from"); to=t.selectbox("To account",names,index=1,key="pf_to"); amount=a.number_input(f"Amount ({symbol})",min_value=0.01,step=1000.0,key="pf_transfer_amount")
                ref=st.text_input("Reference",key="pf_transfer_ref"); notes=st.text_input("Notes",key="pf_transfer_notes")
                if st.form_submit_button("Post Transfer",type="primary"):
                    try: wealth.add_transfer(td.isoformat(),description,amount,int(opts[frm]),int(opts[to]),ref,notes); st.success("Transfer recorded."); st.rerun()
                    except ValueError as exc: st.error(str(exc))
        else: st.info("Create at least two accounts to use transfers.")
        tr=wealth.transfers(start_s,end_s)
        if not tr.empty: st.dataframe(tr[["id","transaction_date","description","amount","from_account","to_account","reference"]],use_container_width=True,hide_index=True)

    with tabs[3]:
        st.subheader("Monthly Budget"); month=st.date_input("Budget month",today.replace(day=1),key="pf_budget_month").strftime("%Y-%m"); cats=personal_finance.categories("Expense").name.tolist(); selected=st.selectbox("Category",cats); amount=st.number_input(f"Monthly Budget ({symbol})",min_value=0.0,step=1000.0,key="pf_budget_amount")
        if st.button("Save Budget",key="pf_save_budget"): personal_finance.set_budget(month,selected,amount); st.success("Budget saved.")
        bv=personal_finance.budget_variance(month)
        if bv.empty: st.info("No budget or expense data for this month.")
        else: st.dataframe(bv,use_container_width=True,hide_index=True); st.download_button("Export Budget CSV",bv.to_csv(index=False),"personal_budget.csv","text/csv")

    with tabs[4]:
        st.subheader("Income Statement"); stmt=personal_finance.monthly_statement(int(year)); st.dataframe(stmt,use_container_width=True,hide_index=True); st.download_button("Export Income Statement CSV",stmt.to_csv(index=False),"personal_income_statement.csv","text/csv")
        st.subheader("Cash Flow Statement"); cf=pfi.monthly_cash_flow(int(year)); st.dataframe(cf,use_container_width=True,hide_index=True); st.download_button("Export Cash Flow CSV",cf.to_csv(index=False),"personal_cash_flow.csv","text/csv"); st.caption("CALCULATION: cash flow after allocations includes recorded expenses, savings/investments and debt payments. Explicit transfers are excluded because they only move cash between accounts.")

    with tabs[5]:
        st.subheader("Integrated Net Worth"); nw=wealth.integrated_net_worth(end_s); x,y,z=st.columns(3); x.metric("Total Assets",money(nw["assets"],symbol)); y.metric("Total Liabilities",money(nw["liabilities"],symbol)); z.metric("Net Worth",money(nw["net_worth"],symbol))
        a,b,c=st.columns(3); a.metric("Liquid Cash",money(nw["liquid_cash"],symbol)); b.metric("Investments",money(nw["investments"],symbol)); c.metric("Debt Register",money(nw["debts"],symbol)); st.caption(nw["status"])
        with st.form("pf_nw"):
            name=st.text_input("Other asset / liability name"); typ_nw=st.selectbox("Type",["Asset","Liability"]); val=st.number_input(f"Balance ({symbol})",min_value=0.0,step=1000.0); asof=st.date_input("As-of date",today,key="pf_nw_date")
            if st.form_submit_button("Save Other Balance"):
                try: personal_finance.set_net_worth_item(name,typ_nw,val,asof.isoformat()); st.success("Balance saved."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        with personal_finance.connect() as conn: items=pd.read_sql_query("SELECT item_name,item_type,amount,as_of_date FROM personal_net_worth ORDER BY item_type,item_name",conn)
        if not items.empty: st.dataframe(items,use_container_width=True,hide_index=True)

    with tabs[6]:
        st.subheader("Savings Goals")
        accts=personal_finance.accounts(); opts=dict(zip(accts.name,accts.id)); names=list(opts)
        with st.form("pf_goal",clear_on_submit=True):
            name=st.text_input("Goal name"); target=st.number_input(f"Target amount ({symbol})",min_value=1.0,step=5000.0); td=st.date_input("Target date",today.replace(month=12,day=31)); linked=st.selectbox("Linked savings/cash account",["None"]+names)
            if st.form_submit_button("Create Goal"):
                try: wealth.add_savings_goal(name,target,td.isoformat(),None if linked=="None" else int(opts[linked])); st.success("Savings goal created."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        goals=wealth.savings_goals(end_s)
        if goals.empty: st.info("No savings goals yet.")
        else:
            st.dataframe(goals[["name","target_amount","current_amount","progress_pct","target_date","linked_account","status"]],use_container_width=True,hide_index=True)
            for _,g in goals.iterrows(): st.progress(int(min(100,max(0,g["progress_pct"]))),text=f"{g['name']}: {g['progress_pct']:.1f}%")

    with tabs[7]:
        st.subheader("Debt Register")
        with st.form("pf_debt",clear_on_submit=True):
            name=st.text_input("Debt name"); principal=st.number_input(f"Original principal ({symbol})",min_value=0.0,step=10000.0); balance=st.number_input(f"Current balance ({symbol})",min_value=0.0,step=10000.0); rate=st.number_input("Annual interest rate (%)",min_value=0.0,step=0.5); minimum=st.number_input(f"Minimum payment ({symbol})",min_value=0.0,step=1000.0); due=st.number_input("Due day",min_value=1,max_value=31,value=28); asof=st.date_input("As-of date",today,key="pf_debt_date"); notes=st.text_input("Notes",key="pf_debt_notes")
            if st.form_submit_button("Add Debt"):
                try: wealth.add_debt(name,principal,balance,rate,minimum,int(due),asof.isoformat(),notes); st.success("Debt recorded."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        debts=wealth.debts(end_s)
        if debts.empty: st.info("No debts recorded.")
        else: st.dataframe(debts[["name","principal","current_balance","interest_rate","minimum_payment","due_day","status","as_of_date"]],use_container_width=True,hide_index=True)
        st.caption("The debt register is a balance snapshot. Debt-payment transactions are tracked separately and are not automatically assumed to change this snapshot.")

    with tabs[8]:
        st.subheader("Investment Register")
        with st.form("pf_inv",clear_on_submit=True):
            name=st.text_input("Investment name"); asset_class=st.selectbox("Asset class",["Equity","Fixed Income","Money Market","Fund","Real Estate","Other"]); cost=st.number_input(f"Cost basis ({symbol})",min_value=0.0,step=10000.0); value=st.number_input(f"Current value ({symbol})",min_value=0.0,step=10000.0); units=st.number_input("Units (optional)",min_value=0.0,step=1.0); asof=st.date_input("Valuation date",today,key="pf_inv_date"); notes=st.text_input("Notes",key="pf_inv_notes")
            if st.form_submit_button("Add Investment"):
                try: wealth.add_investment(name,asset_class,cost,value,units,asof.isoformat(),notes); st.success("Investment recorded."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        inv=wealth.investments(end_s)
        if inv.empty: st.info("No investments recorded.")
        else:
            inv=inv.copy(); inv["gain_loss"]=inv["current_value"]-inv["cost_basis"]; inv["return_pct"]=inv.apply(lambda r:r["gain_loss"]/r["cost_basis"]*100 if r["cost_basis"] else None,axis=1); st.dataframe(inv[["name","asset_class","cost_basis","current_value","gain_loss","return_pct","units","as_of_date"]],use_container_width=True,hide_index=True)

    with tabs[9]:
        st.subheader("Financial Ratios & KPIs"); ratios=personal_finance.financial_ratios(start_s,end_s); target={"Savings Rate":s["savings_target"],"Expense-to-Income Ratio":1-s["savings_target"],"Needs Ratio":s["needs_target"],"Wants Ratio":s["wants_target"],"Savings/Investment Ratio":s["savings_target"],"Debt Repayment Ratio":s["debt_ratio_target"],"Emergency Fund Coverage (months)":s["emergency_months_target"]}; coverage=wealth.emergency_coverage(start_s,end_s); ratios["Emergency Fund Coverage (months)"]=coverage["essential_months"]; ratios["Net Worth"]=nw["net_worth"]; rows=[]
        for k,v in ratios.items():
            tv=target.get(k); status="Informational" if tv is None or v is None else ("On Target" if (v>=tv if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else v<=tv) else ("Below Target" if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else "Above Target")); rows.append({"Metric":k,"Actual":v,"Target":tv,"Status":status})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.caption("Emergency coverage is calculated from liquid cash/savings divided by average monthly essential (Need-classified) expenses in the selected period.")

    with tabs[10]:
        st.subheader("Financial Health Intelligence"); health=pfi.financial_health(start_s,end_s); st.info(health["data_quality"])
        for item in health["findings"]:
            with st.container(border=True): st.markdown(f"**{item['Metric']}** — {item['Status']}"); st.write(item["Explanation"])
        st.caption(health["recommendation_note"])

    with tabs[11]:
        st.subheader("Settings & Assumptions"); currencies=["NGN","USD","GBP","EUR"]; currency=st.selectbox("Base Currency",currencies,index=currencies.index(s["currency"]) if s["currency"] in currencies else 0); symbol_map={"NGN":"₦","USD":"$","GBP":"£","EUR":"€"}; fy=st.number_input("Fiscal Year",2000,2100,int(s["fiscal_year"])); opening=st.number_input("Opening Cash Balance",min_value=0.0,value=float(s["opening_cash"])); n=st.number_input("Needs Target (%)",0.0,1.0,float(s["needs_target"])); w=st.number_input("Wants Target (%)",0.0,1.0,float(s["wants_target"])); sv=st.number_input("Savings/Investment Target (%)",0.0,1.0,float(s["savings_target"])); dr=st.number_input("Debt Ratio Target (%)",0.0,1.0,float(s["debt_ratio_target"])); em=st.number_input("Emergency Fund Target (months)",0.0,24.0,float(s["emergency_months_target"]))
        if st.button("Save Settings",key="pf_settings"):
            if abs((n+w+sv)-1)>1e-9: st.error("Needs, Wants and Savings/Investment targets must total 100%.")
            else: personal_finance.update_settings(currency=currency,symbol=symbol_map[currency],fiscal_year=fy,opening_cash=opening,needs_target=n,wants_target=w,savings_target=sv,debt_ratio_target=dr,emergency_months_target=em); st.success("Settings saved."); st.rerun()
        st.caption("The application is a financial-management tool. Targets are configurable planning assumptions, not individualized financial advice.")
