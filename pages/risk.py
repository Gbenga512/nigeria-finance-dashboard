import pandas as pd
import streamlit as st


def render(snapshot: pd.DataFrame):
    st.title("⚠️ Risk Monitor")
    rows = []
    for _, row in snapshot.iterrows():
        change = row.get("Change %")
        if pd.isna(change):
            level = "Unknown"
        elif abs(float(change)) >= 3:
            level = "High"
        elif abs(float(change)) >= 1:
            level = "Moderate"
        else:
            level = "Low"
        rows.append({"Risk Factor": f"{row['Asset']} volatility", "Risk Level": level, "Daily Change %": change})

    risk = pd.DataFrame(rows)
    st.dataframe(risk, use_container_width=True, hide_index=True)
    st.caption("This is a market-volatility indicator, not a full enterprise risk assessment. Add inflation, rates, credit, liquidity and operational risk feeds in the next release.")
