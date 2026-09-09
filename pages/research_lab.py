import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.research_lab import (
    methodology_record,
    research_summary,
    rolling_volatility,
    run_research_experiment,
    scenario_matrix,
)
from config.settings import MARKET_SYMBOLS
from services.market_data import close_series, fetch_market_data
from ng_ui import hero


def render():
    hero("Research & Backtesting Centre", "A reproducible quantitative research workspace for model comparison, risk validation and empirical analysis.", "MScFE research")

    c1, c2, c3 = st.columns(3)
    with c1:
        lookback = st.selectbox("Dataset lookback", ["6mo", "1y", "2y", "5y"], index=2)
    with c2:
        confidence = st.selectbox("VaR confidence", [0.90, 0.95, 0.975, 0.99], index=1, format_func=lambda x: f"{x:.1%}")
    with c3:
        window = st.selectbox("VaR backtest window", [60, 120, 252], index=2)

    selected = st.multiselect("Research universe", list(MARKET_SYMBOLS.keys()), default=list(MARKET_SYMBOLS.keys()))
    if not selected:
        st.info("Select at least one asset to run the experiment.")
        return

    price_map = {}
    with st.spinner("Loading historical observations and running the experiment..."):
        for asset in selected:
            series = close_series(fetch_market_data(MARKET_SYMBOLS[asset], lookback))
            if not series.empty:
                price_map[asset] = series

    results = run_research_experiment(price_map, confidence, window)
    if results.empty:
        st.warning("No valid historical data is currently available for the selected universe.")
        return

    st.success(research_summary(results, confidence))
    st.markdown("### Experiment results")
    display = results.copy()
    pct_cols = ["annualized_volatility", "historical_var", "historical_es", "monte_carlo_var", "monte_carlo_es", "maximum_drawdown", "worst_5d_loss", "var_exception_rate", "expected_exception_rate"]
    st.dataframe(display.style.format({col: "{:.2%}" for col in pct_cols if col in display.columns}), use_container_width=True, hide_index=True)

    left, right = st.columns(2, gap="large")
    with left:
        fig = px.bar(results, x="Asset", y="annualized_volatility", title="Annualized volatility")
        fig.update_layout(yaxis_tickformat=".1%", height=360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = px.scatter(results, x="historical_var", y="historical_es", text="Asset", title="Historical VaR vs Expected Shortfall")
        fig.update_layout(xaxis_tickformat=".1%", yaxis_tickformat=".1%", height=360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### VaR model validation")
    validation = results[["Asset", "var_exception_rate", "expected_exception_rate", "var_exceptions", "backtest_observations"]].copy()
    validation["Exception Gap"] = validation["var_exception_rate"] - validation["expected_exception_rate"]
    st.dataframe(validation.style.format({"var_exception_rate": "{:.2%}", "expected_exception_rate": "{:.2%}", "Exception Gap": "{:+.2%}"}), use_container_width=True, hide_index=True)

    st.markdown("### Scenario stress analysis")
    shock_levels = st.multiselect("Downside price shocks", [-0.05, -0.10, -0.15, -0.20, -0.30], default=[-0.05, -0.10, -0.20], format_func=lambda x: f"{x:.0%}")
    if shock_levels:
        scenarios = scenario_matrix(price_map, shock_levels)
        scenario_pivot = scenarios.pivot(index="Asset", columns="Shock", values="Scenario Loss")
        st.dataframe(scenario_pivot.style.format("{:.2%}"), use_container_width=True)
        st.caption("Scenario losses are deterministic sensitivity estimates, not forecasts or probability-weighted stress-test results.")

    st.markdown("### Rolling volatility regime")
    selected_asset = st.selectbox("Asset for rolling volatility", list(price_map.keys()))
    rolling = rolling_volatility(price_map[selected_asset], window=21).dropna()
    if not rolling.empty:
        rolling_df = rolling.rename("Annualized Volatility").reset_index()
        rolling_df.columns = ["Date", "Annualized Volatility"]
        fig = px.line(rolling_df, x="Date", y="Annualized Volatility", title=f"21-day rolling volatility — {selected_asset}")
        fig.update_layout(yaxis_tickformat=".1%", height=360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Methodology & reproducibility")
    method = methodology_record(confidence, lookback, window)
    st.json(method)

    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download experiment results (CSV)", csv, "ng_finance_pro_research_results.csv", "text/csv")

    st.caption("Research outputs are designed for empirical analysis and model validation. They are not personalized investment advice. Monte Carlo results use a fixed seed (42) for reproducibility.")
