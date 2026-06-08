import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
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
# AUTO REFRESH
# ============================================
st_autorefresh(interval=60000, key="marketrefresh")

# ============================================
# API KEYS
# ============================================
NEWS_API_KEY = st.secrets["NEWS_API_KEY"]

# ============================================
# FUNCTIONS
# ============================================
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
        return round(((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 100, 2)
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
    try:
        return f"""
📊 Market Summary

USD/NGN: {usd_price}
Bitcoin: {btc_price}
Ethereum: {eth_price}
Gold: {gold_price}
Crude Oil: {oil_price}

Nigeria's financial markets remain sensitive to exchange-rate movements, inflation pressures, commodity prices and cryptocurrency volatility.

Key Observations:
• USD/NGN remains an important indicator of foreign exchange pressure.
• Bitcoin and Ethereum continue to experience significant price volatility.
• Gold remains a traditional safe-haven asset.
• Crude oil prices have a direct impact on Nigeria's revenue outlook.
• Inflation and monetary policy decisions remain key market drivers.

Investment Note:
Monitor exchange rates, commodity prices and macroeconomic developments before making investment decisions.
"""
    except Exception as e:
        return f"AI Error: {str(e)}"


st.sidebar.title("📈 NG Finance Pro")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Markets", "AI Insights", "Risk Monitor", "News Terminal", "Treasury Dashboard", "Bank Reconciliation", "Budget Analysis"]
)

st.sidebar.markdown("---")
st.sidebar.success("🟢 Market Feed Active")
st.sidebar.write(f"Last Refresh: {datetime.now().strftime('%H:%M:%S')}")

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

usd_price = latest_price(usdngn_close)
btc_price = latest_price(btc_close)
eth_price = latest_price(eth_close)
gold_price = latest_price(gold_close)
oil_price = latest_price(oil_close)

if page == "Dashboard":
    st.title("📊 NG Finance Pro Dashboard")
    st.subheader("AI-Powered Nigerian Financial Intelligence Platform")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("USD/NGN", usd_price, f"{pct_change(usdngn_close)}%")
    with col2:
        st.metric("BTC/USD", btc_price, f"{pct_change(btc_close)}%")
    with col3:
        st.metric("ETH/USD", eth_price, f"{pct_change(eth_close)}%")
    with col4:
        st.metric("Gold", gold_price, f"{pct_change(gold_close)}%")
    with col5:
        st.metric("Crude Oil", oil_price, f"{pct_change(oil_close)}%")

    st.markdown("---")
    st.subheader("📌 Market Watchlist")

    watchlist = pd.DataFrame({
        "Asset": ["USD/NGN", "BTC/USD", "ETH/USD", "Gold", "Crude Oil"],
        "Price": [usd_price, btc_price, eth_price, gold_price, oil_price],
        "Change %": [
            pct_change(usdngn_close),
            pct_change(btc_close),
            pct_change(eth_close),
            pct_change(gold_close),
            pct_change(oil_close)
        ]
    })

    st.dataframe(watchlist, width="stretch")

    st.markdown("---")
    st.subheader("🧠 Market Intelligence")
    st.info(generate_ai_insight(
        usd_price, btc_price, eth_price, gold_price, oil_price
    ))

elif page == "Markets":
    st.title("📑 Markets Overview")

    assets = {
        "USD/NGN": usdngn_close,
        "BTC/USD": btc_close,
        "ETH/USD": eth_close,
        "Gold": gold_close,
        "Crude Oil": oil_close
    }

    selected_asset = st.selectbox("Select Asset", list(assets.keys()))
    selected_series = assets[selected_asset]

    if not selected_series.empty:
        chart_df = pd.DataFrame({
            "Date": pd.to_datetime(selected_series.index),
            "Price": selected_series.values
        })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_df["Date"],
            y=chart_df["Price"],
            mode="lines+markers",
            name=selected_asset
        ))
        fig.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig, width="stretch")

elif page == "AI Insights":
    st.title("🤖 AI Financial Insights")
    st.success(generate_ai_insight(
        usd_price, btc_price, eth_price, gold_price, oil_price
    ))

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

    st.dataframe(risk_data, width="stretch")

elif page == "News Terminal":
    st.title("📰 Live Financial News")

    news_df = fetch_news()

    if not news_df.empty:
        st.dataframe(news_df, width="stretch")
    else:
        st.warning("Unable to load live news.")
elif page == "Treasury Dashboard":

    st.title("🏦 Treasury Dashboard")

    cash_position = 250000000
    outstanding_cheques = 12000000
    unreconciled_items = 15

    col1, col2, col3 = st.columns(3)

    col1.metric("Cash Position", f"₦{cash_position:,.0f}")
    col2.metric("Outstanding Cheques", f"₦{outstanding_cheques:,.0f}")
    col3.metric("Unreconciled Items", unreconciled_items)

    treasury_data = pd.DataFrame({
        "Metric": [
            "Cash Position",
            "Outstanding Cheques",
            "Unpresented Deposits",
            "Unreconciled Transactions"
        ],
        "Amount": [
            250000000,
            12000000,
            5000000,
            3500000
        ]
    })
    st.dataframe(treasury_data)

elif page == "Bank Reconciliation":
    st.title("🏦 Bank Reconciliation")
    bank_file = st.file_uploader(
        "Upload Bank Statement",
        type=["xlsx", "csv"]
    )

    cashbook_file = st.file_uploader(
        "Upload Cashbook",
        type=["xlsx", "csv"]
    )

    if bank_file and cashbook_file:

        st.success("Files uploaded successfully")

    if bank_file.name.endswith(".csv"):
       bank_df = pd.read_csv(bank_file)
else:
       bank_df = pd.read_excel(bank_file)

if cashbook_file.name.endswith(".csv"):
    cashbook_df = pd.read_csv(cashbook_file)
else:
    cashbook_df = pd.read_excel(cashbook_file)

    st.subheader("Bank Statement")
    st.dataframe(bank_df.head())

    st.subheader("Cashbook")
    st.dataframe(cashbook_df.head())
   
 elif page == "Budget Analysis":
    st.title("📊 Budget vs Actual Analysis")
    budget = pd.DataFrame({
        "Department": ["Finance", "HR", "Operations"],
        "Budget": [5000000, 3000000, 8000000],
        "Actual": [4500000, 3500000, 7600000]
    })

    budget["Variance"] = (
        budget["Actual"] - budget["Budget"]
    )

    st.dataframe(budget)

    st.bar_chart(
        budget.set_index("Department")[["Budget", "Actual"]]
    )
st.markdown("---")
st.caption("NG Finance Pro • AI Financial Intelligence Platform")
