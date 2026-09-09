import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ng_ui import hero


def render(snapshot: pd.DataFrame):
    hero("Risk Centre", "A market-risk cockpit designed to surface volatility and prioritize management attention.", "Risk monitoring")
    if snapshot.empty:
        st.warning("Risk inputs are currently unavailable.")
        return
    rows = []
    for _, row in snapshot.iterrows():
        change = row.get("Change %")
        if pd.isna(change):
            level, score = "Unknown", 0
        elif abs(float(change)) >= 3:
            level, score = "High", 80
        elif abs(float(change)) >= 1:
            level, score = "Moderate", 50
        else:
            level, score = "Low", 20
        rows.append({"Risk Factor": f"{row['Asset']} volatility", "Risk Level": level, "Daily Change %": change, "Risk Score": score})
    risk = pd.DataFrame(rows)
    high = int((risk["Risk Level"] == "High").sum())
    moderate = int((risk["Risk Level"] == "Moderate").sum())
    low = int((risk["Risk Level"] == "Low").sum())
    avg_score = float(risk["Risk Score"].mean())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio risk score", f"{avg_score:.0f}/100")
    c2.metric("High risk", high)
    c3.metric("Moderate", moderate)
    c4.metric("Low", low)
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        chart = risk.sort_values("Risk Score", ascending=True)
        fig = go.Figure(go.Bar(x=chart["Risk Score"], y=chart["Risk Factor"], orientation="h", text=chart["Risk Score"], textposition="outside"))
        fig.update_layout(height=340, margin=dict(l=10, r=35, t=15, b=10), xaxis_title="Risk score", yaxis_title=None, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Management signal")
        if high:
            st.error(f"{high} market factor(s) require immediate review.")
        elif moderate:
            st.warning(f"{moderate} factor(s) are showing elevated volatility.")
        else:
            st.success("No elevated market-volatility signal detected.")
        st.caption("Current release focuses on market volatility. Credit, liquidity, operational and macroeconomic risk modules can be layered in later.")
    st.markdown("### Risk register")
    st.dataframe(risk, use_container_width=True, hide_index=True)
