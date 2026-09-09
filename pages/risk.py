import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config.settings import MARKET_SYMBOLS
from services.market_data import fetch_market_data, close_series
from analytics.quant_risk import returns_from_prices, risk_metrics, risk_model_comparison, var_backtest, maximum_drawdown, stress_loss
from analytics.var_backtesting import backtest_var
from ng_ui import hero

LOOKBACKS = {"6 months": "6mo", "1 year": "1y", "2 years": "2y", "5 years": "5y"}

def _pct(value):
    return "—" if value is None or pd.isna(value) else f"{float(value) * 100:.2f}%"

def render(snapshot: pd.DataFrame):
    hero("Quant Risk Centre", "Quantitative market-risk analytics with VaR, Expected Shortfall, drawdown, stress testing and formal statistical backtesting.", "Quantitative risk")
    available_assets = list(MARKET_SYMBOLS.keys())
    if not available_assets:
        st.warning("No market instruments are configured.")
        return
    c1, c2, c3 = st.columns(3)
    with c1: asset = st.selectbox("Risk asset", available_assets)
    with c2: lookback_label = st.selectbox("Historical lookback", list(LOOKBACKS.keys()), index=1)
    with c3: confidence = st.selectbox("Confidence level", [0.90, 0.95, 0.975, 0.99], index=1, format_func=lambda x: f"{x:.1%}")
    symbol = MARKET_SYMBOLS[asset]
    prices = close_series(fetch_market_data(symbol, period=LOOKBACKS[lookback_label]))
    if len(prices) < 30:
        st.warning(f"Insufficient historical observations for {asset}. Try a longer lookback period.")
        return
    returns = returns_from_prices(prices)
    metrics = risk_metrics(prices, confidence)
    rolling = var_backtest(returns, confidence, window=min(252, max(30, len(returns) // 2)))

    st.markdown("### Risk dashboard")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Historical VaR", _pct(metrics["historical_var"]))
    k2.metric("Expected Shortfall", _pct(metrics["expected_shortfall"]))
    k3.metric("Annualized volatility", _pct(metrics["annualized_volatility"]))
    k4.metric("Maximum drawdown", _pct(metrics["maximum_drawdown"]))
    exception_rate = rolling.get("exception_rate")
    k5.metric("VaR exceptions", "—" if exception_rate is None else f"{rolling['exceptions']} ({exception_rate:.1%})")

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.markdown("#### Return distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=returns * 100, nbinsx=45, name="Daily returns"))
        var_pct = metrics["historical_var"] * 100 if metrics["historical_var"] is not None else None
        if var_pct is not None: fig.add_vline(x=-var_pct, line_dash="dash", annotation_text="Historical VaR")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=15, b=10), xaxis_title="Daily return (%)", yaxis_title="Frequency", showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Stress scenarios")
        scenarios = pd.DataFrame([
            {"Scenario": "-2% shock", "Loss": stress_loss(returns, -0.02)},
            {"Scenario": "-5% shock", "Loss": stress_loss(returns, -0.05)},
            {"Scenario": "-10% shock", "Loss": stress_loss(returns, -0.10)},
            {"Scenario": "Worst observed day", "Loss": max(0.0, -float(returns.min()))},
        ])
        scenarios["Loss"] = scenarios["Loss"].map(lambda x: f"{x * 100:.2f}%")
        st.dataframe(scenarios, use_container_width=True, hide_index=True)
        st.caption("Stress losses are one-period percentage shocks and are not portfolio monetary losses.")

    st.markdown("### Risk model comparison")
    comparison = risk_model_comparison(returns, confidence)
    display = comparison.copy()
    display["VaR"] = display["VaR"].map(_pct)
    display["Expected Shortfall"] = display["Expected Shortfall"].map(_pct)
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("### Drawdown profile")
    running_peak = prices.cummax()
    drawdown = (prices / running_peak - 1) * 100
    fig_dd = go.Figure(go.Scatter(x=drawdown.index, y=drawdown, mode="lines", name="Drawdown"))
    fig_dd.update_layout(height=280, margin=dict(l=10, r=10, t=15, b=10), yaxis_title="Drawdown (%)", xaxis_title=None, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_dd, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### VaR backtest")
    b1, b2, b3 = st.columns(3)
    b1.metric("Rolling observations", rolling["observations"])
    b2.metric("Rolling exceptions", rolling["exceptions"])
    b3.metric("Expected exception rate", f"{rolling['expected_rate']:.1%}")
    if rolling["exception_rate"] is not None:
        if rolling["exception_rate"] > rolling["expected_rate"] * 2 and rolling["exceptions"] >= 3:
            st.warning("Observed rolling VaR exceptions are materially above the expected frequency. Model performance should be investigated.")
        else:
            st.success("Observed rolling VaR exception frequency is within the current monitoring threshold.")

    st.markdown("### Formal VaR validation")
    formal = backtest_var(returns, pd.Series(metrics["historical_var"], index=returns.index), confidence)
    # The formal test above evaluates the fixed historical VaR threshold. The rolling test remains the primary dynamic monitoring series.
    f1, f2, f3 = st.columns(3)
    f1.metric("Kupiec POF p-value", f"{formal['kupiec']['p_value']:.4f}")
    f2.metric("Christoffersen independence", f"{formal['independence']['p_value']:.4f}")
    f3.metric("Conditional coverage p-value", f"{formal['conditional_coverage']['p_value']:.4f}")
    formal_table = pd.DataFrame([
        {"Test": "Kupiec POF", "Statistic": formal["kupiec"]["statistic"], "p-value": formal["kupiec"]["p_value"], "Reject at 5%": formal["kupiec"]["reject_5pct"]},
        {"Test": "Christoffersen Independence", "Statistic": formal["independence"]["statistic"], "p-value": formal["independence"]["p_value"], "Reject at 5%": formal["independence"]["reject_5pct"]},
        {"Test": "Christoffersen Conditional Coverage", "Statistic": formal["conditional_coverage"]["statistic"], "p-value": formal["conditional_coverage"]["p_value"], "Reject at 5%": formal["conditional_coverage"]["reject_5pct"]},
    ])
    st.dataframe(formal_table, use_container_width=True, hide_index=True)
    st.caption("Formal tests assess unconditional coverage, exception independence and joint conditional coverage. A high p-value means the null hypothesis is not rejected; it does not prove that a VaR model is correct.")

    with st.expander("Methodology and assumptions"):
        st.write("Historical VaR uses the empirical lower-tail return quantile. Expected Shortfall averages losses beyond that tail threshold. Parametric measures assume approximately normal returns, while Monte Carlo currently simulates from a calibrated normal distribution. Rolling VaR monitoring compares observed exceptions with the theoretical tail probability. Kupiec POF tests exception frequency; Christoffersen tests independence and conditional coverage. Results are single-asset percentage risk measures, not investment advice or guaranteed loss limits.")
        st.caption(f"Instrument: {asset} ({symbol}) • Lookback: {lookback_label} • Observations: {len(returns)} • Confidence: {confidence:.1%}")
