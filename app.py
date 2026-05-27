import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="NG Finance Pro",
    page_icon="📈",
    layout="wide"
)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("📈 NG Finance Pro")

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

# =========================
# LIVE TIME
# =========================
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# DOWNLOAD REAL MARKET DATA
# =========================
usdngn = yf.download("NGN=X", period="5d", interval="1d")
btc = yf.download("BTC-USD", period="5d", interval="1d")
gold = yf.download("GC=F", period="5d", interval="1d")

# =========================
# SAFE DATA EXTRACTION
# =========================
usdngn_close = usdngn["Close"].squeeze()
btc_close = btc["Close"].squeeze()
gold_close = gold["Close"].squeeze()

usdngn_price = round(float(usdngn_close.iloc[-1]), 2)
btc_price = round(float(btc_close.iloc[-1]), 2)
gold_price = round(float(gold_close.iloc[-1]), 2)

# =========================
# DASHBOARD PAGE
# =========================
if page == "Dashboard":

    st.markdown(f"## Live Time: {current_time}")

    st.title("📊 NG Finance Pro Dashboard")
    st.subheader("Real-Time Nigerian Financial Intelligence Platform")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="USD/NGN",
            value=usdngn_price,
            delta="+0.95"
        )

    with col2:
        st.metric(
            label="BTC/USD",
            value=btc_price,
            delta="Crypto"
        )

    with col3:
        st.metric(
            label="Gold",
            value=gold_price,
            delta="Commodity"
        )

    st.markdown("---")

    st.subheader("🧠 AI Market Insight")

    st.info(
        "Naira pressure remains elevated. FX volatility continues to impact market stability."
    )

    st.markdown("---")

    st.subheader("📈 USD/NGN Market Trend")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=usdngn.index,
            y=usdngn_close,
            mode="lines+markers",
            name="USD/NGN"
        )
    )

    fig.update_layout(
        height=500,
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Exchange Rate"
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# MARKETS PAGE
# =========================
elif page == "Markets":

    st.title("📑 Latest Market Data")

    # Create separate dataframes
    usd_df = pd.DataFrame({
        "Date": usdngn.index,
        "USD/NGN": usdngn_close.values
    })

    btc_df = pd.DataFrame({
        "Date": btc.index,
        "BTC/USD": btc_close.values
    })

    gold_df = pd.DataFrame({
        "Date": gold.index,
        "Gold": gold_close.values
    })

    # Merge all safely
    market_df = usd_df.merge(btc_df, on="Date", how="outer")
    market_df = market_df.merge(gold_df, on="Date", how="outer")

    # Sort dates
    market_df = market_df.sort_values(by="Date")

    st.dataframe(market_df)
# =========================
# AI INSIGHTS PAGE
# =========================
elif page == "AI Insights":

    st.title("🤖 AI Financial Insights")

    st.success(
        "AI analysis indicates increased FX demand pressure and strong crypto momentum."
    )

    st.warning(
        "Oil market volatility may influence Nigerian fiscal performance."
    )

# =========================
# RISK MONITOR PAGE
# =========================
elif page == "Risk Monitor":

    st.title("⚠️ Risk Monitor")

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

# =========================
# NEWS TERMINAL PAGE
# =========================
elif page == "News Terminal":

    st.title("📰 Market News")

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

# =========================
# FOOTER
# =========================
st.markdown("---")
st.caption("NG Finance Pro • Nigerian Financial Intelligence Platform")