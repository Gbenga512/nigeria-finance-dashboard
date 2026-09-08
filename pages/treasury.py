import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui import hero


def render():
    hero(
        "Treasury Intelligence",
        "Monitor liquidity, available cash and short-term funding headroom from one executive workspace.",
        "Treasury workspace",
    )

    with st.expander("Treasury inputs", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cash = st.number_input("Cash position (₦)", min_value=0.0, value=250_000_000.0, step=1_000_000.0)
        with c2:
            cheques = st.number_input("Outstanding cheques (₦)", min_value=0.0, value=12_000_000.0, step=500_000.0)
        with c3:
            deposits = st.number_input("Unpresented deposits (₦)", min_value=0.0, value=5_000_000.0, step=500_000.0)
        c4, c5 = st.columns(2)
        with c4:
            unreconciled = st.number_input("Unreconciled transactions (₦)", min_value=0.0, value=3_500_000.0, step=250_000.0)
        with c5:
            avg_daily_outflow = st.number_input("Average daily cash outflow (₦)", min_value=0.0, value=10_000_000.0, step=500_000.0)

    adjusted_cash = cash + deposits - cheques - unreconciled
    runway = adjusted_cash / avg_daily_outflow if avg_daily_outflow else None
    liquidity_ratio = adjusted_cash / cash if cash else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash position", f"₦{cash:,.0f}")
    c2.metric("Available cash", f"₦{adjusted_cash:,.0f}")
    c3.metric("Cash runway", "N/A" if runway is None else f"{runway:.1f} days")
    c4.metric("Liquidity coverage", "N/A" if liquidity_ratio is None else f"{liquidity_ratio:.1%}")

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        components = pd.DataFrame({"Component": ["Cash", "Deposits", "Cheques", "Unreconciled"], "Amount": [cash, deposits, -cheques, -unreconciled]})
        fig = go.Figure(go.Bar(x=components["Component"], y=components["Amount"], text=components["Amount"].map(lambda x: f"₦{x/1e6:,.1f}m"), textposition="outside"))
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="₦", showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Liquidity assessment")
        if adjusted_cash <= 0:
            st.error("Immediate liquidity pressure")
        elif runway is not None and runway < 15:
            st.warning("Short cash runway — management attention recommended")
        elif runway is not None and runway < 30:
            st.warning("Moderate liquidity headroom")
        else:
            st.success("Healthy short-term liquidity headroom")
        st.caption("Runway is an analytical estimate based on the inputs above, not a funding commitment.")

    table = pd.DataFrame({"Treasury metric": ["Cash Position", "Unpresented Deposits", "Outstanding Cheques", "Unreconciled Transactions", "Adjusted Available Cash"], "Amount (₦)": [cash, deposits, cheques, unreconciled, adjusted_cash]})
    st.markdown("### Treasury position")
    st.dataframe(table, use_container_width=True, hide_index=True)
