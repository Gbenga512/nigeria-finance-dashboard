import streamlit as st
import plotly.express as px

from analytics.portfolio_risk import (
    align_returns,
    component_var,
    correlation_matrix,
    portfolio_risk,
    portfolio_returns,
    risk_ratios,
)
from services.market_data import fetch_market_data, close_series
from config.settings import MARKET_SYMBOLS
from ng_ui import hero


def render():
    hero("Portfolio Risk", "Cross-asset risk attribution, correlation and risk-adjusted performance analytics.", "Quantitative risk")

    lookback = st.selectbox("Historical lookback", ["6mo", "1y", "2y", "5y"], index=1)
    confidence = st.selectbox("Confidence level", [0.90, 0.95, 0.975, 0.99], index=1, format_func=lambda x: f"{x:.1%}")

    price_map = {}
    for asset, symbol in MARKET_SYMBOLS.items():
        series = close_series(fetch_market_data(symbol, lookback))
        if not series.empty:
            price_map[asset] = series

    if len(price_map) < 2:
        st.warning("At least two assets with historical prices are required for portfolio analytics.")
        return

    assets = list(price_map)
    st.markdown("### Portfolio allocation")
    default_weights = {asset: 1 / len(assets) for asset in assets}
    cols = st.columns(min(4, len(assets)))
    weights = {}
    for i, asset in enumerate(assets):
        with cols[i % len(cols)]:
            weights[asset] = st.number_input(asset, min_value=0.0, max_value=1.0, value=float(default_weights[asset]), step=0.05, format="%.2f")

    metrics = portfolio_risk(price_map, weights, confidence)
    ratios = risk_ratios(portfolio_returns(price_map, weights))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Portfolio volatility", f"{metrics['volatility']:.2%}" if metrics['volatility'] is not None else "—")
    c2.metric("Historical VaR", f"{metrics['historical_var']:.2%}" if metrics['historical_var'] is not None else "—")
    c3.metric("Historical ES", f"{metrics['historical_es']:.2%}" if metrics['historical_es'] is not None else "—")
    c4.metric("Monte Carlo ES", f"{metrics['monte_carlo_es']:.2%}" if metrics['monte_carlo_es'] is not None else "—")
    c5.metric("Sharpe", f"{ratios['sharpe']:.2f}" if ratios['sharpe'] is not None else "—")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Correlation matrix")
        corr = correlation_matrix(price_map)
        fig = px.imshow(corr, text_auto=".2f", aspect="auto")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("### Risk contribution")
        contribution = component_var(price_map, weights, confidence)
        if not contribution.empty:
            st.dataframe(contribution.style.format({"Weight": "{:.1%}", "Marginal Risk": "{:.2%}", "Component Volatility Risk": "{:.2%}", "% of Portfolio Risk": "{:.1%}"}), use_container_width=True, hide_index=True)

    st.markdown("### Risk-adjusted performance")
    r1, r2, r3 = st.columns(3)
    r1.metric("Sharpe ratio", f"{ratios['sharpe']:.2f}" if ratios['sharpe'] is not None else "—")
    r2.metric("Sortino ratio", f"{ratios['sortino']:.2f}" if ratios['sortino'] is not None else "—")
    r3.metric("Calmar ratio", f"{ratios['calmar']:.2f}" if ratios['calmar'] is not None else "—")

    st.info("Methodology: fixed normalized weights, daily simple returns, 252 trading days per year. VaR and ES are loss fractions at the selected confidence level. Ratios assume a 0% annual risk-free rate unless changed in a future release.")
