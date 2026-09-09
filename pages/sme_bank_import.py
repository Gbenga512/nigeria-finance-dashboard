"""Phase 2 bank statement import with lazy SME-store imports."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from services.sme_import import parse_statement, detect_existing_duplicates, suggest_categories
import services.sme_store as sme_store
from ng_ui import hero


def render() -> None:
    hero("SME Bank Statement Import", "Import statements safely: review, categorize and confirm before anything reaches the ledger.", "SME Finance")
    user_id = sme_store.get_or_create_user()
    businesses = sme_store.list_businesses(user_id)
    if not businesses:
        st.info("Create an SME business profile first.")
        return
    labels = [f"{b['name']} · {b['currency']}" for b in businesses]
    label = st.selectbox("Active business", labels, key="sme_import_business")
    business = businesses[labels.index(label)]
    business_id = int(business["id"])
    uploaded = st.file_uploader("Upload bank statement", type=["csv", "xlsx", "xls"], help="CSV or Excel only in this release. PDF extraction will be added after a reliable parser is selected.")
    if uploaded is None:
        st.info("Nothing is posted automatically. Upload a statement to begin the review workflow.")
        return
    try:
        existing = sme_store.transactions_df(business_id)
        review = parse_statement(uploaded.getvalue(), uploaded.name)
        review = detect_existing_duplicates(review, existing)
        review = suggest_categories(review, existing)
    except (ValueError, ImportError) as exc:
        st.error(str(exc))
        return
    st.success(f"Parsed {len(review):,} row(s). Review before posting.")
    st.caption("Workflow: Upload → Parse → Preview → Categorize → Duplicate check → Confirm → Post")
    if review.empty:
        return
    editable = review[["transaction_date", "description", "amount", "transaction_type", "reference", "suggested_category", "existing_duplicate", "duplicate", "valid"]].copy()
    editable = editable.rename(columns={"suggested_category": "category"})
    edited = st.data_editor(editable, use_container_width=True, hide_index=True, num_rows="fixed", column_config={
        "transaction_date": st.column_config.TextColumn("Date", disabled=True),
        "description": st.column_config.TextColumn("Description", disabled=True),
        "amount": st.column_config.NumberColumn("Amount", min_value=0, disabled=True),
        "transaction_type": st.column_config.SelectboxColumn("Type", options=["Income", "Expense", "Transfer"]),
        "reference": st.column_config.TextColumn("Reference"),
        "category": st.column_config.TextColumn("Category"),
        "existing_duplicate": st.column_config.CheckboxColumn("Existing duplicate", disabled=True),
        "duplicate": st.column_config.CheckboxColumn("Duplicate in file", disabled=True),
        "valid": st.column_config.CheckboxColumn("Valid", disabled=True),
    }, key="sme_import_editor")
    invalid = int((~edited["valid"]).sum())
    duplicates = int((edited["existing_duplicate"] | edited["duplicate"]).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(edited)); c2.metric("Invalid", invalid); c3.metric("Duplicate flags", duplicates)
    if invalid:
        st.warning("Invalid rows will not be posted.")
    if duplicates:
        st.warning("Duplicate-flagged rows are excluded from posting.")
    if st.button("Confirm & Post Reviewed Transactions", type="primary", use_container_width=True):
        safe = edited[edited["valid"] & ~edited["existing_duplicate"] & ~edited["duplicate"]].copy()
        posted = sme_store.bulk_add_transactions(business_id, safe.to_dict("records"))
        st.success(f"Confirmed and posted {posted:,} transaction(s).")
        st.rerun()
