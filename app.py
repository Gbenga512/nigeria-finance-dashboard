import streamlit as st
from datetime import datetime

from streamlit_autorefresh import st_autorefresh

from config.settings import MARKET_SYMBOLS
from services.market_data import market_snapshot
from services.news_service import fetch_news
from services.ai_service import generate_ai_insight
from pages import dashboard, markets, reconciliation, financial_statements, treasury, budget, risk, reports, intelligence
from ng_ui import inject_styles, brand, footer


st.set_page_config(
    page_title="NG Finance Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
brand()

st.sidebar.caption("FINANCIAL INTELLIGENCE WORKSPACE")

page = st.sidebar.radio(
    "Workspace",
    [
        "📊  Dashboard",
        "🧠  Intelligence Centre",
        "📈  Markets",
        "🤖  AI Insights",
        "🛡️  Risk Monitor",
        "📰  News Terminal",
        "💧  Treasury Dashboard",
        "↔️  Bank Reconciliation",
        "📑  Budget Analysis",
        "📋  Financial Statement Analyzer",
        "📄  Executive Reports",
    ],
    label_visibility="visible",
)

st.sidebar.markdown(
    """
    <div class="ng-upgrade">
        <div class="ng-upgrade-title">✦ Built for finance teams</div>
        <div class="ng-upgrade-copy">Markets, treasury, risk and accounting intelligence in one workspace.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if page in {"📊  Dashboard", "🧠  Intelligence Centre", "📈  Markets", "🤖  AI Insights", "🛡️  Risk Monitor", "📰  News Terminal", "📄  Executive Reports"}:
    st_autorefresh(interval=300000, key="market_refresh")

snapshot = market_snapshot()

st.sidebar.divider()
st.sidebar.markdown('<span class="ng-status">● LIVE DATA</span>', unsafe_allow_html=True)
st.sidebar.caption(f"Updated {datetime.now().strftime('%d %b %Y • %H:%M')}")
st.sidebar.caption("Yahoo Finance • AI/news integrations optional")

if page == "📊  Dashboard":
    insight, _ = generate_ai_insight(snapshot)
    dashboard.render(snapshot, insight)

elif page == "🧠  Intelligence Centre":
    intelligence.render(snapshot)

elif page == "📈  Markets":
    markets.render(MARKET_SYMBOLS)

elif page == "🤖  AI Insights":
    st.title("AI Financial Analyst")
    st.caption("Decision-support context generated from the available market dataset.")
    insight, ai_active = generate_ai_insight(snapshot)
    if ai_active:
        st.success("Enhanced AI analysis active")
    else:
        st.info("Free analyst mode active — no OPENAI_API_KEY is required.")
    st.markdown(insight)
    st.caption("Insights are informational and are not personalized investment advice.")

elif page == "🛡️  Risk Monitor":
    risk.render(snapshot)

elif page == "📰  News Terminal":
    st.title("Financial News Terminal")
    st.caption("Curated market and economic headlines. Live news integration is optional.")
    news = fetch_news(15)
    if news.empty:
        st.info("Live NewsAPI feed is not configured. The rest of NG Finance Pro remains fully available.")
        st.caption("Add NEWS_API_KEY later when you are ready for live news integration.")
    else:
        for _, item in news.iterrows():
            headline = item.get("Headline", "Untitled")
            source = item.get("Source", "Unknown")
            published = item.get("Published", "")
            url = item.get("URL", "")
            if url:
                st.markdown(f"**{headline}**  \n{source} • {published} • [Read article]({url})")
            else:
                st.markdown(f"**{headline}**  \n{source} • {published}")
            st.divider()

elif page == "💧  Treasury Dashboard":
    treasury.render()

elif page == "↔️  Bank Reconciliation":
    reconciliation.render()

elif page == "📑  Budget Analysis":
    budget.render()

elif page == "📋  Financial Statement Analyzer":
    financial_statements.render()

elif page == "📄  Executive Reports":
    insight, _ = generate_ai_insight(snapshot)
    reports.render(snapshot, insight)

footer()
