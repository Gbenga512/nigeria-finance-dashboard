import streamlit as st
import pandas as pd


def render(snapshot: pd.DataFrame, insight: str):
    st.title("📊 NG Finance Pro Dashboard")
    st.caption("Financial intelligence for markets, treasury and management decision support")
    cols = st.columns(len(snapshot)) if not snapshot.empty else []
    for col, (_, row) in zip(cols, snapshot.iterrows()):
        price = row["Price"]
        change = row["Change %"]
        with col:
            st.metric(row["Asset"], "N/A" if pd.isna(price) else f"{price:,.2f}", None if pd.isna(change) else f"{change:+.2f}%")

    st.divider()
    st.subheader("Market Watchlist")
    st.dataframe(snapshot, use_container_width=True, hide_index=True)
    st.subheader("Analyst Intelligence")
    st.info(insight)
