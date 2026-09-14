"""SME Finance Department: onboarding, operating dashboard and transaction ledger."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.sme_finance import monthly_trend, period_metrics, transaction_health
from ng_ui import hero
from services.sme_store import (
    add_transaction,
    create_business,
    delete_transaction,
    get_or_create_user,
    list_accounts,
    list_businesses,
    transaction_has_posted_journal,
    transactions_df,
    update_transaction,
)


SME_MODULES = [
    ("🏦", "Bank statements", "Import and review bank transactions.", "🏦  SME Bank Statements"),
    ("📚", "Accounting", "Double-entry ledger and financial statements.", "📚  SME Accounting & Statements"),
    ("📘", "Management accounts", "Management KPIs, ratios and recommendations.", "📘  SME Management Accounts"),
    ("📑", "Budget & variance", "Plan revenue and expenses and monitor variance.", "📑  Budget Analysis"),
    ("💧", "Treasury", "Cash position and liquidity scenarios.", "💧  Treasury Dashboard"),
]

TRANSACTION_TYPES = ["Income", "Expense", "Transfer", "Receipt", "Supplier Payment"]
PAYMENT_METHODS = ["Bank transfer", "POS", "Cash", "Card", "Direct debit", "Other"]


def _money(value):
    return "N/A" if value is None else f"₦{value:,.0f}"


def _go_to(target: str) -> None:
    st.session_state["ng_nav_target"] = target
    st.rerun()


def _business_form(user_id: int, form_key: str = "create_sme_business") -> None:
    """Render the business setup form in the main workspace."""
    with st.form(form_key, clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Business name *", placeholder="e.g. Damtob Wholesale Jewelry")
        industry = c2.text_input("Industry", placeholder="Retail, manufacturing, services...")
        c3, c4 = st.columns(2)
        business_type = c3.selectbox("Business type", ["Sole proprietorship", "Partnership", "Limited company", "Other"])
        location = c4.text_input("Location", placeholder="Lagos, Nigeria")
        c5, c6 = st.columns(2)
        cac = c5.text_input("CAC / registration number")
        tin = c6.text_input("TIN")
        c7, c8 = st.columns(2)
        employees = c7.number_input("Employees", min_value=0, step=1)
        year_end = c8.selectbox("Financial year end", ["December", "March", "June", "September"])
        c9, c10 = st.columns(2)
        revenue_range = c9.selectbox("Annual revenue range", ["Not specified", "Below ₦25m", "₦25m–₦100m", "₦100m–₦500m", "Above ₦500m"])
        basis = c10.selectbox("Accounting basis", ["Accrual", "Cash"])
        submitted = st.form_submit_button("Create business profile", use_container_width=True, type="primary")
        if submitted:
            if not name.strip():
                st.error("Business name is required.")
                return
            create_business(user_id, name, industry=industry, business_type=business_type, cac_number=cac, tin=tin, location=location, employees=int(employees), financial_year_end=year_end, revenue_range=revenue_range, accounting_basis=basis)
            st.success("Business profile created. Your finance workspace is now active.")
            st.rerun()


def _render_module_cards() -> None:
    st.markdown("### Finance operations")
    st.caption("Jump directly to the workflow you need. Your existing market and quantitative workspaces remain available from the main menu.")
    for start in range(0, len(SME_MODULES), 2):
        cols = st.columns(2)
        for col, (icon, title, description, target) in zip(cols, SME_MODULES[start:start + 2]):
            with col:
                st.markdown(f"<div class='ng-card'><div class='ng-card-title'>{icon} {title}</div><div class='ng-muted' style='margin:6px 0 12px'>{description}</div></div>", unsafe_allow_html=True)
                if st.button(f"Open {title}", key=f"sme_module_{target}", use_container_width=True):
                    _go_to(target)


def _render_transaction_form(business_id: int, today: date, accounts: list[dict]) -> None:
    st.markdown("### Record a transaction")
    st.caption("Use this for transactions you want in the SME ledger. Bank imports should be reviewed in the Bank Statements module before posting.")
    account_map = {a["name"]: a["id"] for a in accounts}
    with st.form("sme_transaction_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        t_date = c1.date_input("Date", value=today)
        t_type = c2.selectbox("Type", TRANSACTION_TYPES)
        amount = c3.number_input("Amount (₦)", min_value=0.01, step=1000.0)
        c4, c5, c6 = st.columns(3)
        desc = c4.text_input("Description *")
        category = c5.text_input("Category", placeholder="Sales, payroll, rent...")
        account = c6.selectbox("Account", list(account_map) if account_map else ["Main Bank"])
        c7, c8, c9 = st.columns(3)
        counterparty = c7.text_input("Customer / Supplier")
        reference = c8.text_input("Reference")
        payment_method = c9.selectbox("Payment method", PAYMENT_METHODS)
        tax_amount = st.number_input("Tax / VAT amount (₦)", min_value=0.0, step=100.0)
        notes = st.text_input("Notes")
        save = st.form_submit_button("Post transaction", use_container_width=True, type="primary")
        if save:
            try:
                add_transaction(business_id, t_date.isoformat(), desc, amount, t_type, category=category, account_id=account_map.get(account), counterparty=counterparty, reference=reference, payment_method=payment_method, tax_amount=tax_amount, notes=notes)
                st.success("Transaction posted to the operational ledger.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _render_transaction_lifecycle(business_id: int, tx: pd.DataFrame, accounts: list[dict]) -> None:
    st.markdown("### Transaction ledger")
    if tx.empty:
        st.info("No transactions recorded for this business yet. Record your first transaction above or use Bank Statements for an import workflow.")
        return

    with st.expander("Filter transactions", expanded=False):
        f1, f2 = st.columns(2)
        search = f1.text_input("Search", placeholder="Description, category, customer, reference...")
        type_filter = f2.selectbox("Transaction type", ["All"] + TRANSACTION_TYPES)
        f3, f4 = st.columns(2)
        source_filter = f3.selectbox("Source", ["All"] + sorted(tx["source"].fillna("Manual").astype(str).unique().tolist()))
        status_filter = f4.selectbox("Accounting status", ["All", "Posted to accounting", "Operational only"])
        min_tx = tx["transaction_date"].min().date()
        max_tx = tx["transaction_date"].max().date()
        date_range = st.date_input("Date range", value=(min_tx, max_tx), key="sme_ledger_date_range")

    view = tx.copy()
    if search:
        mask = view.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False, regex=False)).any(axis=1)
        view = view[mask]
    if type_filter != "All":
        view = view[view["transaction_type"] == type_filter]
    if source_filter != "All":
        view = view[view["source"].fillna("Manual") == source_filter]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        view = view[(view["transaction_date"].dt.date >= date_range[0]) & (view["transaction_date"].dt.date <= date_range[1])]

    posted_ids = {int(row["id"]) for _, row in view.iterrows() if transaction_has_posted_journal(business_id, int(row["id"]))}
    if status_filter == "Posted to accounting":
        view = view[view["id"].isin(posted_ids)]
    elif status_filter == "Operational only":
        view = view[~view["id"].isin(posted_ids)]

    st.caption(f"Showing {len(view):,} of {len(tx):,} transaction(s). Transactions already posted to accounting are protected from direct editing/deletion.")
    display = view.copy()
    display["Accounting"] = display["id"].map(lambda x: "Posted" if int(x) in posted_ids else "Operational")
    display["Amount"] = display["amount"].map(lambda x: f"₦{float(x):,.0f}")
    st.dataframe(display[["transaction_date", "description", "transaction_type", "category", "Amount", "counterparty", "reference", "payment_method", "source", "Accounting"]], use_container_width=True, hide_index=True)
    st.download_button("Export filtered CSV", display.to_csv(index=False).encode("utf-8"), "sme_transactions_filtered.csv", "text/csv", use_container_width=True)

    if view.empty:
        return

    st.markdown("### Manage a transaction")
    options = {f"#{int(row['id'])} · {row['transaction_date']:%d %b %Y} · {row['description'][:55]} · ₦{float(row['amount']):,.0f}": int(row["id"]) for _, row in view.iterrows()}
    selected_label = st.selectbox("Select transaction", list(options), key="sme_manage_transaction")
    selected_id = options[selected_label]
    selected = tx[tx["id"] == selected_id].iloc[0]
    is_posted = selected_id in posted_ids or transaction_has_posted_journal(business_id, selected_id)
    if is_posted:
        st.warning("This transaction is already posted to the double-entry ledger. Direct edit/delete is locked to protect the accounting trail.")
        return

    account_map = {a["name"]: a["id"] for a in accounts}
    reverse_accounts = {int(a["id"]): a["name"] for a in accounts}
    with st.form(f"edit_transaction_{selected_id}"):
        e1, e2 = st.columns(2)
        e_date = e1.date_input("Date", value=selected["transaction_date"].date())
        e_type = e2.selectbox("Type", TRANSACTION_TYPES, index=TRANSACTION_TYPES.index(selected["transaction_type"]))
        e3, e4 = st.columns(2)
        e_amount = e3.number_input("Amount (₦)", min_value=0.01, value=float(selected["amount"]), step=1000.0)
        e_category = e4.text_input("Category", value=str(selected["category"] or ""))
        e5, e6 = st.columns(2)
        current_account = reverse_accounts.get(int(selected["account_id"])) if pd.notna(selected["account_id"]) else None
        account_options = list(account_map)
        account_index = account_options.index(current_account) if current_account in account_options else 0
        e_account = e5.selectbox("Account", account_options, index=account_index)
        e_counterparty = e6.text_input("Customer / Supplier", value=str(selected["counterparty"] or ""))
        e7, e8 = st.columns(2)
        e_reference = e7.text_input("Reference", value=str(selected["reference"] or ""))
        current_method = str(selected["payment_method"] or "Other")
        e_method = e8.selectbox("Payment method", PAYMENT_METHODS, index=PAYMENT_METHODS.index(current_method) if current_method in PAYMENT_METHODS else PAYMENT_METHODS.index("Other"))
        e_tax = st.number_input("Tax / VAT amount (₦)", min_value=0.0, value=float(selected["tax_amount"] or 0), step=100.0)
        e_desc = st.text_input("Description *", value=str(selected["description"]))
        e_notes = st.text_input("Notes", value=str(selected["notes"] or ""))
        save_edit = st.form_submit_button("Save changes", use_container_width=True, type="primary")
        if save_edit:
            try:
                update_transaction(business_id, selected_id, transaction_date=e_date.isoformat(), description=e_desc, amount=e_amount, transaction_type=e_type, category=e_category, account_id=account_map[e_account], counterparty=e_counterparty, reference=e_reference, payment_method=e_method, tax_amount=e_tax, notes=e_notes)
                st.success("Transaction updated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    with st.expander("Delete transaction", expanded=False):
        st.warning("Deletion is only available for transactions that have not been posted to accounting. For posted entries, use an accounting correction workflow so the audit trail is preserved.")
        confirm = st.checkbox("I understand this permanently removes the operational transaction.", key=f"confirm_delete_{selected_id}")
        if st.button("Delete transaction", key=f"delete_{selected_id}", disabled=not confirm, use_container_width=True):
            try:
                delete_transaction(business_id, selected_id)
                st.success("Transaction deleted.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def render() -> None:
    hero("SME Financial Intelligence", "A practical finance department for Nigerian SMEs — capture transactions, understand cash, produce accounts and act on financial signals.", "Finance department")
    user_id = get_or_create_user()
    businesses = list_businesses(user_id)

    if not businesses:
        st.markdown("## Set up your business in 2 minutes")
        st.caption("Start with your business profile. You can add transactions and connect the accounting workflows after setup.")
        with st.container(border=True):
            st.markdown("### 1 · Business profile")
            _business_form(user_id, "create_sme_business_main")
        st.markdown("### What you get")
        cols = st.columns(2)
        benefits = [("📊", "Finance overview", "Revenue, expenses, profit, cash flow and data quality."), ("🧾", "Accounting foundation", "Transaction capture, double-entry accounting and statements."), ("💧", "Cash visibility", "Historical cash movements and a 13-week forecast."), ("📈", "Management intelligence", "Ratios, budget variance, risks and management recommendations.")]
        for col, (icon, title, text) in zip(cols * 2, benefits):
            with col:
                st.markdown(f"<div class='ng-card'><div class='ng-card-title'>{icon} {title}</div><div class='ng-muted' style='margin-top:6px'>{text}</div></div>", unsafe_allow_html=True)
        st.info("No financial figures are shown until you add real business data. NG Finance Pro does not fabricate SME performance data.")
        return

    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    selected_label = st.selectbox("Active business", labels, key="sme_active_business")
    business = businesses[labels.index(selected_label)]
    business_id = int(business["id"])

    with st.expander("Business profile", expanded=False):
        profile_cols = st.columns(2)
        profile = [("Business type", business["business_type"]), ("Industry", business["industry"] or "Not specified"), ("Location", business["location"] or "Not specified"), ("CAC / registration", business["cac_number"] or "Not specified"), ("TIN", business["tin"] or "Not specified"), ("Employees", business["employees"]), ("Financial year end", business["financial_year_end"]), ("Accounting basis", business["accounting_basis"])]
        for index, (label, value) in enumerate(profile):
            profile_cols[index % 2].markdown(f"**{label}**\n\n{value}")

    tx = transactions_df(business_id)
    min_date = tx["transaction_date"].min().date() if not tx.empty and tx["transaction_date"].notna().any() else date.today().replace(day=1)
    max_date = tx["transaction_date"].max().date() if not tx.empty and tx["transaction_date"].notna().any() else date.today()
    today = date.today()
    st.markdown("### Finance overview")
    period = st.selectbox("Reporting period", ["This month", "Last month", "Quarter", "Year", "Custom"], key="sme_period")
    if period == "This month": start, end = today.replace(day=1), today
    elif period == "Last month": end = today.replace(day=1) - timedelta(days=1); start = end.replace(day=1)
    elif period == "Quarter": start, end = today - timedelta(days=89), today
    elif period == "Year": start, end = today.replace(month=1, day=1), today
    else:
        selected_dates = st.date_input("Custom period", value=(max(min_date, today.replace(day=1)), min(max_date, today)), key="sme_custom_period")
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2: start, end = selected_dates
        else: start = end = selected_dates

    metrics = period_metrics(tx, start, end)
    health = transaction_health(tx)
    margin = metrics["net_profit"] / metrics["revenue"] if metrics["revenue"] else None
    kpi_rows = [[("Revenue", metrics["revenue"]), ("Expenses", metrics["expenses"])], [("Net Profit", metrics["net_profit"]), ("Cash Flow", metrics["cash_flow"])], [("Cash Balance", metrics["cash_balance"]), ("Data Quality", None if health["score"] is None else f"{health['score']:.1f}/100")]]
    for row in kpi_rows:
        cols = st.columns(2)
        for col, (label, value) in zip(cols, row):
            col.metric(label, value if label == "Data Quality" else _money(value))
    st.caption(f"{start:%d %b %Y} → {end:%d %b %Y} • {metrics['count']:,} transaction(s). Gross profit, AR/AP, inventory and a true closing cash balance require their respective subledgers.")

    _render_module_cards()

    st.markdown("### Performance trend")
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
            fig.update_layout(title="Monthly Finance Trend", yaxis_title="₦", height=340, hovermode="x unified", margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("### Finance health")
        st.metric("Net margin", "N/A" if margin is None else f"{margin:.1%}")
        if health["score"] is None:
            st.info("Add transaction data to activate the finance health score.")
        else:
            st.progress(min(1.0, health["score"] / 100))
            for factor in health["factors"]:
                st.write(f"**{factor['Factor']}: {factor['Score']:.1f}/100**")
                st.caption(factor["Explanation"])

    accounts = list_accounts(business_id)
    _render_transaction_form(business_id, today, accounts)
    _render_transaction_lifecycle(business_id, tx, accounts)
    st.caption("NG Finance Pro is a financial-management and analytics tool. It does not provide tax advice, investment advice, or regulated financial services.")
