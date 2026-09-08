import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.market_data import close_series, fetch_market_data


def render(asset_symbols: dict):
    st.title("📑 Markets Overview")
    selected = st.selectbox("Select Asset", list(asset_symbols))
    series = close_series(fetch_market_data(asset_symbols[selected]))
    if series.empty:
        st.warning("Market data is unavailable for this asset right now.")
        return

    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", name=selected))
    fig.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent observations")
    recent = pd.DataFrame({"Date": series.index, "Price": series.values}).tail(10).sort_values("Date", ascending=False)
    st.dataframe(recent, use_container_width=True, hide_index=True)
