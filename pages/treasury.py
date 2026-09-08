import streamlit as st
import pandas as pd


def render():
    st.title("🏦 Treasury Dashboard")
    st.caption("Management-input treasury view. Values are session inputs until a database is connected.")

    c1, c2, c3 = st.columns(3)
    with c1:
        cash = st.number_input("Cash position (₦)", min_value=0.0, value=250_000_000.0, step=1_000_000.0)
    with c2:
        cheques = st.number_input("Outstanding cheques (₦)", min_value=0.0, value=12_000_000.0, step=500_000.0)
    with c3:
        deposits = st.number_input("Unpresented deposits (₦)", min_value=0.0, value=5_000_000.0, step=500_000.0)

    unreconciled = st.number_input("Unreconciled transactions (₦)", min_value=0.0, value=3_500_000.0, step=250_000.0)
    avg_daily_outflow = st.number_input("Average daily cash outflow (₦)", min_value=0.0, value=10_000_000.0, step=500_000.0)

    adjusted_cash = cash + deposits - cheques - unreconciled
    runway = adjusted_cash / avg_daily_outflow if avg_daily_outflow else None

    a, b = st.columns(2)
    a.metric("Adjusted Available Cash", f"₦{adjusted_cash:,.0f}")
    b.metric("Estimated Cash Runway", "N/A" if runway is None else f"{runway:.1f} days")

    table = pd.DataFrame({
        "Treasury Metric": ["Cash Position", "Unpresented Deposits", "Outstanding Cheques", "Unreconciled Transactions", "Adjusted Available Cash"],
        "Amount (₦)": [cash, deposits, cheques, unreconciled, adjusted_cash],
    })
    st.dataframe(table, use_container_width=True, hide_index=True)
