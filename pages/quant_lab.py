import streamlit as st
import plotly.express as px

from analytics.quant_risk import risk_table, returns_from_prices
from services.market_data import close_series, fetch_market_data


def render(market_symbols: dict[str, str]):
    st.title("Quant Lab")
    st.caption("Research-grade market risk analytics powering the NG Finance Pro quantitative layer.")

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("Historical window", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    with col2:
        confidence = st.selectbox("VaR confidence", [0.90, 0.95, 0.99], index=1)

    price_map = {}
    for asset, symbol in market_symbols.items():
        data = fetch_market_data(symbol, period=period)
        series = close_series(data)
        if not series.empty:
            price_map[asset] = series

    if not price_map:
        st.warning("No historical market data is currently available. Try again later.")
        return

    table = risk_table(price_map, confidence)
    display = table.copy()
    pct_cols = [
        "annualized_volatility", "historical_var", "expected_shortfall",
        "maximum_drawdown", "downside_volatility",
    ]
    for col in pct_cols:
        display[col] = display[col].map(lambda x: f"{x:.2%}" if x is not None else "—")
    display = display.rename(columns={
        "observations": "Observations",
        "annualized_volatility": "Ann. Volatility",
        "historical_var": "Historical VaR",
        "expected_shortfall": "Expected Shortfall",
        "maximum_drawdown": "Max Drawdown",
        "downside_volatility": "Downside Volatility",
    })

    st.subheader("Risk Summary")
    st.dataframe(display, use_container_width=True, hide_index=True)

    asset = st.selectbox("Inspect asset", list(price_map))
    prices = price_map[asset]
    returns = returns_from_prices(prices)

    left, right = st.columns(2)
    with left:
        st.metric("Historical VaR", f"{table.loc[table['Asset'] == asset, 'historical_var'].iloc[0]:.2%}")
        st.metric("Expected Shortfall", f"{table.loc[table['Asset'] == asset, 'expected_shortfall'].iloc[0]:.2%}")
    with right:
        st.metric("Annualized Volatility", f"{table.loc[table['Asset'] == asset, 'annualized_volatility'].iloc[0]:.2%}")
        st.metric("Maximum Drawdown", f"{table.loc[table['Asset'] == asset, 'maximum_drawdown'].iloc[0]:.2%}")

    chart = px.line(x=returns.index, y=returns.values, labels={"x": "Date", "y": "Daily Return"}, title=f"{asset} Daily Returns")
    st.plotly_chart(chart, use_container_width=True)

    st.info(
        "Research note: historical VaR and Expected Shortfall are backward-looking estimates. "
        "They do not forecast future losses by themselves and should be evaluated with out-of-sample testing and stress scenarios."
    )
