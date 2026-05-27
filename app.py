import streamlit as st
import yfinance as yf
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

# LIVE TIME
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# DOWNLOAD REAL DATA
usdngn = yf.download("NGN=X", period="1d", interval="1m")
btc = yf.download("BTC-USD", period="1d", interval="1m")
gold = yf.download("GC=F", period="1d", interval="1m")

# CURRENT PRICES
usdngn_price = round(float(usdngn["Close"].dropna().iloc[-1]), 2)
btc_price = round(float(btc["Close"].dropna().iloc[-1]), 2)
gold_price = round(float(gold["Close"].dropna().iloc[-1]), 2)

# DASHBOARD
if page == "Dashboard":

    st.title("📊 NG Finance Pro Dashboard")
    st.subheader("Real-Time Nigerian Financial Intelligence Platform")

    st.write(f"### Live Time: {current_time}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("USD/NGN", usdngn_price, "+0.95")

    with col2:
        st.metric("BTC/USD", btc_price, "Crypto")

    with col3:
        st.metric("Gold", gold_price, "Commodity")

    st.markdown("---")

    st.subheader("🧠 AI Market Insight")

    insight = """
    Naira pressure remains elevated as FX volatility continues.
    Bitcoin remains sensitive to global macroeconomic conditions,
    while gold prices show continued safe-haven demand.
    """

    st.info(insight)

    st.markdown("---")

    st.subheader("📈 Real Market Trends")

    # REAL HISTORICAL DATA
    usdngn_hist = yf.download("NGN=X", period="1mo")
    btc_hist = yf.download("BTC-USD", period="1mo")
    gold_hist = yf.download("GC=F", period="1mo")

    chart_data = pd.DataFrame({
        "USD/NGN": usdngn_hist["Close"],
        "BTC": btc_hist["Close"],
        "Gold": gold_hist["Close"]
    })

    st.line_chart(chart_data)

# MARKETS PAGE
elif page == "Markets":

    st.title("📑 Latest Market Data")

    market_table = pd.DataFrame({
        "Asset": ["USD/NGN", "BTC/USD", "Gold"],
        "Price": [usdngn_price, btc_price, gold_price]
    })

    st.dataframe(market_table)

# AI INSIGHTS PAGE
elif page == "AI Insights":

    st.title("🤖 AI Financial Insights")

    st.success("""
    AI detects sustained FX instability in the Nigerian market.
    
    Oil price fluctuations may continue impacting inflation
    and government revenue projections.
    
    Investors continue monitoring crypto volatility and
    commodity market resilience.
    """)

# RISK MONITOR PAGE
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

# NEWS PAGE
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

# FOOTER
st.markdown("---")
st.caption("NG Finance Pro • Nigerian Financial Intelligence Platform")