import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# PAGE CONFIG
st.set_page_config(
    page_title="NG Finance Pro",
    page_icon="📈",
    layout="wide"
)

# SIDEBAR
st.sidebar.title("📈 NG Finance Pro")
st.subheader(f"Live Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Markets",
        "AI Insights",
        "Risk Monitor",
        "News Terminal"
    ]
)

st.sidebar.markdown("---")

st.sidebar.subheader("⚡ System Status")
st.sidebar.success("Market Feed Active")

# TITLE
st.title("📊 NG Finance Pro Dashboard")
st.subheader("Real-Time Nigerian Financial Intelligence Platform")

# DOWNLOAD DATA
usdngn = yf.download("NGN=X", period="1mo")
btc = yf.download("BTC-USD", period="1mo")
gold = yf.download("GC=F", period="1mo")

# CLEAN DATA
usd_close_series = usdngn["Close"].squeeze()
btc_close_series = btc["Close"].squeeze()
gold_close_series = gold["Close"].squeeze()

# LATEST VALUES
usd_close = float(usd_close_series.iloc[-1])
btc_close = float(btc_close_series.iloc[-1])
gold_close = float(gold_close_series.iloc[-1])

# WATCHLIST CARDS
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "USD/NGN",
        f"{usd_close:.2f}",
        "+0.95"
    )

with col2:
    st.metric(
        "BTC/USD",
        f"{btc_close:.2f}",
        "Crypto"
    )

with col3:
    st.metric(
        "Gold",
        f"{gold_close:.2f}",
        "Commodity"
    )

# AI INSIGHTS
st.markdown("---")

st.subheader("🧠 AI Market Insight")

if usd_close > 1370:
    st.warning(
        "Naira pressure remains elevated. FX volatility continues to impact market stability."
    )
else:
    st.success(
        "USD/NGN remains relatively stable in the short term."
    )

# MARKET CHART
st.markdown("---")

st.subheader("📈 USD/NGN Market Trend")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=usdngn.index,
        y=usd_close_series,
        mode="lines",
        name="USD/NGN",
        line=dict(color="cyan", width=3)
    )
)

fig.update_layout(
    template="plotly_dark",
    height=500,
    title="USD/NGN Exchange Rate Trend",
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117",
    font=dict(color="white")
)

st.plotly_chart(fig, use_container_width=True)

# MARKET TABLE
st.markdown("---")

st.subheader("📋 Latest Market Data")

st.dataframe(usdngn.tail())

# NEWS TERMINAL
st.markdown("---")

st.subheader("📰 Market News")

news_data = pd.DataFrame({
    "Headline": [
        "CBN Maintains Monetary Tightening Policy",
        "Oil Prices Show Increased Volatility",
        "Naira Faces Continued FX Pressure",
        "Bitcoin Holds Above Key Resistance",
        "Global Markets Mixed Amid Inflation Concerns"
    ],
    "Category": [
        "Nigeria",
        "Commodities",
        "FX",
        "Crypto",
        "Global"
    ]
})

st.table(news_data)

# RISK MONITOR
st.markdown("---")

st.subheader("⚠️ Risk Monitor")

risk_data = pd.DataFrame({
    "Risk Factor": [
        "FX Volatility",
        "Inflation Pressure",
        "Oil Market Risk",
        "Crypto Volatility",
        "Interest Rate Risk"
    ],
    "Status": [
        "Moderate",
        "High",
        "Moderate",
        "High",
        "Moderate"
    ]
})

st.table(risk_data)

# FOOTER
st.markdown("---")

st.caption("NG Finance Pro • Nigerian Financial Intelligence Platform")
import pandas as pd
import numpy as np

chart_data = pd.DataFrame(
    np.random.randn(20, 3),
    columns=["USD/NGN", "BTC", "Gold"]
)

st.line_chart(chart_data)