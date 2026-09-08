import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.market_data import close_series, fetch_market_data
from ui import hero


def render(asset_symbols: dict):
    hero(
        "Markets Terminal",
        "Track selected instruments with a clean price history and recent observations.",
        "Live market feed",
    )

    selected = st.selectbox("Instrument", list(asset_symbols), label_visibility="collapsed")
    series = close_series(fetch_market_data(asset_symbols[selected]))
    if series.empty:
        st.warning("Market data is unavailable for this asset right now.")
        return

    current = float(series.iloc[-1])
    previous = float(series.iloc[-2]) if len(series) > 1 else current
    change = ((current - previous) / previous * 100) if previous else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Last price", f"{current:,.2f}")
    c2.metric("Latest move", f"{change:+.2f}%")
    c3.metric("Observations", f"{len(series):,}")

    fig = go.Figure(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            name=selected,
            hovertemplate="%{x|%d %b %Y}: %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Recent observations")
    recent = pd.DataFrame({"Date": series.index, "Price": series.values}).tail(10).sort_values("Date", ascending=False)
    recent["Price"] = recent["Price"].map(lambda x: f"{x:,.2f}")
    st.dataframe(recent, use_container_width=True, hide_index=True)
