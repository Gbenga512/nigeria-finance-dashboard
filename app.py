import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="NG Finance Pro",
    page_icon="📈",
    layout="wide"
)

# ============================================
# AUTO REFRESH EVERY 60 SECONDS
# ============================================
st_autorefresh(interval=60000, key="marketrefresh")

# ============================================
# HELPERS
# ============================================
@st.cache_data(ttl=300)
def fetch_data(symbol):

    try:
        df = yf.download(
            symbol,
            period="30d",
            progress=False
        )

        if df.empty:
            return pd.DataFrame()

        return df

    except:
        return pd.DataFrame()


def get_close(df):

    try:
        return pd.Series(df["Close"].squeeze()).dropna()

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


# ============================================
# SIDEBAR
# ============================================
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
st.sidebar.success("🟢 Market Feed Active")

st.sidebar.write(
    f"Last Refresh: {datetime.now().strftime('%H:%M:%S')}"
)

# ============================================
# FETCH MARKET DATA
# ============================================
usdngn = fetch_data("NGN=X")
btc = fetch_data("BTC-USD")
eth = fetch_data("ETH-USD")
gold = fetch_data("GC=F")
oil = fetch_data("CL=F")

usdngn_close = get_close(usdngn)
btc_close = get_close(btc)
eth_close = get_close(eth)
gold_close = get_close(gold)
oil_close = get_close(oil)

# ============================================
# DASHBOARD PAGE
# ============================================
if page == "Dashboard":

    st.title("📊 NG Finance Pro Dashboard")

    st.subheader(
        "Real-Time Nigerian Financial Intelligence Platform"
    )

    # ============================
    # METRICS
    # ============================
    col1, col2, col3, col4, col5 = st.columns(5)

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
            "ETH/USD",
            latest_price(eth_close),
            f"{pct_change(eth_close)}%"
        )

    with col4:
        st.metric(
            "Gold",
            latest_price(gold_close),
            f"{pct_change(gold_close)}%"
        )

    with col5:
        st.metric(
            "Crude Oil",
            latest_price(oil_close),
            f"{pct_change(oil_close)}%"
        )

    st.markdown("---")

    # ============================
    # WATCHLIST
    # ============================
    st.markdown("## 📌 Market Watchlist")

    watchlist = pd.DataFrame({
        "Asset": [
            "USD/NGN",
            "BTC/USD",
            "ETH/USD",
            "Gold",
            "Crude Oil"
        ],
        "Price": [
            latest_price(usdngn_close),
            latest_price(btc_close),
            latest_price(eth_close),
            latest_price(gold_close),
            latest_price(oil_close)
        ],
        "Change %": [
            pct_change(usdngn_close),
            pct_change(btc_close),
            pct_change(eth_close),
            pct_change(gold_close),
            pct_change(oil_close)
        ]
    })

    st.dataframe(
        watchlist,
        use_container_width=True
    )

    st.markdown("---")

    # ============================
    # AI INSIGHT
    # ============================
    st.subheader("🧠 AI Market Insight")

    st.info(
        "Naira volatility remains elevated amid continued FX demand pressure. "
        "Bitcoin momentum remains positive while oil market uncertainty "
        "continues to influence inflation expectations."
    )

    st.markdown("---")

    # ============================
    # USD/NGN CHART
    # ============================
    st.subheader("📈 USD/NGN Trend")

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

        fig.update_layout(
            template="plotly_dark",
            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

# ============================================
# MARKETS PAGE
# ============================================
elif page == "Markets":

    st.title("📑 Markets Overview")

    assets = {
        "USD/NGN": usdngn_close,
        "BTC/USD": btc_close,
        "ETH/USD": eth_close,
        "Gold": gold_close,
        "Crude Oil": oil_close
    }

    selected_asset = st.selectbox(
        "Select Asset",
        list(assets.keys())
    )

    selected_series = assets[selected_asset]

    # ============================
    # MARKET CHART
    # ============================
    if not selected_series.empty:

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=selected_series.index,
                y=selected_series.values,
                mode="lines+markers",
                name=selected_asset
            )
        )

        fig.update_layout(
            template="plotly_dark",
            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ============================
        # STATISTICS
        # ============================
        stats_df = pd.DataFrame({
            "Metric": [
                "Latest Price",
                "Highest Price",
                "Lowest Price",
                "Average Price"
            ],
            "Value": [
                latest_price(selected_series),
                round(selected_series.max(), 2),
                round(selected_series.min(), 2),
                round(selected_series.mean(), 2)
            ]
        })

        st.dataframe(
            stats_df,
            use_container_width=True
        )

# ============================================
# AI INSIGHTS PAGE
# ============================================
elif page == "AI Insights":

    st.title("🤖 AI Financial Insights")

    st.success(
        "AI detects continued FX instability within the Nigerian market."
    )

    st.warning(
        "Oil market volatility may continue influencing inflation."
    )

    st.info(
        "Crypto assets remain highly sensitive to global macroeconomic conditions."
    )

# ============================================
# RISK MONITOR PAGE
# ============================================
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
        "Risk Level": [
            "High",
            "High",
            "Moderate",
            "High",
            "Moderate"
        ]
    })

    st.dataframe(
        risk_data,
        use_container_width=True
    )

# ============================================
# NEWS PAGE
# ============================================
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

    st.dataframe(
        news_data,
        use_container_width=True
    )

# ============================================
# FOOTER
# ============================================
st.markdown("---")

st.caption(
    "NG Finance Pro • Nigerian Financial Intelligence Platform"
)