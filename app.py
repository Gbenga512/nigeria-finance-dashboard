import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime
from openai import OpenAI
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
# AUTO REFRESH
# ============================================
st_autorefresh(interval=60000, key="marketrefresh")

# ============================================
# API KEYS
# ============================================
NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
# ============================================
# OPENAI CLIENT
# ============================================
client = OpenAI(api_key=OPENAI_API_KEY)

# ============================================
# FUNCTIONS
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
        close = df["Close"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        return pd.Series(close).dropna()

    except:
        return pd.Series(dtype=float)


def latest_price(series):

    try:
        return round(float(series.iloc[-1]), 2)

    except:
        return 0


def pct_change(series):

    try:
        return round(
            ((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 100,
            2
        )

    except:
        return 0


@st.cache_data(ttl=600)
def fetch_news():

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=Nigeria finance OR cryptocurrency OR oil market&"
        f"sortBy=publishedAt&"
        f"language=en&"
        f"apiKey={NEWS_API_KEY}"
    )

    try:

        response = requests.get(url)

        if response.status_code == 200:

            data = response.json()

            articles = []

            for article in data["articles"][:10]:

                articles.append({
                    "Headline": article["title"],
                    "Source": article["source"]["name"],
                    "Published": article["publishedAt"][:10]
                })

            return pd.DataFrame(articles)

        return pd.DataFrame()

    except:
        return pd.DataFrame()


def generate_ai_insight(
    usd_price,
    btc_price,
    eth_price,
    gold_price,
    oil_price
):

    prompt = f"""
    Analyze these market conditions professionally:

    USD/NGN: {usd_price}
    Bitcoin: {btc_price}
    Ethereum: {eth_price}
    Gold: {gold_price}
    Crude Oil: {oil_price}

    Give a short financial market insight
    focused on Nigeria, inflation,
    FX pressure, crypto, and commodities.
    """

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI Error: {str(e)}"


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
# PRICES
# ============================================
usd_price = latest_price(usdngn_close)
btc_price = latest_price(btc_close)
eth_price = latest_price(eth_close)
gold_price = latest_price(gold_close)
oil_price = latest_price(oil_close)

# ============================================
# DASHBOARD
# ============================================
if page == "Dashboard":

    st.title("📊 NG Finance Pro Dashboard")

    st.subheader(
        "AI-Powered Nigerian Financial Intelligence Platform"
    )

    # ========================================
    # METRICS
    # ========================================
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "USD/NGN",
            usd_price,
            f"{pct_change(usdngn_close)}%"
        )

    with col2:
        st.metric(
            "BTC/USD",
            btc_price,
            f"{pct_change(btc_close)}%"
        )

    with col3:
        st.metric(
            "ETH/USD",
            eth_price,
            f"{pct_change(eth_close)}%"
        )

    with col4:
        st.metric(
            "Gold",
            gold_price,
            f"{pct_change(gold_close)}%"
        )

    with col5:
        st.metric(
            "Crude Oil",
            oil_price,
            f"{pct_change(oil_close)}%"
        )

    st.markdown("---")

    # ========================================
    # WATCHLIST
    # ========================================
    st.subheader("📌 Market Watchlist")

    watchlist = pd.DataFrame({
        "Asset": [
            "USD/NGN",
            "BTC/USD",
            "ETH/USD",
            "Gold",
            "Crude Oil"
        ],
        "Price": [
            usd_price,
            btc_price,
            eth_price,
            gold_price,
            oil_price
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

    # ========================================
    # AI INSIGHT
    # ========================================
    st.subheader("🧠 GPT Market Intelligence")

    ai_summary = generate_ai_insight(
        usd_price,
        btc_price,
        eth_price,
        gold_price,
        oil_price
    )

    st.info(ai_summary)

    st.markdown("---")

    # ========================================
    # CHART
    # ========================================
    st.subheader("📈 USD/NGN Trend")

    if not usdngn_close.empty:

        chart_df = pd.DataFrame({
            "Date": pd.to_datetime(usdngn_close.index),
            "Price": usdngn_close.values
        })

        chart_df = chart_df.dropna()

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=chart_df["Date"],
                y=chart_df["Price"],
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

    if not selected_series.empty:

        chart_df = pd.DataFrame({
            "Date": pd.to_datetime(selected_series.index),
            "Price": selected_series.values
        })

        chart_df = chart_df.dropna()

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=chart_df["Date"],
                y=chart_df["Price"],
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

# ============================================
# AI INSIGHTS PAGE
# ============================================
elif page == "AI Insights":

    st.title("🤖 AI Financial Insights")

    ai_page_summary = generate_ai_insight(
        usd_price,
        btc_price,
        eth_price,
        gold_price,
        oil_price
    )

    st.success(ai_page_summary)

# ============================================
# RISK MONITOR
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
# NEWS TERMINAL
# ============================================
elif page == "News Terminal":

    st.title("📰 Live Financial News")

    news_df = fetch_news()

    if not news_df.empty:

        st.dataframe(
            news_df,
            use_container_width=True
        )

    else:
        st.warning(
            "Unable to load live news."
        )

# ============================================
# FOOTER
# ============================================
st.markdown("---")

st.caption(
    "NG Finance Pro • AI Financial Intelligence Platform"
)
