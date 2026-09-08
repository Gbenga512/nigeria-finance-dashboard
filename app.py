import streamlit as st
from datetime import datetime

from streamlit_autorefresh import st_autorefresh

from config.settings import MARKET_SYMBOLS
from services.market_data import market_snapshot
from services.news_service import fetch_news
from services.ai_service import generate_ai_insight
from pages import dashboard, markets, reconciliation, financial_statements, treasury, budget, risk


st.set_page_config(
    page_title="NG Finance Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("📈 NG Finance Pro")
st.sidebar.caption("Financial Intelligence & Treasury Platform")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Markets",
        "AI Insights",
        "Risk Monitor",
        "News Terminal",
        "Treasury Dashboard",
        "Bank Reconciliation",
        "Budget Analysis",
        "Financial Statement Analyzer",
    ],
)

if page in {"Dashboard", "Markets", "AI Insights", "Risk Monitor", "News Terminal"}:
    st_autorefresh(interval=300000, key="market_refresh")

snapshot = market_snapshot()

st.sidebar.divider()
st.sidebar.success("🟢 Market Feed Active")
st.sidebar.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.caption("Data sources: Yahoo Finance / NewsAPI (when configured)")

if page == "Dashboard":
    insight, _ = generate_ai_insight(snapshot)
    dashboard.render(snapshot, insight)

elif page == "Markets":
    markets.render(MARKET_SYMBOLS)

elif page == "AI Insights":
    st.title("🤖 AI Financial Analyst")
    insight, ai_active = generate_ai_insight(snapshot)
    st.success("OpenAI analysis active") if ai_active else st.info("Rule-based analyst mode active — add OPENAI_API_KEY to enable AI analysis.")
    st.write(insight)
    st.caption("Insights are informational and are not personalized investment advice.")

elif page == "Risk Monitor":
    risk.render(snapshot)

elif page == "News Terminal":
    st.title("📰 Financial News Terminal")
    news = fetch_news(15)
    if news.empty:
        st.warning("Live news is unavailable. Configure NEWS_API_KEY in Streamlit secrets to enable the news feed.")
    else:
        for _, item in news.iterrows():
            headline = item.get("Headline", "Untitled")
            source = item.get("Source", "Unknown")
            published = item.get("Published", "")
            url = item.get("URL", "")
            if url:
                st.markdown(f"**{headline}**  \\n{source} • {published} • [Read article]({url})")
            else:
                st.markdown(f"**{headline}**  \\n{source} • {published}")
            st.divider()

elif page == "Treasury Dashboard":
    treasury.render()

elif page == "Bank Reconciliation":
    reconciliation.render()

elif page == "Budget Analysis":
    budget.render()

elif page == "Financial Statement Analyzer":
    financial_statements.render()

st.divider()
st.caption("NG Finance Pro • Financial Intelligence Platform • MVP v2.1")
