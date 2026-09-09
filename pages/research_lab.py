import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.backtesting import walk_forward_backtest
from analytics.factors import factor_features, factor_signal
from analytics.portfolio_risk import portfolio_returns, risk_ratios
from analytics.research_lab import methodology_record, research_summary, rolling_volatility, run_research_experiment, scenario_matrix
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
    pct_cols = ["annualized_volatility", "historical_var", "historical_es", "monte_carlo_var", "monte_carlo_es", "maximum_drawdown", "worst_5d_loss", "var_exception_rate", "expected_exception_rate"]
    st.dataframe(results.style.format({col: "{:.2%}" for col in pct_cols if col in results.columns}), use_container_width=True, hide_index=True)

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

    st.markdown("### Factor diagnostics")
    factor_asset = st.selectbox("Asset for factor diagnostics", list(price_map.keys()), key="factor_asset")
    features = factor_features(price_map[factor_asset])
    if features.empty:
        st.info("Insufficient observations for factor diagnostics.")
    else:
        latest = features.iloc[-1]
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("5D Momentum", f"{latest['momentum_5d']:.2%}")
        f2.metric("21D Momentum", f"{latest['momentum_21d']:.2%}")
        f3.metric("21D Volatility", f"{latest['volatility_21d']:.2%}")
        f4.metric("21D Trend", f"{latest['trend_21d']:.2%}")
        st.info(f"Research factor state: **{factor_signal(price_map[factor_asset])}**. This is a descriptive signal for research, not a trading recommendation.")
        chart_data = features[["momentum_5d", "momentum_21d", "trend_21d"]].tail(252).reset_index()
        chart_data = chart_data.melt(id_vars=[chart_data.columns[0]], var_name="Factor", value_name="Value")
        chart_data = chart_data.rename(columns={chart_data.columns[0]: "Date"})
        fig = px.line(chart_data, x="Date", y="Value", color="Factor", title=f"Factor diagnostics — {factor_asset}")
        fig.update_layout(yaxis_tickformat=".1%", height=360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Walk-forward strategy validation")
    st.caption("The engine selects a candidate using training data only, then evaluates the selected strategy on unseen observations. Signals are shifted one trading day to prevent look-ahead bias.")
    w1, w2, w3 = st.columns(3)
    with w1:
        train_window = st.selectbox("Training window", [126, 252, 504], index=1, key="wf_train")
    with w2:
        test_window = st.selectbox("Test window", [21, 63, 126], index=1, key="wf_test")
    with w3:
        transaction_cost = st.selectbox("Transaction cost", [0.0005, 0.0010, 0.0020], index=1, format_func=lambda x: f"{x:.2%}", key="wf_cost")

    wf_asset = st.selectbox("Asset for walk-forward validation", list(price_map.keys()), key="wf_asset")
    with st.spinner("Running out-of-sample walk-forward validation..."):
        wf = walk_forward_backtest(price_map[wf_asset], train_window, test_window, transaction_cost)

    if not wf["summary"]:
        st.warning("Insufficient observations for the selected training window. Increase the dataset lookback or reduce the training window.")
    else:
        summary = wf["summary"]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("OOS Annualized Return", f"{summary['annualized_return']:.2%}")
        k2.metric("OOS Sharpe", f"{summary['sharpe']:.2f}")
        k3.metric("OOS Max Drawdown", f"{summary['maximum_drawdown']:.2%}")
        k4.metric("OOS Alpha", f"{summary['oos_alpha']:.2%}")

        equity = wf["equity"].reset_index()
        equity = equity.rename(columns={equity.columns[0]: "Date"})
        equity_long = equity.melt(id_vars=["Date"], var_name="Series", value_name="Growth of $1")
        fig = px.line(equity_long, x="Date", y="Growth of $1", color="Series", title=f"Out-of-sample equity curve — {wf_asset}")
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("#### Walk-forward blocks")
        blocks = wf["blocks"]
        st.dataframe(blocks.style.format({"Training Sharpe": "{:.2f}", "Test Return": "{:.2%}", "Test Sharpe": "{:.2f}", "Test Max Drawdown": "{:.2%}", "Benchmark Return": "{:.2%}", "Turnover": "{:.2f}"}), use_container_width=True, hide_index=True)
        st.caption("Candidate set: momentum, mean-reversion, and buy-and-hold. Selection is net of transaction costs and uses only the training sample.")

        regime_table = wf.get("regime_summary", pd.DataFrame())
        if not regime_table.empty:
            st.markdown("#### Regime-conditioned OOS performance")
            st.dataframe(regime_table.style.format({"Cumulative Return": "{:.2%}", "Annualized Volatility": "{:.2%}", "Sharpe": "{:.2f}", "Hit Rate": "{:.2%}"}), use_container_width=True, hide_index=True)
            st.caption("Regimes are classified from rolling volatility as an ex-post diagnostic; they are not used to select the strategy during the test period.")

    st.markdown("### Portfolio walk-forward validation")
    st.caption("A fixed-weight multi-asset portfolio is evaluated on aligned daily returns. The benchmark uses equal weights; portfolio weights are normalized automatically.")
    portfolio_assets = st.multiselect("Portfolio assets", list(price_map.keys()), default=list(price_map.keys()), key="wf_port_assets")
    if portfolio_assets:
        weight_cols = st.columns(len(portfolio_assets))
        weights = {}
        for idx, asset in enumerate(portfolio_assets):
            with weight_cols[idx]:
                weights[asset] = st.number_input(f"{asset} weight", min_value=0.0, max_value=1.0, value=1.0 / len(portfolio_assets), step=0.05, key=f"wf_weight_{asset}")
        portfolio = portfolio_returns({asset: price_map[asset] for asset in portfolio_assets}, weights)
        equal_weights = {asset: 1.0 for asset in portfolio_assets}
        benchmark_portfolio = portfolio_returns({asset: price_map[asset] for asset in portfolio_assets}, equal_weights)
        if not portfolio.empty and not benchmark_portfolio.empty:
            p_metrics = risk_ratios(portfolio)
            b_metrics = risk_ratios(benchmark_portfolio)
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Portfolio Sharpe", "—" if p_metrics["sharpe"] is None else f"{p_metrics['sharpe']:.2f}")
            p2.metric("Portfolio Sortino", "—" if p_metrics["sortino"] is None else f"{p_metrics['sortino']:.2f}")
            p3.metric("Equal-weight Sharpe", "—" if b_metrics["sharpe"] is None else f"{b_metrics['sharpe']:.2f}")
            p4.metric("Equal-weight Sortino", "—" if b_metrics["sortino"] is None else f"{b_metrics['sortino']:.2f}")
            comparison = pd.DataFrame([{
                "Portfolio": "Configured portfolio",
                "Sharpe": p_metrics["sharpe"],
                "Sortino": p_metrics["sortino"],
                "Calmar": p_metrics["calmar"],
            }, {
                "Portfolio": "Equal-weight benchmark",
                "Sharpe": b_metrics["sharpe"],
                "Sortino": b_metrics["sortino"],
                "Calmar": b_metrics["calmar"],
            }])
            st.dataframe(comparison.style.format({"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("### Methodology & reproducibility")
    methodology = methodology_record(confidence, lookback, window)
    methodology.update({
        "walk_forward_validation": "Expanding training window with sequential out-of-sample test blocks",
        "candidate_strategies": "Momentum, mean-reversion, buy-and-hold",
        "look_ahead_control": "Signals are shifted one trading day before returns are realized",
        "training_selection": "Strategy selection is based on net training Sharpe after transaction costs",
        "regime_analysis": "Volatility-regime conditioning is reported ex-post and does not influence test-period selection",
        "portfolio_validation": "Fixed user-specified weights compared with an equal-weight benchmark on aligned daily returns",
        "transaction_cost": "User-selected proportional cost per unit turnover",
    })
    st.json(methodology)

    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download experiment results (CSV)", csv, "ng_finance_pro_research_results.csv", "text/csv")
    st.caption("Research outputs are designed for empirical analysis and model validation. They are not personalized investment advice. Monte Carlo results use a fixed seed (42) for reproducibility.")
