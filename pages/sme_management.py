"""Phase 3 SME management accounts, cash forecasting and budget control."""
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.sme_cashflow_v2 import forecast_13_weeks
from analytics.sme_management_accounts import management_accounts
from ng_ui import hero
from services.sme_accounting import account_catalog, balance_sheet, ensure_standard_accounts, journal_entries_df
from services.sme_budget import create_budget, list_budgets, variance_report
from services.sme_store import get_or_create_user, list_businesses, list_accounts, transactions_df


def money(v):
    return f"₦{float(v):,.0f}"


def _period():
    today = date.today()
    choice = st.selectbox("Reporting period", ["This month", "Last month", "Quarter", "Year", "Custom"], key="mgmt_period")
    if choice == "This month": return today.replace(day=1), today
    if choice == "Last month":
        end = today.replace(day=1) - timedelta(days=1); return end.replace(day=1), end
    if choice == "Quarter": return today - timedelta(days=89), today
    if choice == "Year": return today.replace(month=1, day=1), today
    value = st.date_input("Custom period", value=(today.replace(day=1), today), key="mgmt_custom")
    return value[0], value[1]


def render():
    hero("SME Management Accounts", "Management reporting, 13-week liquidity forecasting and budget control from the posted accounting ledger.", "Management Accounts")
    user = get_or_create_user(); businesses = list_businesses(user)
    if not businesses:
        st.info("Create a business in SME Finance Department first.")
        return
    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    selected = st.selectbox("Active business", labels, key="mgmt_business")
    business = businesses[labels.index(selected)]; bid = int(business["id"])
    ensure_standard_accounts(bid)
    start, end = _period()
    report = management_accounts(bid, start, end); k = report["kpis"]

    cards = st.columns(6)
    for c, label, value in zip(cards, ["Revenue","Gross Profit","Net Income","Cash","Working Capital","Current Ratio"], [k["revenue"],k["gross_profit"],k["net_income"],k["cash"],k["working_capital"],k["current_ratio"]]):
        c.metric(label, "N/A" if value is None else (money(value) if label != "Current Ratio" else f"{value:.2f}x"))
    st.caption(f"{start:%d %b %Y} → {end:%d %b %Y} • FACT values come from posted journals; ratios are CALCULATIONs.")

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("### Profitability & liquidity")
        df = pd.DataFrame({"Metric":["Revenue","COGS","Gross profit","Operating expenses","Net income","Cash flow"],"Amount":[k["revenue"],k["cogs"],k["gross_profit"],k["operating_expenses"],k["net_income"],k["cash_flow"]]})
        st.dataframe(df.style.format({"Amount":"₦{:,.0f}"}), use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Rule-based risk watch")
        for r in report["risks"]:
            st.warning(f"**{r['Risk']}** — {r['WHY']}")
        st.markdown("### Recommended actions")
        for r in report["recommendations"]: st.write(f"• {r}")

    st.markdown("---")
    st.markdown("## 13-Week Cash Flow Forecast")
    tx = transactions_df(bid)
    forecast = forecast_13_weeks(tx, as_of=end, opening_cash=k["cash"])
    fdf = forecast["forecast"]
    st.info(f"{forecast['status']} • ESTIMATE — {forecast['assumption']}")
    if fdf.empty:
        st.warning("Insufficient transaction history for a forecast.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fdf["Week"], y=fdf["Closing Cash"], mode="lines+markers", name="Projected closing cash"))
        fig.update_layout(height=330, yaxis_title="₦", title="Projected Closing Cash")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.dataframe(fdf.style.format({c:"₦{:,.0f}" for c in ["Opening Cash","Expected Inflow","Expected Outflow","Net Cash Flow","Closing Cash"]}), use_container_width=True, hide_index=True)
        st.download_button("Download 13-week forecast CSV", fdf.to_csv(index=False).encode("utf-8"), "ng_finance_13_week_cashflow.csv", "text/csv")

    st.markdown("---")
    st.markdown("## Budget & Variance Control")
    accounts = list_accounts(bid); account_map = {a["name"]: int(a["id"]) for a in accounts}
    tab1, tab2 = st.tabs(["Create budget", "Variance report"])
    with tab1:
        with st.form("sme_budget_form"):
            name = st.text_input("Budget name", value=f"{start:%b %Y} Operating Budget")
            b1,b2 = st.columns(2); pstart = b1.date_input("Budget start", start); pend = b2.date_input("Budget end", end)
            choices = st.multiselect("Accounts to budget", list(account_map), default=[x for x in ["Sales Revenue","Operating Expenses","Payroll","Rent","Utilities"] if x in account_map])
            lines = []
            for name_ in choices:
                amount = st.number_input(f"Budget — {name_} (₦)", min_value=0.0, step=10000.0, key=f"budget_{name_}")
                lines.append({"account_id": account_map[name_], "amount": amount})
            save = st.form_submit_button("Save active budget", use_container_width=True)
            if save:
                try:
                    create_budget(bid, name, pstart, pend, lines)
                    st.success("Budget saved."); st.rerun()
                except ValueError as exc: st.error(str(exc))
    with tab2:
        budgets = list_budgets(bid)
        if budgets.empty:
            st.info("No SME budgets yet. Create one to activate variance reporting.")
        else:
            labels2 = {int(r.id): f"{r['name']} · {r['period_start']} → {r['period_end']}" for _, r in budgets.iterrows()}
            chosen = st.selectbox("Budget", list(labels2), format_func=lambda x: labels2[x])
            vr = variance_report(bid, chosen)
            if vr.empty: st.info("No budget lines found.")
            else:
                st.dataframe(vr.style.format({c:"₦{:,.0f}" for c in ["Budget","Actual","Variance"]}, na_rep="N/A"), use_container_width=True, hide_index=True)
                st.caption("Variance = Actual − Budget. Direction is a control flag; revenue and expense favourability should be interpreted by account type.")
                st.download_button("Download variance CSV", vr.to_csv(index=False).encode("utf-8"), "ng_finance_budget_variance.csv", "text/csv")

    st.caption("ESTIMATEs are clearly separated from FACTs. This module provides management decision support and is not tax, audit, investment or other regulated professional advice.")
