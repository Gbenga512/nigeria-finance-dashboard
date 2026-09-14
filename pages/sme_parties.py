"""SME customers, suppliers and AR/AP workspace."""
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from ng_ui import hero
from services.sme_parties import (
    ar_ap_summary,
    create_invoice,
    create_party,
    invoice_register,
    list_parties,
    record_payment,
)
from services.sme_store import get_or_create_user, list_businesses


def _money(value: float) -> str:
    return f"₦{float(value):,.0f}"


def _party_form(business_id: int, party_type: str) -> None:
    with st.form(f"new_{party_type.lower()}_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input(f"{party_type} name *")
        contact = c2.text_input("Contact person")
        c3, c4 = st.columns(2)
        email = c3.text_input("Email")
        phone = c4.text_input("Phone")
        c5, c6 = st.columns(2)
        tax_id = c5.text_input("Tax ID / TIN")
        terms = c6.number_input("Payment terms (days)", min_value=0, value=30, step=1)
        credit = st.number_input("Credit limit (₦)", min_value=0.0, step=10000.0)
        address = st.text_area("Address", height=80)
        if st.form_submit_button(f"Add {party_type.lower()}", use_container_width=True, type="primary"):
            try:
                create_party(business_id, party_type, name, contact_name=contact, email=email, phone=phone, address=address, tax_id=tax_id, payment_terms_days=int(terms), credit_limit=credit)
                st.success(f"{party_type} added.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _invoice_form(business_id: int, party_type: str, parties: list[dict]) -> None:
    if not parties:
        st.info(f"Add a {party_type.lower()} first before creating an invoice.")
        return
    party_map = {p["name"]: int(p["id"]) for p in parties}
    with st.form(f"new_{party_type.lower()}_invoice", clear_on_submit=True):
        c1, c2 = st.columns(2)
        party_name = c1.selectbox(party_type, list(party_map))
        number = c2.text_input("Invoice number *", placeholder="INV-0001")
        c3, c4 = st.columns(2)
        invoice_date = c3.date_input("Invoice date", value=date.today())
        due_date = c4.date_input("Due date", value=date.today())
        description = st.text_input("Description *")
        c5, c6 = st.columns(2)
        subtotal = c5.number_input("Subtotal (₦)", min_value=0.01, step=1000.0)
        tax = c6.number_input("Tax / VAT (₦)", min_value=0.0, step=100.0)
        notes = st.text_area("Notes", height=70)
        if st.form_submit_button(f"Create {party_type.lower()} invoice", use_container_width=True, type="primary"):
            try:
                create_invoice(business_id, party_map[party_name], number, invoice_date.isoformat(), description, subtotal, tax, due_date.isoformat(), notes)
                st.success("Invoice recorded in the operational subledger.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _register(business_id: int, party_type: str) -> None:
    df = invoice_register(business_id, party_type)
    st.markdown(f"### {party_type} invoices")
    if df.empty:
        st.info(f"No {party_type.lower()} invoices recorded yet.")
        return
    open_df = df[df["outstanding"] > 0].copy()
    cols = st.columns(3)
    cols[0].metric("Invoiced", _money(df["total_amount"].sum()))
    cols[1].metric("Outstanding", _money(df["outstanding"].sum()))
    cols[2].metric("Overdue", _money(df.loc[df["days_overdue"] > 0, "outstanding"].sum()))
    display = df.copy()
    display["Total"] = display["total_amount"].map(_money)
    display["Paid"] = display["paid_amount"].map(_money)
    display["Outstanding"] = display["outstanding"].map(_money)
    display["Due"] = display["due_date"].dt.strftime("%d %b %Y")
    display["Age"] = display["age_bucket"].astype(str)
    st.dataframe(display[["invoice_number", "party_name", "invoice_date", "Due", "description", "Total", "Paid", "Outstanding", "Age", "status"]], use_container_width=True, hide_index=True)

    if not open_df.empty:
        options = {f"{r['invoice_number']} · {r['party_name']} · {_money(r['outstanding'])}": int(r['id']) for _, r in open_df.iterrows()}
        selected = st.selectbox("Record operational payment", list(options), key=f"payment_{party_type}")
        invoice_id = options[selected]
        outstanding = float(open_df.loc[open_df["id"] == invoice_id, "outstanding"].iloc[0])
        amount = st.number_input("Payment amount (₦)", min_value=0.01, max_value=max(0.01, outstanding), value=min(outstanding, 1000.0), step=100.0, key=f"payment_amount_{party_type}")
        st.caption("Payment updates the AR/AP operational subledger. General-ledger cash and receivable/payable journals remain a separate accounting-posting step.")
        if st.button("Record payment", key=f"record_payment_{party_type}", use_container_width=True, type="primary"):
            try:
                record_payment(business_id, invoice_id, amount)
                st.success("Payment recorded.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def render() -> None:
    hero("Customers, Suppliers & AR/AP", "Manage counterparties, invoice balances and ageing before connecting approved activity to the accounting ledger.", "SME subledgers")
    user_id = get_or_create_user()
    businesses = list_businesses(user_id)
    if not businesses:
        st.info("Create a business profile in SME Finance first.")
        return
    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    selected = st.selectbox("Active business", labels, key="sme_parties_business")
    business_id = int(businesses[labels.index(selected)]["id"])
    summary = ar_ap_summary(business_id)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Accounts receivable", _money(summary["accounts_receivable"]))
    k2.metric("Accounts payable", _money(summary["accounts_payable"]))
    k3.metric("Overdue receivables", _money(summary["overdue_receivables"]))
    k4.metric("Overdue payables", _money(summary["overdue_payables"]))

    tabs = st.tabs(["Customers", "Suppliers", "AR invoices", "AP invoices"])
    customers = list_parties(business_id, "Customer")
    suppliers = list_parties(business_id, "Supplier")
    with tabs[0]:
        _party_form(business_id, "Customer")
        if customers:
            st.dataframe(pd.DataFrame(customers)[["name", "contact_name", "email", "phone", "payment_terms_days", "credit_limit"]], use_container_width=True, hide_index=True)
    with tabs[1]:
        _party_form(business_id, "Supplier")
        if suppliers:
            st.dataframe(pd.DataFrame(suppliers)[["name", "contact_name", "email", "phone", "payment_terms_days", "credit_limit"]], use_container_width=True, hide_index=True)
    with tabs[2]:
        _invoice_form(business_id, "Customer", customers)
        _register(business_id, "Customer")
    with tabs[3]:
        _invoice_form(business_id, "Supplier", suppliers)
        _register(business_id, "Supplier")

    st.info("AR/AP in this release is an operational subledger. It does not automatically alter the general ledger; approved accounting posting will be added as part of the controlled invoice-to-ledger workflow.")
    st.caption("NG Finance Pro is a financial-management and analytics tool and does not provide tax advice or regulated financial services.")
