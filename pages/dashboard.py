import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui import hero


def render(snapshot: pd.DataFrame, insight: str):
    hero(
        "Executive Dashboard",
        "A concise view of market conditions and analyst context for finance, treasury and management decisions.",
        "Live market feed",
    )

    if snapshot.empty:
        st.warning("Market data is temporarily unavailable. Please refresh shortly.")
        return

    # Executive KPI cards. On mobile Streamlit stacks these cleanly rather than
    # forcing the five-card desktop layout into a cramped viewport.
    cols = st.columns(5, gap="small")
    for col, (_, row) in zip(cols, snapshot.iterrows()):
        price = row["Price"]
        change = row["Change %"]
        with col:
            st.metric(
                row["Asset"],
                "N/A" if pd.isna(price) else f"{price:,.2f}",
                None if pd.isna(change) else f"{change:+.2f}%",
            )

    st.markdown("### Market overview")
    left, right = st.columns([1.7, 1], gap="large")

    with left:
        chart_df = snapshot.dropna(subset=["Change %"]).copy()
        chart_df = chart_df.sort_values("Change %")
        fig = go.Figure(
            go.Bar(
                x=chart_df["Change %"],
                y=chart_df["Asset"],
                orientation="h",
                text=chart_df["Change %"].map(lambda x: f"{x:+.2f}%"),
                textposition="outside",
                hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
            )
        )
        fig.update_layout(
            height=330,
            margin=dict(l=10, r=35, t=10, b=10),
            xaxis_title="Daily change (%)",
            yaxis_title=None,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        st.markdown("#### Market pulse")
        up = int((snapshot["Change %"] > 0).sum())
        down = int((snapshot["Change %"] < 0).sum())
        flat = int((snapshot["Change %"] == 0).sum())
        st.metric("Positive assets", up)
        st.metric("Negative assets", down)
        st.metric("Flat / unchanged", flat)

    st.markdown("### Market watchlist")
    display = snapshot.copy()
    display["Price"] = display["Price"].map(lambda x: "N/A" if pd.isna(x) else f"{x:,.2f}")
    display["Change %"] = display["Change %"].map(lambda x: "N/A" if pd.isna(x) else f"{x:+.2f}%")
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("### Analyst intelligence")
    st.info(insight)
    st.caption("Use this as market context, not as personalized investment advice.")
