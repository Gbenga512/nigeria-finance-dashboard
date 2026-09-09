import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.garch import clean_returns, ewma_volatility, fit_garch11
from services.market_data import close_series, fetch_market_data


def render(symbols: dict[str, str]):
    st.title("GARCH Volatility Lab")
    st.caption("Conditional-volatility modelling for quantitative risk research and MScFE empirical work.")

    col1, col2 = st.columns(2)
    with col1:
        asset = st.selectbox("Asset", list(symbols.keys()), key="garch_asset")
    with col2:
        lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y"], index=1, key="garch_lookback")

    prices = close_series(fetch_market_data(symbols[asset], period=lookback))
    returns = clean_returns(prices.pct_change())
    if returns.empty:
        st.warning("No usable return data is available for this asset/lookback.")
        return

    result = fit_garch11(returns)
    if not result.get("success"):
        st.warning(result.get("message", "GARCH estimation failed."))
        return

    metrics = [
        ("Latest conditional vol", result["latest_volatility"] * np.sqrt(252)),
        ("1-day forecast vol", result["forecast_volatility"] * np.sqrt(252)),
        ("Persistence α+β", result["persistence"]),
        ("Half-life", result["half_life"]),
        ("AIC", result["aic"]),
        ("BIC", result["bic"]),
    ]
    cards = st.columns(6)
    for card, (label, value) in zip(cards, metrics):
        if "vol" in label.lower(): text = f"{value:.2%}"
        elif label == "Half-life": text = f"{value:.1f} days"
        elif "Persistence" in label: text = f"{value:.4f}"
        else: text = f"{value:.2f}"
        card.metric(label, text)

    p1, p2, p3 = st.columns(3)
    p1.metric("ω", f"{result['omega']:.8f}")
    p2.metric("α", f"{result['alpha']:.4f}")
    p3.metric("β", f"{result['beta']:.4f}")

    garch_vol = result["conditional_volatility"] * np.sqrt(252)
    ewma = ewma_volatility(returns)
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=garch_vol.index, y=garch_vol.values, name="GARCH(1,1)"))
    chart.add_trace(go.Scatter(x=ewma.index, y=ewma.values, name="EWMA (λ=0.94)"))
    chart.update_layout(title=f"Conditional Volatility — {asset}", yaxis_title="Annualized volatility", hovermode="x unified")
    st.plotly_chart(chart, use_container_width=True)

    residuals = result["standardized_residuals"]
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=residuals, nbinsx=40, name="Standardized residuals"))
    fig.update_layout(title="Standardized Residual Distribution", xaxis_title="Residual", yaxis_title="Frequency")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Model methodology and assumptions"):
        st.markdown("""
**GARCH(1,1)** models time-varying conditional variance as

σ²ₜ = ω + αε²ₜ₋₁ + βσ²ₜ₋₁

The implementation estimates parameters by Gaussian quasi-maximum likelihood. Returns are supplied as decimal daily returns and internally scaled for numerical stability. A stationary solution requires ω > 0, α ≥ 0, β ≥ 0 and α + β < 1. The reported volatility is annualized using 252 trading days.

EWMA is shown as a transparent benchmark. The model is a research tool, not a guarantee of future volatility.
""")

    export = pd.DataFrame({"GARCH Volatility": garch_vol, "EWMA Volatility": ewma}).reset_index(names="Date")
    st.download_button("Download volatility series (CSV)", export.to_csv(index=False), f"garch_{asset.replace('/', '-')}.csv", "text/csv")
