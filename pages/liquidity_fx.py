import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.liquidity_fx import fx_risk_metrics, fx_exposure_stress, liquidity_metrics, liquidity_stress, risk_signal
from config.settings import MARKET_SYMBOLS
from services.market_data import close_series, fetch_market_data
from ng_ui import hero


def render():
    hero("Liquidity & FX Risk Centre", "Integrated Naira liquidity, foreign-exchange exposure and stress analysis for finance teams.", "Treasury risk")
    st.markdown("### Treasury liquidity inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        cash = st.number_input("Liquid cash (₦)", min_value=0.0, value=250_000_000.0, step=5_000_000.0)
    with c2:
        daily_outflow = st.number_input("Daily cash outflow (₦)", min_value=0.0, value=10_000_000.0, step=500_000.0)
    with c3:
        liabilities = st.number_input("Near-term liabilities (₦)", min_value=0.0, value=100_000_000.0, step=5_000_000.0)
    lm = liquidity_metrics(cash, daily_outflow, liabilities)
    k1, k2, k3 = st.columns(3)
    k1.metric("Liquid cash", f"₦{lm['liquid_assets']:,.0f}")
    k2.metric("Cash runway", "∞" if not np.isfinite(lm['runway_days']) else f"{lm['runway_days']:.1f} days")
    k3.metric("Liquidity coverage", "∞" if not np.isfinite(lm['liquidity_coverage']) else f"{lm['liquidity_coverage']:.2f}x")

    st.markdown("### USD/NGN FX risk")
    fx_symbol = MARKET_SYMBOLS.get("USD/NGN", "NGN=X")
    fx_prices = close_series(fetch_market_data(fx_symbol, period="2y"))
    if len(fx_prices) < 30:
        st.warning("Insufficient USD/NGN observations for FX risk analysis.")
        return
    fx = fx_risk_metrics(fx_prices)
    f1, f2, f3 = st.columns(3)
    f1.metric("Annualized FX volatility", f"{fx['annualized_volatility']:.2%}")
    f2.metric("Worst observed day", f"{fx['worst_day']:.2%}")
    f3.metric("FX drawdown", f"{fx['max_drawdown']:.2%}")

    exposure = st.number_input("Foreign-currency exposure at risk (₦ equivalent)", min_value=0.0, value=100_000_000.0, step=5_000_000.0)
    stress = fx_exposure_stress(exposure)
    stress["FX Shock"] = stress["FX Shock"].map(lambda x: f"{x:.1%}")
    stress["Naira Impact"] = stress["Naira Impact"].map(lambda x: f"₦{x:,.0f}")
    stress["Absolute Impact"] = stress["Absolute Impact"].map(lambda x: f"₦{x:,.0f}")
    st.dataframe(stress, use_container_width=True, hide_index=True)

    left, right = st.columns(2, gap="large")
    with left:
        if not fx["rolling_volatility"].empty:
            fig = go.Figure(go.Scatter(x=fx["rolling_volatility"].index, y=fx["rolling_volatility"], mode="lines", name="21-day FX volatility"))
            fig.update_layout(title="USD/NGN Rolling Volatility", yaxis_title="Annualized volatility", height=320)
            st.plotly_chart(fig, use_container_width=True)
    with right:
        stressed = liquidity_stress(cash, daily_outflow)
        st.markdown("#### Liquidity stress")
        view = stressed.copy()
        view["Outflow Multiplier"] = view["Outflow Multiplier"].map(lambda x: f"{x:.2f}x")
        view["Stressed Cash"] = view["Stressed Cash"].map(lambda x: f"₦{x:,.0f}")
        view["Daily Outflow"] = view["Daily Outflow"].map(lambda x: f"₦{x:,.0f}")
        view["Runway Days"] = view["Runway Days"].map(lambda x: f"{x:.1f}")
        st.dataframe(view, use_container_width=True, hide_index=True)

    level, alerts = risk_signal(fx["annualized_volatility"], lm["runway_days"])
    st.markdown("### Management signal")
    if level == "High attention":
        st.error(f"{level}: " + "; ".join(alerts))
    elif level == "Elevated":
        st.warning(f"{level}: " + "; ".join(alerts))
    else:
        st.success("Normal: no threshold breach in the current liquidity/FX monitor.")
    st.caption("FX shocks are scenario assumptions, not forecasts. Liquidity metrics depend on user-supplied treasury inputs.")
