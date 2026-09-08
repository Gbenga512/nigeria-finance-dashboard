import os

import pandas as pd
import requests
import streamlit as st

from config.settings import NEWS_CACHE_TTL, NEWS_QUERY, get_secret


@st.cache_data(ttl=NEWS_CACHE_TTL, show_spinner=False)
def fetch_news(limit: int = 10) -> pd.DataFrame:
    """Fetch live news when NEWS_API_KEY is configured.

    Without a key, return an empty frame so the application remains fully usable.
    """
    api_key = get_secret("NEWS_API_KEY")
    if not api_key:
        return pd.DataFrame()

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": NEWS_QUERY,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": limit,
                "apiKey": api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return pd.DataFrame([
            {
                "Headline": a.get("title", "Untitled"),
                "Source": (a.get("source") or {}).get("name", "Unknown"),
                "Published": (a.get("publishedAt") or "")[:10],
                "URL": a.get("url", ""),
            }
            for a in articles
        ])
    except (requests.RequestException, ValueError, TypeError):
        return pd.DataFrame()
