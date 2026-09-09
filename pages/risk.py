import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config.settings import MARKET_SYMBOLS
from services.market_data import fetch_market_data, close_series
from analytics.quant_risk import (
    returns_from_prices,
    risk_metrics,
    risk_model_comparison,
    var_backtest,
    maximum_drawdown,
    stress_loss,
)
from ng_ui import hero


LOOKBACKS = {
    "6 months": "6mo",
    "1 year": "1y",
    "2 years": "2y",
    "5 years": "5y",
}


def _pct(value):
    return "—" if value is None or pd.isna(value) else f"{float(value) * 100:.2f}%"


def render(snapshot: pd.DataFrame):
    hero(
        "Quant Risk Centre",
        "Quantitative market-risk analytics with VaR, Expected Shortfall, drawdown, stress testing and model comparison.",
        "Quantitative risk",
    )

    available_assets = list(MARKET_SYMBOLS.keys())
    if not available_assets:
        st.warning("No market instruments are configured.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        asset = st.selectbox("Risk asset", available_assets)
    with c2:
        lookback_label = st.selectbox("Historical lookback", list(LOOKBACKS.keys()), index=1)
    with c3:
        confidence = st.selectbox("Confidence level", [0.90, 0.95, 0.975, 0.99], index=1, format_func=lambda x: f"{x:.1%}")

    symbol = MARKET_SYMBOLS[asset]
    prices = close_series(fetch_market_data(symbol, period=LOOKBACKS[lookback_label]))
    if len(prices) < 30:
        st.warning(f"Insufficient historical observations for {asset}. Try a longer lookback period.")
        return

    returns = returns_from_prices(prices)
    metrics = risk_metrics(prices, confidence)
    backtest = var_backtest(returns, confidence, window=min(252, max(30, len(returns) // 2)))

    st.markdown("### Risk dashboard")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Historical VaR", _pct(metrics["historical_var"]))
    k2.metric("Expected Shortfall", _pct(metrics["expected_shortfall"]))
    k3.metric("Annualized volatility", _pct(metrics["annualized_volatility"]))
    k4.metric("Maximum drawdown", _pct(metrics["maximum_drawdown"]))
    exception_rate = backtest.get("exception_rate")
    k5.metric("VaR exceptions", "—" if exception_rate is None else f"{backtest['exceptions']} ({exception_rate:.1%})")

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.markdown("#### Return distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=returns * 100, nbinsx=45, name="Daily returns"))
        var_pct = metrics["historical_var"] * 100 if metrics["historical_var"] is not None else None
        if var_pct is not None:
            fig.add_vline(x=-var_pct, line_dash="dash", annotation_text="Historical VaR")
        fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=15, b=10),
            xaxis_title="Daily return (%)",
            yaxis_title="Frequency",
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
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
    fig_dd.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=15, b=10),
        yaxis_title="Drawdown (%)",
        xaxis_title=None,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_dd, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### VaR backtest")
    b1, b2, b3 = st.columns(3)
    b1.metric("Forecast observations", backtest["observations"])
    b2.metric("Exceptions", backtest["exceptions"])
    b3.metric("Expected exception rate", f"{backtest['expected_rate']:.1%}")
    if backtest["exception_rate"] is not None:
        actual = backtest["exception_rate"]
        expected = backtest["expected_rate"]
        if actual > expected * 2 and backtest["exceptions"] >= 3:
            st.warning("Observed VaR exceptions are materially above the model's expected frequency. Model performance should be investigated.")
        else:
            st.success("Observed VaR exception frequency is within the current monitoring threshold.")

    with st.expander("Methodology and assumptions"):
        st.write(
            "Historical VaR uses the empirical lower-tail return quantile. Expected Shortfall averages losses beyond that tail threshold. "
            "Parametric measures assume approximately normal returns, while Monte Carlo currently simulates from a calibrated normal distribution. "
            "The VaR backtest uses rolling historical VaR and compares observed exceptions with the theoretical tail probability. "
            "Results are single-asset percentage risk measures, not investment advice or guaranteed loss limits."
        )
        st.caption(f"Instrument: {asset} ({symbol}) • Lookback: {lookback_label} • Observations: {len(returns)} • Confidence: {confidence:.1%}")
