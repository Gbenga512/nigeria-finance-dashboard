"""Intelligent finance data workspace for uploading, profiling, and validating datasets."""

from __future__ import annotations

import streamlit as st

from analytics.finance_data import (
    CANONICAL_COLUMNS,
    classify_dataset,
    normalize_finance_data,
    read_uploaded_file,
    suggest_column_mapping,
    validate_finance_data,
)


def render() -> None:
    st.title("Finance Data Workspace")
    st.caption("Bring company financial data into NG Finance Pro, identify its purpose, map it to a common schema, and validate it before analysis.")

    uploaded = st.file_uploader(
        "Upload financial data",
        type=["csv", "xlsx"],
        help="CSV and XLSX files are supported. Your file is processed for the current session only.",
    )
    if uploaded is None:
        st.info("Upload a transaction, bank statement, budget, ledger, or financial-statement export to begin.")
        st.markdown("**Supported dataset types:** Bank Statement • General Ledger • Budget • Transaction Export • Financial Statement")
        st.markdown("**Expected finance fields:** date, account, description, debit, credit, amount, currency, category, reference, entity.")
        return

    try:
        raw = read_uploaded_file(uploaded, uploaded.name)
    except Exception as exc:
        st.error(f"Unable to read this file: {exc}")
        return

    if raw.empty:
        st.warning("The uploaded file contains no rows.")
        return

    st.subheader("1. Source preview")
    st.dataframe(raw.head(20), use_container_width=True)

    profile = classify_dataset(raw.columns.tolist())
    st.subheader("2. Dataset intelligence")
    c1, c2, c3 = st.columns(3)
    c1.metric("Detected type", profile.label)
    c2.metric("Classification confidence", f"{profile.confidence}%")
    c3.metric("Recommended route", profile.route)
    if profile.reasons:
        st.caption("Why: " + " • ".join(profile.reasons))
    if profile.missing_required_fields:
        st.warning("Expected fields still missing: " + ", ".join(profile.missing_required_fields))
    elif profile.dataset_type != "unknown":
        st.success("The dataset has the core fields expected for its detected finance workflow.")

    st.subheader("3. Column mapping")
    st.caption("Review the automatically suggested mapping. You can override any field before validation.")
    suggested = suggest_column_mapping(raw.columns.tolist())
    mapping: dict[str, str] = {}
    for canonical in CANONICAL_COLUMNS:
        options = ["—"] + raw.columns.tolist()
        default = suggested.get(canonical)
        index = options.index(default) if default in options else 0
        selected = st.selectbox(canonical.replace("_", " ").title(), options, index=index, key=f"map_{canonical}")
        if selected != "—":
            mapping[canonical] = selected

    normalized = normalize_finance_data(raw, mapping)
    result = validate_finance_data(normalized, profile.dataset_type)

    st.subheader("4. Finance data quality")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{result.rows:,}")
    c2.metric("Duplicate rows", f"{result.duplicate_rows:,}")
    c3.metric("Missing dates", f"{result.missing_dates:,}")
    c4.metric("Numeric issues", f"{result.numeric_issues:,}")

    if result.errors:
        for error in result.errors:
            st.error(error)
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)
    if result.valid:
        st.success(f"Dataset passed structural validation and is ready for: {profile.route}.")

    st.subheader("5. Canonical dataset")
    st.dataframe(normalized.head(100), use_container_width=True)

    csv = normalized.to_csv(index=False).encode("utf-8")
    st.download_button("Download normalized CSV", csv, file_name="ng_finance_normalized.csv", mime="text/csv")
