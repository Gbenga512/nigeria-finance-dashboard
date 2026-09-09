import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from analytics.intelligence import build_market_intelligence, management_summary
from ng_ui import hero


def render(snapshot: pd.DataFrame):
    intelligence = build_market_intelligence(snapshot)
    hero(
        "Intelligence Centre",
        "Explainable signals that turn market data into management attention, priorities and actions.",
        "Decision-support engine",
    )

    score = intelligence["score"]
    breadth = intelligence["breadth"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attention score", "N/A" if score is None else f"{score}/100")
    c2.metric("Gainers", breadth["gainers"])
    c3.metric("Decliners", breadth["decliners"])
    c4.metric("Priority alerts", len(intelligence["alerts"]))

    st.markdown("### Executive signal")
    if intelligence["overall"] == "High attention":
        st.error(management_summary(intelligence))
    elif intelligence["overall"] == "Elevated":
        st.warning(management_summary(intelligence))
    elif score is None:
        st.info(management_summary(intelligence))
    else:
        st.success(management_summary(intelligence))

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown("### Signal map")
        movers = intelligence["movers"]
        if movers.empty:
            st.info("No market movements are currently available.")
        else:
            chart = movers.sort_values("Change %")
            fig = go.Figure(go.Bar(
                x=chart["Change %"],
                y=chart["Asset"],
                orientation="h",
                text=chart["Change %"].map(lambda x: f"{x:+.2f}%"),
                textposition="outside",
                hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
            ))
            fig.update_layout(
                height=360,
                margin=dict(l=10, r=45, t=10, b=10),
                xaxis_title="Daily movement (%)",
                yaxis_title=None,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        st.markdown("### Decision priorities")
        if not intelligence["alerts"]:
            st.success("No priority market alerts.")
        for alert in intelligence["alerts"]:
            if alert["Severity"] == "High":
                st.error(f"**HIGH • {alert['Area']}**  \n{alert['Signal']}")
            else:
                st.warning(f"**MODERATE • {alert['Area']}**  \n{alert['Signal']}")

    st.markdown("### Management action centre")
    actions = [
        ("01", "Review material movements", "Investigate any High or Moderate market signals against current exposures."),
        ("02", "Check liquidity sensitivity", "Assess whether FX, commodity or crypto movements could affect near-term cash requirements."),
        ("03", "Validate source records", "Before acting, reconcile relevant internal balances and confirm the market data context."),
        ("04", "Document management response", "Record the issue, owner, decision and follow-up date for governance and auditability."),
    ]
    for number, title, copy in actions:
        st.markdown(
            f"<div class='ng-card' style='margin-bottom:9px'><div class='ng-card-title'>{number} • {title.upper()}</div><div style='margin-top:5px;color:#c3cfdd'>{copy}</div></div>",
            unsafe_allow_html=True,
        )

    st.caption("The Intelligence Centre currently uses transparent rule-based thresholds. It is decision support, not investment advice.")
