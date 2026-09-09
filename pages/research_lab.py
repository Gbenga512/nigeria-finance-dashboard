import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.backtesting import walk_forward_backtest
from analytics.factors import factor_features, factor_signal
from analytics.ml_regime import regime_ml_experiment
from analytics.portfolio_risk import portfolio_returns, risk_ratios, optimized_portfolio_walk_forward, portfolio_stress_matrix
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
        equity = wf["equity"].reset_index().rename(columns={wf["equity"].index.name or "index": "Date"})
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
    st.caption("Fixed weights are evaluated out-of-sample for comparison; the optimizer below performs true sequential minimum-variance re-estimation using training data only.")
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
            comparison = pd.DataFrame([{"Portfolio": "Configured portfolio", "Sharpe": p_metrics["sharpe"], "Sortino": p_metrics["sortino"], "Calmar": p_metrics["calmar"]}, {"Portfolio": "Equal-weight benchmark", "Sharpe": b_metrics["sharpe"], "Sortino": b_metrics["sortino"], "Calmar": b_metrics["calmar"]}])
            st.dataframe(comparison.style.format({"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}"}), use_container_width=True, hide_index=True)

        st.markdown("#### True portfolio walk-forward optimizer")
        opt = optimized_portfolio_walk_forward({asset: price_map[asset] for asset in portfolio_assets}, train_window=train_window, test_window=test_window, transaction_cost=transaction_cost)
        if opt["summary"]:
            s = opt["summary"]
            o1, o2, o3, o4 = st.columns(4)
            o1.metric("OOS Optimized Return", f"{s['annualized_return']:.2%}")
            o2.metric("OOS Optimized Sharpe", "—" if s["sharpe"] is None else f"{s['sharpe']:.2f}")
            o3.metric("OOS Volatility", f"{s['annualized_volatility']:.2%}")
            o4.metric("Benchmark Sharpe", "—" if s["benchmark_sharpe"] is None else f"{s['benchmark_sharpe']:.2f}")
            eq = opt["equity"].reset_index().rename(columns={opt["equity"].index.name or "index": "Date"})
            eq_long = eq.melt(id_vars=["Date"], var_name="Series", value_name="Growth of $1")
            fig = px.line(eq_long, x="Date", y="Growth of $1", color="Series", title="Minimum-variance portfolio vs equal weight")
            fig.update_layout(height=360)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.dataframe(opt["blocks"].style.format({"Test Return": "{:.2%}", "Benchmark Return": "{:.2%}", "Turnover": "{:.2f}"}), use_container_width=True, hide_index=True)
            st.markdown("#### Re-estimated portfolio weights")
            st.dataframe(opt["weights"].style.format("{:.2%}"), use_container_width=True)
            st.caption("At each rebalance, weights are estimated from the preceding training window only. The first test-day return includes the configured transaction cost. This is a research backtest, not an investment recommendation.")
        else:
            st.info("Insufficient observations for true portfolio walk-forward optimization. Increase the dataset lookback or reduce the training window.")

        st.markdown("#### Portfolio stress testing")
        stress_shocks = st.multiselect("Portfolio shocks", [-0.05, -0.10, -0.20, -0.30], default=[-0.10, -0.20], format_func=lambda x: f"{x:.0%}", key="portfolio_stress")
        stress = portfolio_stress_matrix({asset: price_map[asset] for asset in portfolio_assets}, weights, stress_shocks)
        if not stress.empty:
            st.dataframe(stress.style.format({"Portfolio Loss": "{:.2%}"}), use_container_width=True, hide_index=True)
            st.caption("Stress results are deterministic sensitivity scenarios. Common shocks apply to the whole portfolio; asset-specific shocks apply only to the named asset while other positions are unchanged.")

    st.markdown("### ML volatility regime prediction")
    st.caption("Chronological out-of-sample classification of the next 21-trading-day volatility regime. Thresholds are estimated from the training sample only; the persistence baseline uses current volatility as a simple benchmark.")
    ml_asset = st.selectbox("Asset for ML regime prediction", list(price_map.keys()), key="ml_regime_asset")
    ml_result = regime_ml_experiment(price_map[ml_asset], test_fraction=0.30, feature_window=21, horizon=21, random_state=42)
    if not ml_result["available"]:
        st.info(ml_result["reason"])
    else:
        ml_metrics = ml_result["evaluations"].copy()
        st.dataframe(ml_metrics.style.format({col: "{:.2%}" for col in ["accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1"]}), use_container_width=True, hide_index=True)
        best_model = ml_metrics.sort_values("balanced_accuracy", ascending=False).iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Best test balanced accuracy", f"{best_model['balanced_accuracy']:.2%}")
        m2.metric("Best model", str(best_model["Model"]))
        m3.metric("Test observations", f"{ml_result['test_observations']:,}")
        pred = ml_result["predictions"].reset_index().rename(columns={ml_result["predictions"].index.name or "index": "Date"})
        pred_long = pred.melt(id_vars=["Date"], var_name="Series", value_name="Regime")
        fig = px.scatter(pred_long, x="Date", y="Series", color="Regime", title=f"Predicted vs realized volatility regimes — {ml_asset}")
        fig.update_traces(marker={"size": 7})
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        model_choice = st.selectbox("Confusion matrix model", ["Logistic regression", "Random forest"], key="ml_cm_model")
        cm = ml_result["confusion_matrices"][model_choice]
        cm_display = cm.copy(); cm_display.index.name = "Actual"; cm_display.columns.name = "Predicted"
        st.dataframe(cm_display, use_container_width=True)
        importance = ml_result["feature_importance"]
        if not importance.empty:
            fig = px.bar(importance, x="Importance", y="Feature", orientation="h", title="Random forest feature importance")
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with st.expander("ML methodology & reproducibility"):
            st.json(ml_result["methodology"])
            st.write(f"Training observations: {ml_result['train_observations']:,}. Test observations: {ml_result['test_observations']:,}. Training end: {ml_result['train_end']}. Test start: {ml_result['test_start']}.")
        st.caption("The ML output is an empirical research model, not a trading signal. Test-set performance should be interpreted with model risk, non-stationarity and multiple-testing considerations in mind.")

    st.markdown("### Methodology & reproducibility")
    methodology = methodology_record(confidence, lookback, window)
    methodology.update({
        "walk_forward_validation": "Expanding training window with sequential out-of-sample test blocks",
        "candidate_strategies": "Momentum, mean-reversion, buy-and-hold",
        "look_ahead_control": "Signals are shifted one trading day before returns are realized",
        "training_selection": "Strategy selection is based on net training Sharpe after transaction costs",
        "regime_analysis": "Volatility-regime conditioning is reported ex-post and does not influence test-period selection",
        "portfolio_validation": "Fixed weights plus sequential long-only minimum-variance re-estimation compared with an equal-weight benchmark",
        "portfolio_optimizer": "Minimum-variance weights estimated independently in each training window; long-only and normalized",
        "portfolio_stress": "Deterministic common and asset-specific downside shock sensitivity",
        "ml_regime_prediction": "Chronological out-of-sample logistic regression and random forest classification of forward volatility regimes",
        "ml_threshold_control": "33rd/67th regime thresholds estimated from training targets only",
        "transaction_cost": "User-selected proportional cost per unit turnover",
    })
    st.json(methodology)
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download experiment results (CSV)", csv, "ng_finance_pro_research_results.csv", "text/csv")
    st.caption("Research outputs are designed for empirical analysis and model validation. They are not personalized investment advice. Monte Carlo results use a fixed seed (42) for reproducibility.")
