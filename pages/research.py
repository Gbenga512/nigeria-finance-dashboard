import streamlit as st
import plotly.express as px

from analytics.emerging_markets import comparative_statistics, rolling_volatility, rolling_sharpe, stress_scenarios
from services.market_data import fetch_market_data, close_series
from config.settings import MARKET_SYMBOLS
from ng_ui import hero


def render():
    hero("Research Centre", "A reproducible quantitative workspace for emerging-market risk, comparative analysis and stress testing.", "MScFE research")

    st.markdown("### Research specification")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Research question", value="How do volatility and downside risk differ across selected emerging and global assets?")
        st.text_input("Study design", value="Comparative empirical risk analysis")
    with c2:
        st.text_input("Primary outcome", value="Volatility, drawdown and tail-loss behaviour")
        st.text_input("Validation approach", value="Rolling statistics and historical stress scenarios")

    lookback = st.selectbox("Dataset lookback", ["6mo", "1y", "2y", "5y"], index=2)
    asset = st.selectbox("Primary asset", list(MARKET_SYMBOLS.keys()), index=0)

    price_map = {}
    for name, symbol in MARKET_SYMBOLS.items():
        series = close_series(fetch_market_data(symbol, lookback))
        if not series.empty:
            price_map[name] = series

    stats = comparative_statistics(price_map)
    if stats.empty:
        st.warning("No historical dataset is currently available. Research outputs require real observations.")
        return

    st.markdown("### Comparative risk statistics")
    st.dataframe(stats.style.format({"Annual Return": "{:.2%}", "Annual Volatility": "{:.2%}", "Downside Volatility": "{:.2%}", "Maximum Drawdown": "{:.2%}"}), use_container_width=True, hide_index=True)

    if asset in price_map:
        prices = price_map[asset]
        returns = prices.pct_change().dropna()
        vol = rolling_volatility(returns).dropna()
        sharpe = rolling_sharpe(returns).dropna()

        st.markdown(f"### {asset}: rolling diagnostics")
        left, right = st.columns(2, gap="large")
        with left:
            if not vol.empty:
                fig = px.line(x=vol.index, y=vol.values, labels={"x": "Date", "y": "Annualized volatility"})
                fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with right:
            if not sharpe.empty:
                fig = px.line(x=sharpe.index, y=sharpe.values, labels={"x": "Date", "y": "Rolling Sharpe"})
                fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### Historical stress scenarios")
        stress = stress_scenarios(returns)
        if not stress.empty:
            st.dataframe(stress.style.format({"Worst Historical Return": "{:.2%}"}), use_container_width=True, hide_index=True)

    st.info("Research discipline: datasets must be real and traceable. This centre is an analytical research layer, not a claim of predictive performance. Model results should be evaluated out-of-sample before being used for investment decisions.")
