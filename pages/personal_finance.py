from __future__ import annotations
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from services import personal_finance
from services import personal_finance_controls as controls
from services import personal_finance_intelligence as pfi
from services import personal_finance_wealth as wealth
from services import personal_net_worth_history as nw_history
from services import personal_debt_payments as debt_payments
from services import personal_investment_history as investment_history
from analytics import personal_allocation
from analytics import personal_health
from analytics import personal_data_quality
from analytics import personal_report
from analytics import personal_cashflow_forecast
from analytics import personal_scenarios


def money(v: float, symbol: str = "₦") -> str:
    return f"{symbol}{float(v):,.2f}"


def render() -> None:
    personal_finance.ensure_schema(); controls.ensure_schema(); wealth.ensure_schema(); s=personal_finance.settings(); symbol=s["symbol"]; today=date.today()
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

    tabs=st.tabs(["Dashboard","Income & Expenses","Transfers","Budget","Statements","Net Worth","Net Worth History","Savings Goals","Debt","Investments","Financial Ratios","Health Intelligence","Data Quality","Reports","Cash-Flow Forecast","Scenarios","Settings"])
    with tabs[0]:
        st.subheader("Needs / Wants / Savings-Investment Allocation")
        allocation = personal_allocation.allocation_report(start_s, end_s)
        if allocation.empty:
            st.info("No allocation data for the selected period.")
        else:
            a, b, c = st.columns(3)
            for col, (_, row) in zip((a, b, c), allocation.iterrows()):
                pct = row["Actual % of Income"]
                target_pct = row["Target %"]
                col.metric(
                    row["Bucket"],
                    f"{pct:.1f}%" if pd.notna(pct) else "—",
                    f"Target {target_pct:.0f}%",
                )
            st.dataframe(
                allocation[
                    ["Bucket", "Actual", "Actual % of Income", "Target %", "Target Amount", "Budgeted", "Budget Variance", "Target Variance"]
                ],
                use_container_width=True,
                hide_index=True,
            )
            chart = allocation[["Bucket", "Actual % of Income", "Target %"]].melt(
                id_vars="Bucket", var_name="Metric", value_name="Percent"
            )
            st.plotly_chart(
                px.bar(
                    chart,
                    x="Bucket",
                    y="Percent",
                    color="Metric",
                    barmode="group",
                    title="Actual vs Target Allocation",
                ),
                use_container_width=True,
            )
            st.caption(
                "FACT/CALCULATION: Needs and Wants include recorded expenses plus debt payments classified as Needs; "
                "Savings/Investment includes recorded savings and investment allocations. Budgeted values aggregate category budgets."
            )
        df=personal_finance.transactions(start_s,end_s); income=m["income"]
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
                try:
                    tx_id=personal_finance.add_transaction(tx_date.isoformat(),description,amount,typ,category,int(opts[account]),payment,ref,notes)
                    controls.record_create(tx_id)
                    st.success("Transaction saved and audit record created."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        tx=personal_finance.transactions(start_s,end_s)
        if tx.empty:
            st.info("No transactions for the selected period.")
        else:
            st.dataframe(tx[["id","transaction_date","transaction_type","category","classification","description","amount","account_name","payment_method","reference"]],use_container_width=True,hide_index=True)
            st.divider()
            st.subheader("Transaction Controls")
            tx_ids=tx["id"].astype(int).tolist()
            selected_id=st.selectbox("Select transaction",tx_ids,key="pf_control_id")
            selected=tx.loc[tx["id"]==selected_id].iloc[0]
            selected_type=str(selected["transaction_type"])
            selected_categories=personal_finance.categories(selected_type).name.tolist() or [str(selected["category"])]
            with st.form("pf_edit_tx"):
                d1,d2=st.columns(2); edit_date=d1.date_input("Date",pd.to_datetime(selected["transaction_date"]).date(),key=f"pf_edit_date_{selected_id}"); edit_desc=d2.text_input("Description",str(selected["description"]),key=f"pf_edit_desc_{selected_id}")
                a1,a2,a3=st.columns(3); edit_amount=a1.number_input(f"Amount ({symbol})",min_value=0.01,value=float(selected["amount"]),step=100.0,key=f"pf_edit_amount_{selected_id}"); edit_category=a2.selectbox("Category",selected_categories,index=selected_categories.index(str(selected["category"])) if str(selected["category"]) in selected_categories else 0,key=f"pf_edit_cat_{selected_id}"); account_names=list(opts); current_account=str(selected["account_name"]); account_index=account_names.index(current_account) if current_account in account_names else 0; edit_account=a3.selectbox("Account",account_names,index=account_index,key=f"pf_edit_account_{selected_id}")
                edit_payment=st.text_input("Payment Method",str(selected["payment_method"] or ""),key=f"pf_edit_payment_{selected_id}"); edit_ref=st.text_input("Reference",str(selected["reference"] or ""),key=f"pf_edit_ref_{selected_id}"); edit_notes=st.text_area("Notes",str(selected["notes"] or ""),key=f"pf_edit_notes_{selected_id}")
                if st.form_submit_button("Save Changes",type="primary"):
                    try:
                        controls.update_transaction(selected_id,transaction_date=edit_date.isoformat(),description=edit_desc,amount=edit_amount,transaction_type=selected_type,category=edit_category,account_id=int(opts[edit_account]),payment_method=edit_payment,reference=edit_ref,notes=edit_notes)
                        st.success("Transaction amended and audit logged."); st.rerun()
                    except ValueError as exc: st.error(str(exc))
            d1,d2,d3=st.columns(3)
            with d1:
                if st.button("Delete Selected",key=f"pf_delete_{selected_id}",type="secondary"):
                    try:
                        controls.delete_transaction(selected_id,"User requested deletion")
                        st.success("Transaction deleted and audit logged."); st.rerun()
                    except ValueError as exc: st.error(str(exc))
            with d2:
                if st.button("Show Audit Trail",key=f"pf_audit_{selected_id}"):
                    st.session_state["pf_show_audit"] = selected_id
            if st.session_state.get("pf_show_audit")==selected_id:
                audit=pd.DataFrame(controls.audit_log(selected_id))
                if audit.empty: st.info("No audit records yet.")
                else: st.dataframe(audit[["id","action","reason","created_at","before_json","after_json"]],use_container_width=True,hide_index=True)

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
        st.subheader("Historical Net Worth")
        st.caption("Record period-end snapshots to build a reliable personal wealth history. Historical values are never invented.")
        nw_history.ensure_snapshot_schema()
        if st.button("Record Current Net Worth Snapshot", key="pf_record_nw_snapshot", type="primary"):
            try:
                nw_history.record_snapshot(end_s, "Recorded from Personal Finance workspace")
                st.success(f"Net worth snapshot recorded for {end_s}.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        snapshots = nw_history.snapshots()
        if snapshots.empty:
            st.info("No historical snapshots yet. Record a snapshot at each month-end or valuation date.")
        else:
            latest = snapshots.iloc[-1]
            first = snapshots.iloc[0]
            x, y, z = st.columns(3)
            x.metric("Snapshots", int(len(snapshots)))
            y.metric("Latest Net Worth", money(latest["net_worth"], symbol))
            z.metric("Change Since First", money(float(latest["net_worth"]) - float(first["net_worth"]), symbol))
            chart = snapshots[["snapshot_date", "assets", "liabilities", "net_worth"]].copy()
            chart["snapshot_date"] = pd.to_datetime(chart["snapshot_date"])
            chart = chart.melt("snapshot_date", var_name="Metric", value_name="Amount")
            st.plotly_chart(px.line(chart, x="snapshot_date", y="Amount", color="Metric", title="Net Worth Trend"), use_container_width=True)
            st.dataframe(
                snapshots[["snapshot_date", "assets", "liabilities", "net_worth", "liquid_cash", "investments", "debt_register", "notes"]],
                use_container_width=True,
                hide_index=True,
            )
            st.download_button("Export Net Worth History CSV", snapshots.to_csv(index=False), "personal_net_worth_history.csv", "text/csv")
        st.caption("FACT/CALCULATION: each point is a recorded snapshot derived from the personal accounts, investment register, debt register and recorded assets/liabilities available as of that date.")

    with tabs[7]:
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

    with tabs[8]:
        st.subheader("Debt Register")
        with st.form("pf_debt",clear_on_submit=True):
            name=st.text_input("Debt name"); principal=st.number_input(f"Original principal ({symbol})",min_value=0.0,step=10000.0); balance=st.number_input(f"Current balance ({symbol})",min_value=0.0,step=10000.0); rate=st.number_input("Annual interest rate (%)",min_value=0.0,step=0.5); minimum=st.number_input(f"Minimum payment ({symbol})",min_value=0.0,step=1000.0); due=st.number_input("Due day",min_value=1,max_value=31,value=28); asof=st.date_input("As-of date",today,key="pf_debt_date"); notes=st.text_input("Notes",key="pf_debt_notes")
            if st.form_submit_button("Add Debt"):
                try: wealth.add_debt(name,principal,balance,rate,minimum,int(due),asof.isoformat(),notes); st.success("Debt recorded."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        debts=wealth.debts(end_s)
        if debts.empty: st.info("No debts recorded.")
        else: st.dataframe(debts[["name","principal","current_balance","interest_rate","minimum_payment","due_day","status","as_of_date"]],use_container_width=True,hide_index=True)
        st.divider()
        st.subheader("Link Debt Payments")
        st.caption("Link a recorded Debt Payment transaction to a specific debt and split it between principal and interest. The payment amount must reconcile exactly.")
        debt_payments.ensure_schema()
        tx_payments=personal_finance.transactions(end=end_s)
        tx_payments=tx_payments[tx_payments["transaction_type"]=="Debt Payment"] if not tx_payments.empty else tx_payments
        debt_options=wealth.debts(end_s)
        if tx_payments.empty: st.info("Record a Debt Payment transaction first.")
        elif debt_options.empty: st.info("Create a debt in the register before linking payments.")
        else:
            payment_ids=tx_payments["id"].astype(int).tolist()
            labels={int(r["id"]):f"#{int(r['id'])} • {r['transaction_date']} • {r['description']} • {money(r['amount'],symbol)}" for _,r in tx_payments.iterrows()}
            with st.form("pf_link_debt_payment"):
                tx_id=st.selectbox("Debt payment transaction",payment_ids,format_func=lambda x:labels[x])
                debt_map={f"{r['name']} (ID {int(r['id'])})":int(r["id"]) for _,r in debt_options.iterrows()}
                debt_label=st.selectbox("Debt",list(debt_map))
                selected_payment=float(tx_payments.loc[tx_payments["id"]==tx_id,"amount"].iloc[0])
                p,i=st.columns(2)
                principal_alloc=p.number_input(f"Principal allocation ({symbol})",min_value=0.0,max_value=selected_payment,value=selected_payment,step=100.0)
                interest_alloc=i.number_input(f"Interest allocation ({symbol})",min_value=0.0,max_value=selected_payment,value=0.0,step=100.0)
                st.caption(f"Payment total: {money(selected_payment,symbol)} • Principal + interest must equal this amount.")
                if st.form_submit_button("Link Payment",type="primary"):
                    try: debt_payments.link_payment(tx_id,debt_map[debt_label],principal_alloc,interest_alloc); st.success("Debt payment linked."); st.rerun()
                    except ValueError as exc: st.error(str(exc))
        summary=debt_payments.debt_summary(end_s)
        if not summary.empty:
            st.subheader("Debt Position After Linked Payments")
            st.dataframe(summary[["name","current_balance","linked_principal","linked_interest","calculated_balance"]],use_container_width=True,hide_index=True)
        register=debt_payments.payment_register()
        if not register.empty:
            st.subheader("Linked Payment History")
            st.dataframe(register[["transaction_date","debt_name","payment_amount","principal_amount","interest_amount","description"]],use_container_width=True,hide_index=True)
        st.caption("FACT/CALCULATION: calculated balance = recorded debt balance at its as-of date less linked principal payments dated after that snapshot. Interest is tracked separately and does not reduce principal.")

    with tabs[9]:
        st.subheader("Investment Register")
        with st.form("pf_inv",clear_on_submit=True):
            name=st.text_input("Investment name"); asset_class=st.selectbox("Asset class",["Equity","Fixed Income","Money Market","Fund","Real Estate","Other"]); cost=st.number_input(f"Cost basis ({symbol})",min_value=0.0,step=10000.0); value=st.number_input(f"Current value ({symbol})",min_value=0.0,step=10000.0); units=st.number_input("Units (optional)",min_value=0.0,step=1.0); asof=st.date_input("Valuation date",today,key="pf_inv_date"); notes=st.text_input("Notes",key="pf_inv_notes")
            if st.form_submit_button("Add Investment"):
                try: wealth.add_investment(name,asset_class,cost,value,units,asof.isoformat(),notes); st.success("Investment recorded."); st.rerun()
                except ValueError as exc: st.error(str(exc))
        inv=wealth.investments(end_s)
        if inv.empty:
            st.info("No investments recorded.")
        else:
            inv=inv.copy()
            inv["gain_loss"]=inv["current_value"]-inv["cost_basis"]
            inv["return_pct"]=inv.apply(lambda r:r["gain_loss"]/r["cost_basis"]*100 if r["cost_basis"] else None,axis=1)
            st.dataframe(inv[["name","asset_class","cost_basis","current_value","gain_loss","return_pct","units","as_of_date"]],use_container_width=True,hide_index=True)
            st.divider()
            st.subheader("Investment Valuation History")
            st.caption("Record valuation points to preserve an auditable performance history. Current value remains the latest recorded valuation.")
            investment_history.ensure_schema()
            inv_map={f"{r['name']} (ID {int(r['id'])})":int(r['id']) for _,r in inv.iterrows()}
            with st.form("pf_investment_valuation"):
                selected_inv=st.selectbox("Investment",list(inv_map))
                valuation_date=st.date_input("Valuation date",today,key="pf_valuation_date")
                current_value=st.number_input(f"Current value ({symbol})",min_value=0.0,step=1000.0)
                units_value=st.number_input("Units",min_value=0.0,step=1.0)
                note=st.text_input("Valuation note")
                if st.form_submit_button("Record Valuation",type="primary"):
                    try:
                        investment_history.record_valuation(inv_map[selected_inv],valuation_date.isoformat(),current_value,units_value,note)
                        st.success("Investment valuation recorded.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            perf=investment_history.performance_summary(end_s)
            if not perf.empty:
                st.subheader("Performance Summary")
                st.dataframe(perf[["name","asset_class","cost_basis","current_value","gain_loss","return_pct","first_valuation","latest_valuation","observations"]],use_container_width=True,hide_index=True)
            portfolio=investment_history.portfolio_history(end_s)
            if not portfolio.empty:
                st.plotly_chart(px.line(portfolio,x="valuation_date",y="portfolio_value",title="Portfolio Valuation Trend"),use_container_width=True)
            vh=investment_history.valuation_history(end=end_s)
            if not vh.empty:
                st.dataframe(vh[["valuation_date","name","asset_class","current_value","units","note"]],use_container_width=True,hide_index=True)
                st.download_button("Export Investment Valuation History CSV",vh.to_csv(index=False),"personal_investment_valuation_history.csv","text/csv")
            st.caption("FACT/CALCULATION: gain/loss is current value less recorded cost basis; return is gain/loss divided by cost basis. Historical valuation points are user-recorded observations, not market-price estimates.")

    with tabs[10]:
        st.subheader("Financial Ratios & KPIs"); ratios=personal_finance.financial_ratios(start_s,end_s); target={"Savings Rate":s["savings_target"],"Expense-to-Income Ratio":1-s["savings_target"],"Needs Ratio":s["needs_target"],"Wants Ratio":s["wants_target"],"Savings/Investment Ratio":s["savings_target"],"Debt Repayment Ratio":s["debt_ratio_target"],"Emergency Fund Coverage (months)":s["emergency_months_target"]}; coverage=wealth.emergency_coverage(start_s,end_s); ratios["Emergency Fund Coverage (months)"]=coverage["essential_months"]; ratios["Net Worth"]=nw["net_worth"]; rows=[]
        for k,v in ratios.items():
            tv=target.get(k); status="Informational" if tv is None or v is None else ("On Target" if (v>=tv if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else v<=tv) else ("Below Target" if k in ["Savings Rate","Savings/Investment Ratio","Emergency Fund Coverage (months)"] else "Above Target")); rows.append({"Metric":k,"Actual":v,"Target":tv,"Status":status})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.caption("Emergency coverage is calculated from liquid cash/savings divided by average monthly essential (Need-classified) expenses in the selected period.")

    with tabs[11]:
        st.subheader("Financial Health Intelligence")
        health=pfi.financial_health(start_s,end_s)
        score=personal_health.health_score(start_s,end_s)
        x,y=st.columns(2)
        x.metric("Financial Health Indicator",f"{score['score']:.1f} / 100",score["label"])
        y.info(score["status"])
        st.dataframe(score["components"],use_container_width=True,hide_index=True)
        st.divider()
        for item in health["findings"]:
            with st.container(border=True):
                st.markdown(f"**{item['Metric']}** — {item['Status']}")
                st.write(item["Explanation"])
        st.caption(health["data_quality"])
        st.caption(health["recommendation_note"])
        st.caption("The indicator is a transparent planning metric, not a credit score, investment recommendation or regulated financial assessment.")
    with tabs[12]:
        st.subheader("Data Quality & Controls")
        dq=personal_data_quality.data_quality_report(start_s,end_s)
        if dq["status"]=="PASS": st.success("PASS — no data-quality exceptions detected in the selected period.")
        else: st.warning("REVIEW — one or more data-quality exceptions require attention.")
        st.dataframe(dq["checks"],use_container_width=True,hide_index=True)
        if not dq["issues"].empty: st.subheader("Exceptions Requiring Review"); st.dataframe(dq["issues"],use_container_width=True,hide_index=True)
        st.caption(dq["status_note"])

    with tabs[13]:
        st.subheader("Personal Finance Reports")
        st.caption("Generate a period-based management report from recorded financial data.")
        pack=personal_report.report_pack(start_s,end_s)
        m=pack["metrics"]; nw=pack["net_worth"]
        a,b,c,d=st.columns(4)
        a.metric("Income",money(m["income"],symbol))
        b.metric("Expenses",money(m["expenses"],symbol))
        c.metric("Net Worth",money(nw["net_worth"],symbol))
        d.metric("Health",f"{pack['health']['score']:.1f}/100")
        st.subheader("Executive Summary")
        for item in personal_report.executive_summary(pack): st.write("• "+item)
        st.subheader("Allocation")
        st.dataframe(pack["allocation"],use_container_width=True,hide_index=True)
        st.subheader("Financial Health")
        st.dataframe(pack["health"]["components"],use_container_width=True,hide_index=True)
        st.subheader("Data Quality")
        st.dataframe(pack["data_quality"]["checks"],use_container_width=True,hide_index=True)
        st.subheader("Scenario Summary")
        scenarios=pack.get("scenarios")
        if scenarios is not None and not scenarios.empty:
            st.dataframe(scenarios[["Scenario","Month","Adjusted Income","Adjusted Outflows","Projected Closing Cash","Status"]],use_container_width=True,hide_index=True)
        text_report=personal_report.report_text(pack)
        st.download_button("Download Personal Finance Report (TXT)",text_report,"personal_finance_report.txt","text/plain")
        st.download_button("Download Transactions (CSV)",personal_finance.transactions(start_s,end_s).to_csv(index=False),"personal_finance_transactions.csv","text/csv")
        st.caption(pack["status"])

    with tabs[14]:
        st.subheader("Forward Cash-Flow Forecast")
        months = st.slider("Forecast horizon (months)", 3, 12, 6, key="pf_forecast_months")
        if st.button("Generate Forecast", type="primary"):
            forecast = personal_cashflow_forecast.forecast(end_s, months)
            st.dataframe(forecast, use_container_width=True, hide_index=True)
            if not forecast.empty:
                st.metric("Forecast Closing Cash", money(forecast.iloc[-1]["Closing Cash"], symbol))
                st.line_chart(forecast.set_index("Month")[["Opening Cash","Closing Cash"]])
            st.caption("ESTIMATE: forecast combines recorded liquid cash, historical same-month patterns and active recurring rules. It is a planning scenario, not a guaranteed cash position.")

    with tabs[15]:
        st.subheader("Scenario Planning")
        horizon=st.slider("Scenario horizon (months)",3,12,6,key="pf_scenario_months")
        scenario_name=st.selectbox("Scenario",["Base Case","Conservative","Custom"],key="pf_scenario_name")
        if scenario_name=="Custom":
            a,b,c=st.columns(3)
            inc=a.number_input("Income change %",-100.0,200.0,0.0,step=1.0)
            out=b.number_input("Outflow change %",-100.0,200.0,0.0,step=1.0)
            sav=c.number_input("Savings change %",-100.0,200.0,0.0,step=1.0)
            scenario=personal_scenarios.Scenario("Custom",inc,out,sav)
        elif scenario_name=="Conservative":
            scenario=personal_scenarios.Scenario("Conservative",-10.0,10.0,-10.0)
        else:
            scenario=personal_scenarios.Scenario("Base Case")
        if st.button("Run Scenario",type="primary",key="pf_run_scenario"):
            result=personal_scenarios.project(end_s,horizon,scenario)
            st.dataframe(result[["Month","Adjusted Income","Adjusted Outflows","Adjusted Net Cash Flow","Projected Closing Cash","Status"]],use_container_width=True,hide_index=True)
            if not result.empty:
                st.metric("Scenario Closing Cash",money(result.iloc[-1]["Projected Closing Cash"],symbol))
                st.line_chart(result.set_index("Month")[["Projected Closing Cash"]])
            st.caption("ESTIMATE / SCENARIO: explicit planning assumptions applied to the forward cash-flow model; not a prediction or guaranteed outcome.")

    with tabs[16]:
        st.subheader("Settings & Assumptions"); currencies=["NGN","USD","GBP","EUR"]; currency=st.selectbox("Base Currency",currencies,index=currencies.index(s["currency"]) if s["currency"] in currencies else 0); symbol_map={"NGN":"₦","USD":"$","GBP":"£","EUR":"€"}; fy=st.number_input("Fiscal Year",2000,2100,int(s["fiscal_year"])); opening=st.number_input("Opening Cash Balance",min_value=0.0,value=float(s["opening_cash"])); n=st.number_input("Needs Target (%)",0.0,1.0,float(s["needs_target"])); w=st.number_input("Wants Target (%)",0.0,1.0,float(s["wants_target"])); sv=st.number_input("Savings/Investment Target (%)",0.0,1.0,float(s["savings_target"])); dr=st.number_input("Debt Ratio Target (%)",0.0,1.0,float(s["debt_ratio_target"])); em=st.number_input("Emergency Fund Target (months)",0.0,24.0,float(s["emergency_months_target"]))
        if st.button("Save Settings",key="pf_settings"):
            if abs((n+w+sv)-1)>1e-9: st.error("Needs, Wants and Savings/Investment targets must total 100%.")
            else: personal_finance.update_settings(currency=currency,symbol=symbol_map[currency],fiscal_year=fy,opening_cash=opening,needs_target=n,wants_target=w,savings_target=sv,debt_ratio_target=dr,emergency_months_target=em); st.success("Settings saved."); st.rerun()
        st.caption("The application is a financial-management tool. Targets are configurable planning assumptions, not individualized financial advice.")
