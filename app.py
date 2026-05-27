import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
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
# HELPERS
# =========================
@st.cache_data(ttl=300)
def fetch_data(symbol):
    try:
        df = yf.download(symbol, period="30d", progress=False)

        if df.empty:
            return pd.DataFrame()

        return df

    except:
        return pd.DataFrame()


def get_close(df):
    try:
        return df["Close"].dropna()
    except:
        return pd.Series(dtype=float)


def latest_price(series):
    try:
        return round(float(series.iloc[-1]), 2)
    except:
        return None


def pct_change(series):
    try:
        return round(
            ((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 100,
            2
        )
    except:
        return None


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
st.sidebar.success("Market Feed Active")

# =========================
# FETCH MARKET DATA
# =========================
usdngn = fetch_data("NGN=X")
btc = fetch_data("BTC-USD")
gold = fetch_data("GC=F")

usdngn_close = get_close(usdngn)
btc_close = get_close(btc)
gold_close = get_close(gold)

# =========================
# DASHBOARD
# =========================
if page == "Dashboard":

    st.title("📊 NG Finance Pro Dashboard")
    st.subheader("Real-Time Nigerian Financial Intelligence Platform")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "USD/NGN",
            latest_price(usdngn_close),
            f"{pct_change(usdngn_close)}%"
        )

    with col2:
        st.metric(
            "BTC/USD",
            latest_price(btc_close),
            f"{pct_change(btc_close)}%"
        )

    with col3:
        st.metric(
            "Gold",
            latest_price(gold_close),
            f"{pct_change(gold_close)}%"
        )

    st.markdown("---")

    st.subheader("🧠 AI Market Insight")

    st.info(
        "Naira pressure remains elevated. "
        "FX volatility continues to impact market stability."
    )

    st.markdown("---")

    st.subheader("📉 USD/NGN Market Trend")

    if not usdngn_close.empty:

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=usdngn_close.index,
                y=usdngn_close.values,
                mode="lines",
                name="USD/NGN"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("USD/NGN data unavailable.")

# =========================
# MARKETS PAGE
# =========================
elif page == "Markets":

    st.title("📑 Latest Market Data")

    # CREATE INDIVIDUAL DATAFRAMES
    usd_df = pd.DataFrame({
        "Date": usdngn_close.index,
        "USD/NGN": usdngn_close.values
    })

    btc_df = pd.DataFrame({
        "Date": btc_close.index,
        "BTC/USD": btc_close.values
    })

    gold_df = pd.DataFrame({
        "Date": gold_close.index,
        "Gold": gold_close.values
    })

    # MERGE SAFELY
    market_df = usd_df.merge(
        btc_df,
        on="Date",
        how="outer"
    )

    market_df = market_df.merge(
        gold_df,
        on="Date",
        how="outer"
    )

    market_df = market_df.sort_values(by="Date")

    st.dataframe(
        market_df,
        use_container_width=True
    )

# =========================
# AI INSIGHTS
# =========================
elif page == "AI Insights":

    st.title("🧠 AI Financial Insights")

    st.success(
        "AI analysis indicates increased FX demand pressure "
        "and strong crypto momentum."
    )

    st.write(
        "Oil market volatility may influence Nigerian fiscal performance."
    )

# =========================
# RISK MONITOR
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
# NEWS TERMINAL
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

st.caption(
    "NG Finance Pro • Nigerian Financial Intelligence Platform"
)