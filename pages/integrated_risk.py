import pandas as pd
import streamlit as st

from analytics.integrated_risk import integrated_risk_score, risk_driver_table
from analytics.liquidity_fx import liquidity_metrics
from ng_ui import hero


def render(snapshot: pd.DataFrame):
    hero("Integrated Risk Command Centre", "One management view connecting market risk, liquidity runway and FX exposure.", "Enterprise risk")

    c1, c2, c3 = st.columns(3)
    with c1:
        liquid_cash = st.number_input("Liquid cash / assets", min_value=0.0, value=0.0, step=100000.0, format="%.2f")
    with c2:
        daily_outflow = st.number_input("Average daily cash outflow", min_value=0.0, value=0.0, step=10000.0, format="%.2f")
    with c3:
        fx_exposure = st.number_input("Foreign-currency exposure (NGN equivalent)", min_value=0.0, value=0.0, step=100000.0, format="%.2f")

    liquidity = liquidity_metrics(liquid_cash, daily_outflow)
    result = integrated_risk_score(snapshot, liquidity["runway_days"], fx_exposure)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Integrated Risk Score", f"{result['score']:.1f}/100")
    m2.metric("Risk Level", result["level"])
    runway = liquidity["runway_days"]
    m3.metric("Liquidity Runway", "∞" if runway == float("inf") else f"{runway:.1f} days")
    m4.metric("FX Exposure", f"₦{fx_exposure:,.0f}")

    if result["level"] in {"Critical", "High"}:
        st.error(result["action"])
    elif result["level"] == "Elevated":
        st.warning(result["action"])
    else:
        st.success(result["action"])

    st.markdown("### Principal risk drivers")
    if result["drivers"]:
        for driver in result["drivers"]:
            st.write(f"• {driver}")
    else:
        st.write("No material driver was detected by the current rule set.")

    st.markdown("### Audit view")
    table = risk_driver_table(snapshot, runway, fx_exposure)
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.markdown("### Market pulse")
    if snapshot is None or snapshot.empty:
        st.info("Market data is unavailable.")
    else:
        st.dataframe(snapshot, use_container_width=True, hide_index=True)

    with st.expander("Risk-engine methodology"):
        st.markdown("""
The score is a transparent management heuristic, not a regulatory capital model.
Market movements contribute according to absolute daily percentage changes;
liquidity contributes according to cash runway; FX exposure contributes according
to its Naira-equivalent magnitude. Thresholds should be calibrated to an
organisation's risk appetite, balance sheet and regulatory framework before
production use.
""")
