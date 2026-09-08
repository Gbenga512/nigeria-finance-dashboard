import pandas as pd
import streamlit as st

from analytics.reconciliation import normalize_transactions, reconcile


def _read(upload):
    return pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)


def render():
    st.title("🏦 Bank Reconciliation Engine")
    st.caption("One-to-one transaction matching by amount with configurable date tolerance.")
    col1, col2 = st.columns(2)
    with col1:
        bank_file = st.file_uploader("Bank Statement", type=["csv", "xlsx"])
    with col2:
        cashbook_file = st.file_uploader("Cashbook", type=["csv", "xlsx"])
    tolerance = st.number_input("Date tolerance (days)", min_value=0, max_value=30, value=3)

    if not (bank_file and cashbook_file):
        st.info("Upload both files to run the reconciliation.")
        return

    try:
        bank = normalize_transactions(_read(bank_file), "Bank")
        cashbook = normalize_transactions(_read(cashbook_file), "Cashbook")
        bank_result, cashbook_result, matches = reconcile(bank, cashbook, int(tolerance))
    except Exception as exc:
        st.error(str(exc))
        return

    matched = len(matches)
    unmatched_bank = int((~bank_result["Matched"]).sum())
    unmatched_cashbook = int((~cashbook_result["Matched"]).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Matched", matched)
    c2.metric("Unmatched Bank", unmatched_bank)
    c3.metric("Unmatched Cashbook", unmatched_cashbook)

    st.subheader("Matched Transactions")
    st.dataframe(matches, use_container_width=True, hide_index=True)
    st.subheader("Bank Items Requiring Review")
    st.dataframe(bank_result.loc[~bank_result["Matched"]], use_container_width=True, hide_index=True)
    st.subheader("Cashbook Items Requiring Review")
    st.dataframe(cashbook_result.loc[~cashbook_result["Matched"]], use_container_width=True, hide_index=True)
