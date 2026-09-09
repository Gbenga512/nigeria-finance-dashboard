import streamlit as st
import plotly.express as px

from analytics.robustness import model_sensitivity, rolling_var_stability, bootstrap_metric_ci, robustness_summary
from services.market_data import close_series, fetch_market_data
from analytics.quant_risk import returns_from_prices


def render():
    st.title("Risk Robustness Lab")
    st.caption("Sensitivity and uncertainty analysis for quantitative market-risk estimates.")

    from config.settings import MARKET_SYMBOLS

    c1, c2, c3 = st.columns(3)
    with c1:
        asset = st.selectbox("Asset", list(MARKET_SYMBOLS))
    with c2:
        period = st.selectbox("Historical window", ["1y", "2y", "5y"], index=1)
    with c3:
        confidence = st.selectbox("VaR confidence", [0.90, 0.95, 0.975, 0.99], index=1)

    data = fetch_market_data(MARKET_SYMBOLS[asset], period=period)
    prices = close_series(data)
    returns = returns_from_prices(prices)

    if returns.empty:
        st.warning("No historical market data is currently available. Try again later.")
        return

    summary = robustness_summary(returns, confidence)
    a, b, c = st.columns(3)
    a.metric("Observations", f"{len(returns):,}")
    b.metric("VaR model range", f"{summary['var_range']:.2%}" if summary["var_range"] is not None else "—")
    c.metric("ES model range", f"{summary['es_range']:.2%}" if summary["es_range"] is not None else "—")

    st.subheader("Cross-model sensitivity")
    sensitivity = model_sensitivity(returns)
    st.dataframe(
        sensitivity.style.format({"Confidence": "{:.1%}", "VaR": "{:.2%}", "Expected Shortfall": "{:.2%}"}),
        use_container_width=True,
        hide_index=True,
    )

    chart = px.line(
        sensitivity,
        x="Confidence",
        y="VaR",
        color="Model",
        markers=True,
        labels={"Confidence": "Confidence level", "VaR": "VaR"},
        title="VaR sensitivity to confidence level",
    )
    chart.update_xaxes(tickformat=".1%")
    chart.update_yaxes(tickformat=".2%")
    st.plotly_chart(chart, use_container_width=True)

    st.subheader("Estimation-window sensitivity")
    stability = rolling_var_stability(returns, confidence)
    if stability.empty:
        st.info("Not enough observations for the selected estimation windows.")
    else:
        st.dataframe(stability.style.format({"VaR": "{:.2%}"}), use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(stability, x="Window", y="VaR", title="Historical VaR by estimation window"),
            use_container_width=True,
        )

    st.subheader("Bootstrap uncertainty")
    metric = st.radio("Metric", ["VaR", "Expected Shortfall"], horizontal=True)
    ci = bootstrap_metric_ci(returns, confidence, metric=metric)
    if ci["estimate"] is None:
        st.info("Not enough observations to estimate a bootstrap confidence interval.")
    else:
        x, y, z = st.columns(3)
        x.metric("Estimate", f"{ci['estimate']:.2%}")
        y.metric("2.5% CI", f"{ci['ci_lower']:.2%}")
        z.metric("97.5% CI", f"{ci['ci_upper']:.2%}")

    with st.expander("Interpretation & methodology"):
        st.markdown(
            "Model disagreement is a model-risk diagnostic, not evidence that one estimate is correct. "
            "Historical VaR is sensitive to the estimation window and tail observations. "
            "Bootstrap intervals quantify sampling uncertainty and do not eliminate structural or regime-change risk."
        )
        st.caption("Deterministic research settings use fixed random seeds. Results are informational and not investment advice.")
