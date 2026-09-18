from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from services import personal_finance
from services import personal_account_controls as account_controls
from services import personal_finance_wealth as wealth


def money(v: float, symbol: str = "₦") -> str:
    return f"{symbol}{float(v):,.2f}"


def render() -> None:
    personal_finance.ensure_schema()
    wealth.ensure_schema()
    s = personal_finance.settings()
    symbol = s["symbol"]
    today = date.today()

    st.title("💳 Personal Accounts")
    st.caption("Manage bank, cash, savings and investment accounts used by the Personal Finance workspace.")

    accts = personal_finance.accounts()
    balances = wealth.account_balances(today.isoformat())
    if not balances.empty:
        total = float(balances["balance"].sum())
        liquid = float(balances.loc[balances["account_type"].isin(["Cash", "Savings"]), "balance"].sum())
        investments = float(balances.loc[balances["account_type"] == "Investment", "balance"].sum())
    else:
        total = liquid = investments = 0.0

    a, b, c = st.columns(3)
    a.metric("Total Account Balances", money(total, symbol))
    b.metric("Cash & Savings", money(liquid, symbol))
    c.metric("Investment Accounts", money(investments, symbol))

    st.subheader("Add Account")
    with st.form("pf_add_account", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Account name")
        account_type = c2.selectbox("Account type", account_controls.ACCOUNT_TYPES)
        opening = c3.number_input(f"Opening balance ({symbol})", step=1000.0)
        if st.form_submit_button("Create Account", type="primary"):
            try:
                personal_finance.add_account(name, account_type, opening)
                st.success("Account created.")
                st.rerun()
            except (ValueError, Exception) as exc:
                st.error(str(exc))

    st.subheader("Account Register")
    accts = personal_finance.accounts()
    if accts.empty:
        st.info("No active personal accounts.")
        return

    balances = wealth.account_balances(today.isoformat())
    display = accts.merge(
        balances[["id", "movement", "balance"]],
        on="id",
        how="left",
        suffixes=("", "_calc"),
    )
    display["movement"] = display["movement"].fillna(0.0)
    display["balance"] = display["balance"].fillna(display["opening_balance"])
    st.dataframe(
        display[["id", "name", "account_type", "opening_balance", "movement", "balance"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Edit / Archive Account")
    options = {f"{row.name} (ID {int(row.id)})": int(row.id) for _, row in accts.iterrows()}
    selected_label = st.selectbox("Select account", list(options))
    account_id = options[selected_label]
    selected = accts.loc[accts["id"] == account_id].iloc[0]

    with st.form("pf_edit_account"):
        c1, c2, c3 = st.columns(3)
        edit_name = c1.text_input("Account name", str(selected["name"]))
        type_values = list(account_controls.ACCOUNT_TYPES)
        current_type = str(selected["account_type"])
        edit_type = c2.selectbox(
            "Account type",
            type_values,
            index=type_values.index(current_type) if current_type in type_values else 0,
        )
        edit_opening = c3.number_input(
            f"Opening balance ({symbol})",
            value=float(selected["opening_balance"]),
            step=1000.0,
        )
        if st.form_submit_button("Save Account Changes", type="primary"):
            try:
                account_controls.update_account(
                    account_id, edit_name, edit_type, edit_opening
                )
                st.success("Account updated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    usage = account_controls.account_usage(account_id)
    st.caption(
        f"Usage: {usage['transactions']} transactions • "
        f"{usage['transfers']} transfers • {usage['goals']} linked savings goals"
    )

    if usage["transactions"] == 0 and usage["transfers"] == 0 and usage["goals"] == 0:
        if st.button("Archive Unused Account", key=f"pf_archive_{account_id}"):
            try:
                account_controls.deactivate_account(account_id)
                st.success("Account archived.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("Accounts with historical activity are kept active so historical reporting is not broken.")

    st.caption(
        "CONTROL: account deletion is not offered. An unused account can be archived; "
        "accounts with historical activity remain available for reporting integrity."
    )
