from __future__ import annotations

from datetime import date

import plotly.express as px
import streamlit as st

from services import personal_finance


def render() -> None:
    personal_finance.ensure_schema()
    st.title("👤 Personal Finance")
    st.caption("Track personal income, spending, savings, debt and investments in NG Finance Pro.")

    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("From", today.replace(day=1), key="pf_start")
    with c2:
        end = st.date_input("To", today, key="pf_end")
    if start > end:
        st.error("The start date must be before the end date.")
        return

    metrics = personal_finance.dashboard_metrics(start.isoformat(), end.isoformat())
    cols = st.columns(5)
    cards = [
        ("Income", metrics["income"]),
        ("Expenses", metrics["expenses"]),
        ("Net Cash Flow", metrics["net_cash_flow"]),
        ("Savings", metrics["savings"]),
        ("Investments", metrics["investments"]),
    ]
    for col, (label, value) in zip(cols, cards):
        col.metric(label, f"₦{value:,.2f}")

    if metrics["savings_rate"] is not None:
        st.caption(f"Savings rate: {metrics['savings_rate']:.1f}% • {metrics['transaction_count']} tracked transactions")

    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Transactions", "Budget", "Accounts"])

    with tab1:
        spending = personal_finance.spending_by_category(start.isoformat(), end.isoformat())
        if spending.empty:
            st.info("No expense transactions exist for this period yet.")
        else:
            fig = px.bar(spending, x="category", y="amount", title="Spending by Category")
            fig.update_layout(yaxis_title="Amount (₦)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        nw = personal_finance.net_worth()
        st.subheader("Financial Position")
        st.info(nw["status"])
        st.metric("Tracked Cash Movement", f"₦{nw['tracked_cash_movement']:,.2f}")

    with tab2:
        st.subheader("Add Transaction")
        accts = personal_finance.accounts()
        with st.form("personal_transaction_form", clear_on_submit=True):
            d, desc = st.columns(2)
            tx_date = d.date_input("Date", today)
            description = desc.text_input("Description")
            a, typ, cat = st.columns(3)
            amount = a.number_input("Amount (₦)", min_value=0.01, step=100.0, format="%.2f")
            tx_type = typ.selectbox("Type", personal_finance.PERSONAL_TYPES)
            categories = personal_finance.DEFAULT_CATEGORIES.get(tx_type, ["Other"])
            category = cat.selectbox("Category", categories)
            account_options = dict(zip(accts["name"], accts["id"]))
            account_name = st.selectbox("Account", list(account_options))
            reference = st.text_input("Reference")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save Transaction", type="primary")
            if submitted:
                try:
                    personal_finance.add_transaction(tx_date.isoformat(), description, amount, tx_type, category, int(account_options[account_name]), reference, notes)
                    st.success("Transaction saved.")
                except ValueError as exc:
                    st.error(str(exc))

        df = personal_finance.transactions(start.isoformat(), end.isoformat())
        st.subheader("Transaction Register")
        if df.empty:
            st.info("No transactions in the selected period.")
        else:
            st.dataframe(df[["transaction_date", "description", "transaction_type", "category", "amount", "account_name", "reference"]], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Personal Budget")
        st.info("Budget envelopes are part of the next implementation layer. The transaction engine is ready to receive the Excel-based rules and categories.")

    with tab4:
        st.subheader("Personal Accounts")
        st.dataframe(accts[["name", "account_type", "opening_balance"]], use_container_width=True, hide_index=True)
        st.caption("Account opening balances, assets, liabilities and full net-worth accounting will be mapped from the user's reference specification before production release.")
