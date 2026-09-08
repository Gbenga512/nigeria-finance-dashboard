import pandas as pd
import yfinance as yf
import streamlit as st

from config.settings import DEFAULT_PERIOD, MARKET_CACHE_TTL, MARKET_SYMBOLS


@st.cache_data(ttl=MARKET_CACHE_TTL, show_spinner=False)
def fetch_market_data(symbol: str, period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    try:
        data = yf.download(symbol, period=period, progress=False, auto_adjust=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data.dropna(how="all")
    except Exception:
        return pd.DataFrame()


def close_series(data: pd.DataFrame) -> pd.Series:
    if data.empty or "Close" not in data.columns:
        return pd.Series(dtype="float64")
    series = pd.to_numeric(data["Close"], errors="coerce").dropna()
    return series


def latest_price(series: pd.Series):
    return round(float(series.iloc[-1]), 2) if not series.empty else None


def daily_change_pct(series: pd.Series):
    if len(series) < 2 or series.iloc[-2] == 0:
        return None
    return round(float((series.iloc[-1] / series.iloc[-2] - 1) * 100), 2)


def market_snapshot() -> pd.DataFrame:
    rows = []
    for name, symbol in MARKET_SYMBOLS.items():
        series = close_series(fetch_market_data(symbol))
        rows.append({
            "Asset": name,
            "Price": latest_price(series),
            "Change %": daily_change_pct(series),
            "Data": "Live" if not series.empty else "Unavailable",
        })
    return pd.DataFrame(rows)
