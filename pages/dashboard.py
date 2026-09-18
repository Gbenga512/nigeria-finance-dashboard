import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ng_ui import hero


def _asset_class(asset: str) -> str:
    if "BTC" in asset or "ETH" in asset:
        return "CRYPTO"
    if asset in {"Gold", "Crude Oil"}:
        return "COMMODITY"
    return "FX"


def _fmt(value):
    return "N/A" if pd.isna(value) else f"{value:,.2f}"


def _change_class(value):
    return "ng-positive" if value > 0 else "ng-negative" if value < 0 else "ng-neutral"


def render(snapshot: pd.DataFrame, insight: str):
    hero(
        "Financial Command Centre",
        "One operating view for market context, financial health, liquidity, risk and the decisions that need attention.",
        "Live market feed",
    )

    now = datetime.now().strftime("%d %b %Y • %H:%M")
    st.markdown(
        f'<div class="ng-command"><span><span class="ng-command-kicker">Executive view</span> · {now}</span><span class="ng-live-dot">Data refresh active</span></div>',
        unsafe_allow_html=True,
    )

    if snapshot.empty:
        st.warning("Market data is temporarily unavailable. Please refresh shortly.")
        return

    valid = snapshot["Change %"].dropna()
    up = int((valid > 0).sum())
    down = int((valid < 0).sum())
    flat = int((valid == 0).sum())
    breadth = up - down
    breadth_label = "Positive breadth" if breadth > 0 else "Negative breadth" if breadth < 0 else "Balanced breadth"
    breadth_class = "ng-positive" if breadth > 0 else "ng-negative" if breadth < 0 else "ng-neutral"

    # A compact market ticker gives the home screen a living terminal feel without inventing data.
    ticker_html = '<div class="ng-ticker">'
    for _, row in snapshot.iterrows():
        change = row["Change %"]
        ticker_html += (
            f'<div class="ng-ticker-item"><div class="ng-ticker-name">{row["Asset"]}</div>'
            f'<div class="ng-ticker-price">{_fmt(row["Price"])}</div>'
            f'<div class="ng-ticker-change {_change_class(change) if pd.notna(change) else "ng-muted"}">'
            f'{"N/A" if pd.isna(change) else f"{change:+.2f}%"}'
            f'</div></div>'
        )
    ticker_html += "</div>"
    st.markdown(ticker_html, unsafe_allow_html=True)

    st.markdown('<div class="ng-section-label">At a glance</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4, gap="small")
    kpis = [
        ("Market breadth", breadth_label, f"{up} gainers · {down} decliners · {flat} flat", breadth_class),
        ("Tracked assets", str(len(snapshot)), "Across the current market universe", "ng-neutral"),
        ("Live observations", str(int((snapshot["Data"] == "Live").sum())) if "Data" in snapshot else "N/A", "Current snapshot availability", "ng-positive"),
        ("Largest move", f"{valid.abs().max():.2f}%" if not valid.empty else "N/A", "Absolute daily movement", "ng-neutral"),
    ]
    for col, (title, value, meta, css) in zip((k1, k2, k3, k4), kpis):
        with col:
            st.markdown(
                f'<div class="ng-card ng-kpi"><div class="ng-card-title">{title}</div><div class="ng-card-value {css}">{value}</div><div class="ng-kpi-meta">{meta}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="ng-section-label">Decision layer</div>', unsafe_allow_html=True)
    left, right = st.columns([1.45, 1], gap="large")

    with left:
        st.markdown("### What needs attention")
        alerts = []
        if not valid.empty:
            largest = snapshot.loc[snapshot["Change %"].abs().idxmax()]
            alerts.append(("Market movement", f'{largest["Asset"]} has the largest observed daily move at {largest["Change %"]:+.2f}%.'))
        alerts.append(("Data quality", f'{len(snapshot) - len(valid)} tracked observations currently have no daily movement value.' if len(snapshot) != len(valid) else "All tracked observations have daily movement data."))
        alerts.append(("Next workflow", "Use Intelligence Centre, Risk Monitor or Treasury when a dashboard signal requires investigation."))
        for title, copy in alerts:
            st.markdown(f'<div class="ng-alert"><div class="ng-alert-title">{title}</div><div class="ng-alert-copy">{copy}</div></div>', unsafe_allow_html=True)

    with right:
        st.markdown("### Market pulse")
        st.markdown(
            f'<div class="ng-card"><div class="ng-card-title">Current breadth</div>'
            f'<div class="ng-card-value {breadth_class}">{breadth_label}</div>'
            f'<div class="ng-muted">Based only on observations available in the current snapshot.</div>'
            f'<hr style="border-color:rgba(148,163,184,.10);margin:16px 0">'
            f'<div style="display:flex;justify-content:space-between"><span class="ng-positive">Gainers&nbsp; {up}</span><span class="ng-neutral">Flat&nbsp; {flat}</span><span class="ng-negative">Decliners&nbsp; {down}</span></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ng-section-label">Market intelligence</div>', unsafe_allow_html=True)
    chart_col, table_col = st.columns([1.35, 1], gap="large")

    with chart_col:
        st.markdown("### Performance map")
        chart_df = snapshot.dropna(subset=["Change %"]).copy().sort_values("Change %")
        fig = go.Figure(
            go.Bar(
                x=chart_df["Change %"],
                y=chart_df["Asset"],
                orientation="h",
                text=chart_df["Change %"].map(lambda x: f"{x:+.2f}%"),
                textposition="outside",
                hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
                marker_line_width=0,
            )
        )
        fig.update_layout(
            height=360,
            margin=dict(l=4, r=45, t=8, b=8),
            xaxis_title="Daily change (%)",
            yaxis_title=None,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#91a4bb"),
            xaxis=dict(gridcolor="rgba(148,163,184,.10)", zerolinecolor="rgba(148,163,184,.18)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

    with table_col:
        st.markdown("### Market watchlist")
        display = snapshot.copy()
        display["Class"] = display["Asset"].map(_asset_class)
        display["Price"] = display["Price"].map(_fmt)
        display["Change %"] = display["Change %"].map(lambda x: "N/A" if pd.isna(x) else f"{x:+.2f}%")
        display = display[["Asset", "Class", "Price", "Change %", "Data"]]
        st.dataframe(display, use_container_width=True, hide_index=True, height=360)

    st.markdown('<div class="ng-section-label">Analyst layer</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ng-card"><div class="ng-card-title">RULE-BASED FINANCIAL CONTEXT</div>'
        f'<div style="font-size:.98rem;line-height:1.75;margin-top:8px;color:#dce5ee">{insight}</div>'
        f'<div class="ng-muted" style="margin-top:10px">The analyst layer is grounded in the available dataset. It does not invent missing financial observations.</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ng-section-label">Move from insight to action</div>', unsafe_allow_html=True)
    actions = [
        ("📘", "Management Accounts", "Review revenue, margin, working capital and operating performance.", "📘  SME Management Accounts"),
        ("💧", "Treasury", "Investigate cash position, liquidity and cash-flow scenarios.", "💧  Treasury Dashboard"),
        ("🛡", "Risk Monitor", "Open quantitative market-risk indicators and stress analysis.", "🛡️  Risk Monitor"),
        ("🧠", "Intelligence Centre", "Move from market observations into explainable signals.", "🧠  Intelligence Centre"),
    ]
    action_cols = st.columns(4, gap="small")
    for col, (icon, title, copy, target) in zip(action_cols, actions):
        with col:
            st.markdown(f'<div class="ng-action"><div style="font-size:1.15rem">{icon}</div><div class="ng-action-title">{title}</div><div class="ng-action-copy">{copy}</div></div>', unsafe_allow_html=True)
            if st.button("Open", key=f"home_action_{target}", use_container_width=True):
                st.session_state["ng_nav_target"] = target
                st.rerun()

    st.caption("Market context only — not personalized investment advice.")
