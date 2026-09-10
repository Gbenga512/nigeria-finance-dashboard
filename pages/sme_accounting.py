"""SME accounting workspace with self-contained onboarding and double-entry controls."""
from __future__ import annotations

from datetime import date, timedelta
import streamlit as st

from ng_ui import hero
from services.sme_store import create_business, get_or_create_user, list_businesses
from services.sme_accounting import (
    account_catalog, balance_sheet, cash_flow, journal_entries_df,
    post_journal_entry, profit_and_loss, sync_eligible_transactions,
    trial_balance, ensure_standard_accounts,
)


def _money(v: float) -> str:
    return f"₦{float(v):,.0f}"


def _create_business_form(user_id: int) -> None:
    st.subheader("Set up your SME finance workspace")
    st.write("Create your business profile here. You do not need to leave this page or use the sidebar.")
    with st.form("accounting_onboarding", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Business name", placeholder="e.g. G&BO Enterprises")
        industry = c2.text_input("Industry", placeholder="Retail, services, manufacturing...")
        c3, c4 = st.columns(2)
        business_type = c3.selectbox("Business type", ["Sole proprietorship", "Partnership", "Limited company", "Other"])
        location = c4.text_input("Location", value="Lagos, Nigeria")
        c5, c6 = st.columns(2)
        cac = c5.text_input("CAC / registration number")
        tin = c6.text_input("TIN")
        c7, c8 = st.columns(2)
        employees = c7.number_input("Employees", min_value=0, step=1)
        basis = c8.selectbox("Accounting basis", ["Accrual", "Cash"])
        year_end = st.selectbox("Financial year end", ["December", "March", "June", "September"])
        revenue_range = st.selectbox("Annual revenue range", ["Not specified", "Below ₦25m", "₦25m–₦100m", "₦100m–₦500m", "Above ₦500m"])
        submitted = st.form_submit_button("Create business & activate accounting", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Business name is required.")
                return
            try:
                create_business(
                    user_id, name, industry=industry, business_type=business_type,
                    cac_number=cac, tin=tin, location=location, employees=int(employees),
                    financial_year_end=year_end, revenue_range=revenue_range,
                    accounting_basis=basis,
                )
                st.success("Business created. Accounting workspace is now active.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not create business: {exc}")


def _period():
    today = date.today()
    choice = st.selectbox("Reporting period", ["This month", "Last month", "Quarter", "Year", "Custom"], key="acct_period")
    if choice == "This month":
        return today.replace(day=1), today
    if choice == "Last month":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if choice == "Quarter":
        return today - timedelta(days=89), today
    if choice == "Year":
        return today.replace(month=1, day=1), today
    value = st.date_input("Custom period", value=(today.replace(day=1), today), key="acct_custom")
    return value[0], value[1]


def render() -> None:
    hero(
        "SME Accounting & Financial Statements",
        "Double-entry journals, trial balance and management statements built from the SME finance ledger.",
        "Accounting Engine",
    )
    user_id = get_or_create_user()
    businesses = list_businesses(user_id)

    if not businesses:
        st.info("Your accounting workspace is ready. Create your first SME business below.")
        _create_business_form(user_id)
        st.markdown("### What becomes available")
        st.write("✓ Profit & Loss  •  ✓ Balance Sheet  •  ✓ Trial Balance  •  ✓ Journal Entries  •  ✓ Cash Flow  •  ✓ Chart of Accounts")
        st.caption("No financial data is fabricated. Statements populate after you post or import transactions.")
        return

    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    label = st.selectbox("Active business", labels, key="acct_business")
    business = businesses[labels.index(label)]
    business_id = int(business["id"])
    ensure_standard_accounts(business_id)
    start, end = _period()

    pnl = profit_and_loss(business_id, start, end)
    bs = balance_sheet(business_id, end)
    tb = trial_balance(business_id, start, end)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", _money(pnl["Revenue"]))
    c2.metric("Expenses", _money(pnl["Expenses"]))
    c3.metric("Net Income", _money(pnl["Net Income"]))
    c4.metric("Balance Sheet", "BALANCED" if bs["Balanced"] else "OUT OF BALANCE")

    st.caption(f"Period: {start:%d %b %Y} → {end:%d %b %Y}. Statements only use posted journals; no balances are fabricated.")

    tabs = st.tabs(["Financial Statements", "Trial Balance", "Journal Entry", "Transaction Sync", "Chart of Accounts"])
    with tabs[0]:
        st.subheader("Profit & Loss")
        st.dataframe({"Line": ["Revenue", "Expenses", "Net Income"], "Amount": [_money(pnl["Revenue"]), _money(pnl["Expenses"]), _money(pnl["Net Income"])]}, use_container_width=True, hide_index=True)
        st.subheader("Balance Sheet")
        st.dataframe({"Line": ["Assets", "Liabilities", "Equity", "Liabilities + Equity"], "Amount": [_money(bs["Assets"]), _money(bs["Liabilities"]), _money(bs["Equity"]), _money(bs["Liabilities + Equity"])]}, use_container_width=True, hide_index=True)
        if not bs["Balanced"]:
            st.error("The balance sheet does not balance. Review posted journals before relying on the statement.")
        cf = cash_flow(business_id, start, end)
        st.subheader("Direct Cash Flow")
        if cf.empty:
            st.info("No posted cash movements for this period.")
        else:
            st.dataframe(cf, use_container_width=True, hide_index=True)
        st.download_button("Export trial balance CSV", tb.to_csv(index=False).encode("utf-8"), f"{business['name']}_trial_balance.csv", "text/csv")

    with tabs[1]:
        total_debits = float(tb["Debits"].sum())
        total_credits = float(tb["Credits"].sum())
        a, b, c = st.columns(3)
        a.metric("Total Debits", _money(total_debits))
        b.metric("Total Credits", _money(total_credits))
        c.metric("Difference", _money(abs(total_debits - total_credits)))
        st.dataframe(tb, use_container_width=True, hide_index=True)

    with tabs[2]:
        accounts = account_catalog(business_id)
        options = {f"{r['name']} ({r['account_type']})": int(r['id']) for _, r in accounts.iterrows()}
        names = list(options)
        st.caption("A journal is posted only when total debits equal total credits.")
        with st.form("manual_journal", clear_on_submit=True):
            jdate = st.date_input("Entry date", value=date.today())
            desc = st.text_input("Description")
            reference = st.text_input("Reference")
            debit_name = st.selectbox("Debit account", names, key="journal_debit")
            credit_name = st.selectbox("Credit account", names, key="journal_credit")
            amount = st.number_input("Amount (₦)", min_value=0.01, step=1000.0)
            submitted = st.form_submit_button("Post balanced journal", type="primary", use_container_width=True)
            if submitted:
                if debit_name == credit_name:
                    st.error("Debit and credit accounts must be different.")
                else:
                    try:
                        entry_id = post_journal_entry(business_id, jdate, desc, [{"account_id": options[debit_name], "debit": amount}, {"account_id": options[credit_name], "credit": amount}], reference=reference)
                        st.success(f"Journal #{entry_id} posted and balanced.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        entries = journal_entries_df(business_id, start, end)
        if not entries.empty:
            st.dataframe(entries, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.info("This converts eligible Income/Receipt and Expense/Supplier Payment transactions into balanced cash journals. Transfers are intentionally skipped because the current transaction record does not identify both sides of the transfer.")
        if st.button("Sync eligible transactions to double-entry journals", type="primary", use_container_width=True):
            posted, skipped = sync_eligible_transactions(business_id)
            st.success(f"Synced {posted} transaction(s). Skipped {skipped} transfer(s). Existing journal links are not duplicated.")
            st.rerun()
        entries = journal_entries_df(business_id)
        st.metric("Posted journal lines", len(entries))

    with tabs[4]:
        st.dataframe(account_catalog(business_id), use_container_width=True, hide_index=True)
        st.caption("Standard accounts are created only when missing. Existing Phase 1 account records and balances are preserved.")

    st.caption("NG Finance Pro accounting is a financial-management tool. It does not constitute regulated tax, audit, investment or banking advice.")
