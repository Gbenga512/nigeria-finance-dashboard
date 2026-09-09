import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from ng_ui import hero


def render():
    hero("Budget & Planning", "Turn budget-versus-actual data into a management view of spending discipline and variance.", "Planning workspace")
    upload = st.file_uploader("Upload budget / actual data", type=["csv", "xlsx"])
    if upload:
        df = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
        df.columns = [str(c).strip() for c in df.columns]
        required = {"Department", "Budget", "Actual"}
        if not required.issubset(df.columns):
            st.error("File must contain Department, Budget and Actual columns.")
            return
    else:
        df = pd.DataFrame({"Department": ["Finance", "HR", "Operations"], "Budget": [5_000_000, 3_000_000, 8_000_000], "Actual": [4_500_000, 3_500_000, 7_600_000]})
        st.caption("Demo data is shown until you upload your own planning file.")
    df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce")
    df["Actual"] = pd.to_numeric(df["Actual"], errors="coerce")
    df = df.dropna(subset=["Budget", "Actual"]).copy()
    if df.empty:
        st.warning("No valid budget rows were found.")
        return
    df["Variance"] = df["Actual"] - df["Budget"]
    df["Variance %"] = df["Variance"].div(df["Budget"].replace(0, pd.NA)) * 100
    overspend = float(df.loc[df["Variance"] > 0, "Variance"].sum())
    underspend = float(-df.loc[df["Variance"] < 0, "Variance"].sum())
    utilization = df["Actual"].sum() / df["Budget"].sum() if df["Budget"].sum() else None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total budget", f"₦{df['Budget'].sum():,.0f}")
    c2.metric("Actual spend", f"₦{df['Actual'].sum():,.0f}")
    c3.metric("Gross overspend", f"₦{overspend:,.0f}")
    c4.metric("Budget utilization", "N/A" if utilization is None else f"{utilization:.1%}")
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        fig = go.Figure()
        fig.add_bar(x=df["Department"], y=df["Budget"], name="Budget")
        fig.add_bar(x=df["Department"], y=df["Actual"], name="Actual")
        fig.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="₦", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Variance summary")
        st.metric("Overspend", f"₦{overspend:,.0f}")
        st.metric("Underspend", f"₦{underspend:,.0f}")
        st.caption("Positive variance indicates actual spending above budget in this expense-oriented view.")
    display = df.copy()
    display["Budget"] = display["Budget"].map(lambda x: f"₦{x:,.0f}")
    display["Actual"] = display["Actual"].map(lambda x: f"₦{x:,.0f}")
    display["Variance"] = display["Variance"].map(lambda x: f"₦{x:,.0f}")
    display["Variance %"] = display["Variance %"].map(lambda x: "N/A" if pd.isna(x) else f"{x:+.1f}%")
    st.markdown("### Department performance")
    st.dataframe(display, use_container_width=True, hide_index=True)
