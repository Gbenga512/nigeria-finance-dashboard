import os

APP_NAME = "NG Finance Pro"
DEFAULT_PERIOD = "30d"
MARKET_CACHE_TTL = 300
NEWS_CACHE_TTL = 600
RECONCILIATION_DATE_TOLERANCE_DAYS = 3

MARKET_SYMBOLS = {
    "USD/NGN": "NGN=X",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "Gold": "GC=F",
    "Crude Oil": "CL=F",
}

NEWS_QUERY = "Nigeria finance OR Nigeria economy OR oil market OR cryptocurrency"


def get_secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)
