"""Budget analysis for both SME ledger data and ad-hoc planning files."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ng_ui import hero
from services.sme_accounting import account_catalog
from services.sme_budget import create_budget, list_budgets, variance_report
from services.sme_store import get_or_create_user, list_businesses


def _uploaded_budget(upload):
    df = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"Department", "Budget", "Actual"}
    if not required.issubset(df.columns):
        raise ValueError("File must contain Department, Budget and Actual columns.")
    df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce")
    df["Actual"] = pd.to_numeric(df["Actual"], errors="coerce")
    return df.dropna(subset=["Budget", "Actual"]).copy()


def _ledger_budget(business_id: int, budget_id: int) -> pd.DataFrame:
    report = variance_report(business_id, budget_id).copy()
    if report.empty:
        return report
    report["Favourability"] = report.apply(
        lambda r: "Favourable" if (
            (r["Type"] == "Revenue" and r["Variance"] >= 0)
            or (r["Type"] == "Expense" and r["Variance"] <= 0)
        ) else "Unfavourable" if r["Type"] in {"Revenue", "Expense"} else "Review",
        axis=1,
    )
    return report


def render():
    hero("Budget & Planning", "Connect budget control to SME ledger data, or analyse a standalone planning file without fabricating results.", "Planning workspace")

    user_id = get_or_create_user()
    businesses = list_businesses(user_id)
    if businesses:
        labels = [f"{b['name']} · {b['currency']}" for b in businesses]
        label = st.selectbox("Active SME business", labels, key="budget_business")
        business_id = int(businesses[labels.index(label)]["id"])

        st.markdown("### Budget register")
        budgets = list_budgets(business_id)
        if budgets.empty:
            st.info("No SME budgets have been created yet. Create one below or analyse an uploaded planning file.")
        else:
            budget_labels = [f"{r['name']} · {r['period_start']} → {r['period_end']} · {r['status']}" for _, r in budgets.iterrows()]
            selected = st.selectbox("Budget", budget_labels, key="selected_budget")
            budget_id = int(budgets.iloc[budget_labels.index(selected)]["id"])
            report = _ledger_budget(business_id, budget_id)
            if not report.empty:
                revenue = report[report["Type"] == "Revenue"]
                expense = report[report["Type"] == "Expense"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Revenue budget", f"₦{revenue['Budget'].sum():,.0f}")
                c2.metric("Revenue actual", f"₦{revenue['Actual'].sum():,.0f}")
                c3.metric("Expense budget", f"₦{expense['Budget'].sum():,.0f}")
                c4.metric("Expense actual", f"₦{expense['Actual'].sum():,.0f}")
                st.dataframe(report, use_container_width=True, hide_index=True)
                st.caption("Revenue variance is favourable when actual revenue exceeds budget. Expense variance is favourable when actual expense is below budget.")

        with st.expander("Create SME budget"):
            accounts = account_catalog(business_id)
            choices = [f"{r['name']} · {r['statement_type']}" for _, r in accounts.iterrows() if r["statement_type"] in {"Revenue", "Expense"}]
            if not choices:
                st.info("No budgetable accounts are available.")
            else:
                with st.form("create_sme_budget"):
                    name = st.text_input("Budget name", value="Monthly Operating Budget")
                    period = st.date_input("Budget period", value=(pd.Timestamp.today().replace(day=1).date(), pd.Timestamp.today().date()))
                    selected_accounts = st.multiselect("Budget accounts", choices, default=choices)
                    lines = []
                    for choice in selected_accounts:
                        row = accounts.iloc[choices.index(choice)]
                        amount = st.number_input(f"Budget — {row['name']} (₦)", min_value=0.0, step=1000.0, key=f"budget_amt_{int(row['id'])}")
                        lines.append({"account_id": int(row["id"]), "amount": amount})
                    submit = st.form_submit_button("Create budget", use_container_width=True)
                    if submit:
                        try:
                            create_budget(business_id, name, period[0], period[1], lines)
                            st.success("Budget created.")
                            st.rerun()
                        except (ValueError, TypeError, IndexError) as exc:
                            st.error(str(exc))

    st.markdown("### Standalone planning analysis")
    upload = st.file_uploader("Upload budget / actual data", type=["csv", "xlsx"], key="budget_upload")
    if not upload:
        st.info("Upload a planning file to analyse it. No demo figures are shown when no source data is supplied.")
        return
    try:
        df = _uploaded_budget(upload)
    except Exception as exc:
        st.error(str(exc))
        return
    if df.empty:
        st.warning("No valid budget rows were found.")
        return
    df["Variance"] = df["Actual"] - df["Budget"]
    df["Variance %"] = df["Variance"].div(df["Budget"].replace(0, pd.NA)) * 100
    overspend = float(df.loc[df["Variance"] > 0, "Variance"].sum())
    utilization = df["Actual"].sum() / df["Budget"].sum() if df["Budget"].sum() else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Total budget", f"₦{df['Budget'].sum():,.0f}")
    c2.metric("Actual spend", f"₦{df['Actual'].sum():,.0f}")
    c3.metric("Gross overspend", f"₦{overspend:,.0f}")
    st.metric("Budget utilization", "N/A" if utilization is None else f"{utilization:.1%}")
    fig = go.Figure()
    fig.add_bar(x=df["Department"], y=df["Budget"], name="Budget")
    fig.add_bar(x=df["Department"], y=df["Actual"], name="Actual")
    fig.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="₦", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("Standalone variance is Actual − Budget. For expense budgets, positive variance indicates overspend.")
