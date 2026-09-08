import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from analytics.reconciliation import normalize_transactions, reconcile
from ui import hero


def _read(upload):
    return pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)


def render():
    hero(
        "Bank Reconciliation",
        "Match bank and cashbook transactions, isolate exceptions and focus review effort where it matters.",
        "Reconciliation engine",
    )
    col1, col2 = st.columns(2)
    with col1:
        bank_file = st.file_uploader("Bank statement", type=["csv", "xlsx"])
    with col2:
        cashbook_file = st.file_uploader("Cashbook", type=["csv", "xlsx"])
    tolerance = st.number_input("Date tolerance (days)", min_value=0, max_value=30, value=3)

    if not (bank_file and cashbook_file):
        st.info("Upload both files to activate the reconciliation engine.")
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
    total_items = len(bank_result) + len(cashbook_result)
    match_rate = (matched * 2 / total_items) if total_items else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matched", matched)
    c2.metric("Unmatched bank", unmatched_bank)
    c3.metric("Unmatched cashbook", unmatched_cashbook)
    c4.metric("Match rate", f"{match_rate:.1%}")

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        fig = go.Figure(go.Pie(labels=["Matched", "Bank exceptions", "Cashbook exceptions"], values=[matched, unmatched_bank, unmatched_cashbook], hole=0.68))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=True, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Control status")
        if unmatched_bank + unmatched_cashbook == 0:
            st.success("All supplied transactions are reconciled.")
        elif match_rate >= 0.9:
            st.warning("Reconciliation is largely complete; review remaining exceptions.")
        else:
            st.error("Material reconciliation exceptions require review.")
        st.caption("Matching is based on normalized transaction amount and the configured date tolerance.")

    st.markdown("### Matched transactions")
    st.dataframe(matches, use_container_width=True, hide_index=True)
    with st.expander("Bank exceptions"):
        st.dataframe(bank_result.loc[~bank_result["Matched"]], use_container_width=True, hide_index=True)
    with st.expander("Cashbook exceptions"):
        st.dataframe(cashbook_result.loc[~cashbook_result["Matched"]], use_container_width=True, hide_index=True)
