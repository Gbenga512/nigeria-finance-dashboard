"""Phase 1 SME Finance Department: business profile, transactions and dashboard."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.sme_finance import monthly_trend, period_metrics, transaction_health
from ng_ui import hero
from services.sme_store import add_transaction, create_business, get_or_create_user, list_accounts, list_businesses, transactions_df


def _money(value):
    return "N/A" if value is None else f"₦{value:,.0f}"


def render() -> None:
    hero("SME Financial Intelligence", "A dedicated finance department workspace for Nigerian SMEs — records, cash visibility and management intelligence.", "SME Finance")
    user_id = get_or_create_user()
    businesses = list_businesses(user_id)

    with st.sidebar.expander("SME business profile", expanded=not businesses):
        with st.form("create_sme_business", clear_on_submit=True):
            name = st.text_input("Business name")
            industry = st.text_input("Industry", placeholder="Retail, manufacturing, services...")
            business_type = st.selectbox("Business type", ["Sole proprietorship", "Partnership", "Limited company", "Other"])
            cac = st.text_input("CAC / registration number")
            tin = st.text_input("TIN")
            location = st.text_input("Location", placeholder="Lagos, Nigeria")
            employees = st.number_input("Employees", min_value=0, step=1)
            year_end = st.selectbox("Financial year end", ["December", "March", "June", "September"])
            revenue_range = st.selectbox("Annual revenue range", ["Not specified", "Below ₦25m", "₦25m–₦100m", "₦100m–₦500m", "Above ₦500m"])
            basis = st.selectbox("Accounting basis", ["Accrual", "Cash"])
            submitted = st.form_submit_button("Create business", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("Business name is required.")
                else:
                    create_business(user_id, name, industry=industry, business_type=business_type, cac_number=cac, tin=tin, location=location, employees=int(employees), financial_year_end=year_end, revenue_range=revenue_range, accounting_basis=basis)
                    st.success("Business created. Select it below.")
                    st.rerun()

    if not businesses:
        st.info("Create your first SME business profile in the sidebar to activate the finance department.")
        st.markdown("### Phase 1 now available")
        st.write("Business profile • Transaction ledger • Cash/revenue/expense dashboard • Monthly trend • Data-quality health")
        return

    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    selected_label = st.selectbox("Active business", labels, key="sme_active_business")
    business = businesses[labels.index(selected_label)]
    business_id = int(business["id"])

    tx = transactions_df(business_id)
    min_date = tx["transaction_date"].min().date() if not tx.empty and tx["transaction_date"].notna().any() else date.today().replace(day=1)
    max_date = tx["transaction_date"].max().date() if not tx.empty and tx["transaction_date"].notna().any() else date.today()
    today = date.today()
    period = st.selectbox("Reporting period", ["This month", "Last month", "Quarter", "Year", "Custom"], key="sme_period")
    if period == "This month": start, end = today.replace(day=1), today
    elif period == "Last month":
        end = today.replace(day=1) - timedelta(days=1); start = end.replace(day=1)
    elif period == "Quarter": start, end = today - timedelta(days=89), today
    elif period == "Year": start, end = today.replace(month=1, day=1), today
    else:
        start, end = st.date_input("Custom period", value=(max(min_date, today.replace(day=1)), today), key="sme_custom_period")
        if isinstance(start, tuple): start, end = start

    metrics = period_metrics(tx, start, end)
    health = transaction_health(tx)
    margin = metrics["net_profit"] / metrics["revenue"] if metrics["revenue"] else None

    cards = st.columns(6)
    for card, label, value in zip(cards, ["Revenue","Expenses","Net Profit","Cash Flow","Cash Balance","Finance Data Score"], [metrics["revenue"],metrics["expenses"],metrics["net_profit"],metrics["cash_flow"],metrics["cash_balance"],health["score"]]):
        if label == "Finance Data Score": text = "N/A" if value is None else f"{value:.1f}/100"
        else: text = _money(value)
        card.metric(label, text)
    st.caption(f"Period: {start:%d %b %Y} → {end:%d %b %Y} • {metrics['count']:,} transaction(s). Gross profit, AR/AP, inventory and true closing cash remain N/A until their subledgers are populated in later phases.")

    left, right = st.columns([1.6, 1], gap="large")
    with left:
        trend = monthly_trend(tx)
        if trend.empty:
            st.info("Add transactions to populate the management trend.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend["Month"], y=trend["Revenue"], name="Revenue", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=trend["Month"], y=trend["Expenses"], name="Expenses", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=trend["Month"], y=trend["Net Cash Flow"], name="Net cash flow", mode="lines+markers"))
            fig.update_layout(title="Monthly Finance Trend", yaxis_title="₦", height=360, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    with right:
        st.markdown("### Finance health")
        st.metric("Net margin", "N/A" if margin is None else f"{margin:.1%}")
        if health["score"] is None: st.info("No transaction data yet.")
        else:
            st.progress(min(1.0, health["score"] / 100))
            for factor in health["factors"]:
                st.write(f"**{factor['Factor']}: {factor['Score']:.1f}/100**")
                st.caption(factor["Explanation"])

    st.markdown("### Add transaction")
    accounts = list_accounts(business_id)
    account_map = {a["name"]: a["id"] for a in accounts}
    with st.form("sme_transaction_form", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        t_date = c1.date_input("Date", value=today)
        t_type = c2.selectbox("Type", ["Income","Expense","Transfer","Receipt","Supplier Payment"])
        amount = c3.number_input("Amount (₦)", min_value=0.01, step=1000.0)
        c4,c5,c6 = st.columns(3)
        desc = c4.text_input("Description")
        category = c5.text_input("Category", placeholder="Sales, payroll, rent...")
        account = c6.selectbox("Account", list(account_map) if account_map else ["Main Bank"])
        c7,c8,c9 = st.columns(3)
        counterparty = c7.text_input("Customer / Supplier")
        reference = c8.text_input("Reference")
        payment_method = c9.selectbox("Payment method", ["Bank transfer","POS","Cash","Card","Direct debit","Other"])
        tax_amount = st.number_input("Tax / VAT amount (₦)", min_value=0.0, step=100.0)
        notes = st.text_input("Notes")
        save = st.form_submit_button("Post transaction", use_container_width=True)
        if save:
            try:
                add_transaction(business_id, t_date.isoformat(), desc, amount, t_type, category=category, account_id=account_map.get(account), counterparty=counterparty, reference=reference, payment_method=payment_method, tax_amount=tax_amount, notes=notes)
                st.success("Transaction posted.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown("### Transaction ledger")
    if tx.empty:
        st.info("No transactions recorded for this business yet.")
    else:
        search = st.text_input("Search transactions", placeholder="Description, category, customer, reference...")
        view = tx.copy()
        if search:
            mask = view.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            view = view[mask]
        view["Amount"] = view["amount"].map(lambda x: f"₦{float(x):,.0f}")
        st.dataframe(view[["transaction_date","description","transaction_type","category","Amount","counterparty","reference","payment_method"]], use_container_width=True, hide_index=True)
        st.download_button("Export transactions CSV", view.to_csv(index=False).encode("utf-8"), f"{business['name']}_transactions.csv", "text/csv")

    with st.expander("Business profile"):
        st.json({k: business[k] for k in ["name","industry","business_type","cac_number","tin","location","employees","financial_year_end","revenue_range","accounting_basis","currency"]})
    st.caption("Phase 1 is a financial-management foundation. It does not provide tax advice, investment advice, or a regulated financial service.")
