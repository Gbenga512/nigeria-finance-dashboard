import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ng_ui import hero


def _asset_class(asset: str) -> str:
    if "BTC" in asset or "ETH" in asset:
        return "CRYPTO"
    if asset in {"Gold", "Crude Oil"}:
        return "COMMODITY"
    return "FX"


def render(snapshot: pd.DataFrame, insight: str):
    hero(
        "Executive Dashboard",
        "A unified command centre for markets, treasury, risk and financial decision support.",
        "Live market feed",
    )

    if snapshot.empty:
        st.warning("Market data is temporarily unavailable. Please refresh shortly.")
        return

    cols = st.columns(min(5, len(snapshot)), gap="small")
    for col, (_, row) in zip(cols, snapshot.iterrows()):
        price = row["Price"]
        change = row["Change %"]
        direction = "▲" if pd.notna(change) and change > 0 else "▼" if pd.notna(change) and change < 0 else "—"
        css = "ng-positive" if direction == "▲" else "ng-negative" if direction == "▼" else "ng-neutral"
        with col:
            st.markdown(
                f"""
                <div class="ng-card">
                    <div class="ng-card-title">{_asset_class(row['Asset'])} • {row['Asset']}</div>
                    <div class="ng-card-value">{'N/A' if pd.isna(price) else f'{price:,.2f}'}</div>
                    <div class="{css}">{direction} {'N/A' if pd.isna(change) else f'{change:+.2f}%'} <span class="ng-muted">today</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="ng-section-label">Market intelligence</div>', unsafe_allow_html=True)
    left, right = st.columns([1.75, 1], gap="large")

    with left:
        st.markdown("### Performance snapshot")
        chart_df = snapshot.dropna(subset=["Change %"]).copy().sort_values("Change %")
        fig = go.Figure(go.Bar(x=chart_df["Change %"], y=chart_df["Asset"], orientation="h", text=chart_df["Change %"].map(lambda x: f"{x:+.2f}%"), textposition="outside", hovertemplate="%{y}: %{x:+.2f}%<extra></extra>", marker_line_width=0))
        fig.update_layout(height=340, margin=dict(l=8, r=42, t=8, b=8), xaxis_title="Daily change (%)", yaxis_title=None, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#91a4bb"), xaxis=dict(gridcolor="rgba(148,163,184,.10)", zerolinecolor="rgba(148,163,184,.18)"), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

    with right:
        st.markdown("### Market pulse")
        up = int((snapshot["Change %"] > 0).sum())
        down = int((snapshot["Change %"] < 0).sum())
        flat = int((snapshot["Change %"] == 0).sum())
        valid = int(snapshot["Change %"].notna().sum())
        net = up - down
        sentiment = "Positive" if net > 0 else "Negative" if net < 0 else "Balanced"
        sentiment_class = "ng-positive" if net > 0 else "ng-negative" if net < 0 else "ng-neutral"
        st.markdown(f"<div class=\"ng-card\"><div class=\"ng-card-title\">Current breadth</div><div class=\"ng-card-value {sentiment_class}\">{sentiment}</div><div class=\"ng-muted\">{valid} tracked assets with available movement data</div><hr style=\"border-color:rgba(148,163,184,.10); margin:16px 0\"><div style=\"display:flex;justify-content:space-between\"><span class=\"ng-positive\">Gainers&nbsp; {up}</span><span class=\"ng-neutral\">Flat&nbsp; {flat}</span><span class=\"ng-negative\">Decliners&nbsp; {down}</span></div></div>", unsafe_allow_html=True)
        st.markdown("### Data status")
        st.markdown("<div class='ng-card'><span class='ng-positive'>● Connected</span><br><span class='ng-muted'>Market snapshot refreshed automatically. Values are informational.</span></div>", unsafe_allow_html=True)

    st.markdown('<div class="ng-section-label">Portfolio of information</div>', unsafe_allow_html=True)
    st.markdown("### Market watchlist")
    display = snapshot.copy()
    display["Class"] = display["Asset"].map(_asset_class)
    display["Price"] = display["Price"].map(lambda x: "N/A" if pd.isna(x) else f"{x:,.2f}")
    display["Change %"] = display["Change %"].map(lambda x: "N/A" if pd.isna(x) else f"{x:+.2f}%")
    display = display[["Asset", "Class", "Price", "Change %", "Data"]]
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.markdown("### Analyst intelligence")
    st.markdown(f"<div class='ng-card'><div class='ng-card-title'>RULE-BASED FINANCIAL CONTEXT</div><div style='font-size:1rem;line-height:1.75;margin-top:8px'>{insight}</div></div>", unsafe_allow_html=True)
    st.caption("Market context only — not personalized investment advice.")

    st.markdown("### Quick actions")
    actions = [
        ("📋 Statements", "📋  Financial Statement Analyzer", "Review financial statement analytics."),
        ("💧 Treasury", "💧  Treasury Dashboard", "Review liquidity and cash-position tools."),
        ("↔ Reconciliation", "↔️  Bank Reconciliation", "Run a bank-versus-cashbook reconciliation."),
        ("🛡 Risk", "🛡️  Risk Monitor", "Review current market-risk indicators."),
    ]
    action_cols = st.columns(2 if len(actions) > 2 else len(actions), gap="small")
    for col, (label, target, help_text) in zip(action_cols, actions):
        with col:
            if st.button(label, use_container_width=True, help=help_text, key=f"quick_{target}"):
                st.session_state["ng_nav_target"] = target
                st.rerun()
