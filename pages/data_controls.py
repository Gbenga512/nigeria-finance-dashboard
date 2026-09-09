"""Executive data-control dashboard built on the finance ingestion layer."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from analytics.data_quality import control_summary, daily_control_totals
from analytics.finance_data import normalize_finance_data, read_uploaded_file
from ng_ui import hero


def render() -> None:
    hero("Financial Data Controls", "A control layer for data quality, transaction anomalies and daily finance totals.", "Data governance")
    uploaded = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"], key="data_controls_upload")
    if uploaded is None:
        st.info("Upload a normalized or export-format finance dataset to run control tests.")
        return
    try:
        raw = read_uploaded_file(uploaded, uploaded.name)
        data = normalize_finance_data(raw)
    except Exception as exc:
        st.error(f"Unable to process the file: {exc}")
        return
    controls = control_summary(data)
    q = controls["quality"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality score", f"{q['score']:.1f}/100")
    c2.metric("Rows", f"{q['rows']:,}")
    c3.metric("Duplicates", f"{q['duplicate_rows']:,}")
    c4.metric("Amount anomalies", f"{len(controls['anomalies']):,}")
    for observation in controls["observations"]:
        st.write("• " + observation)
    if not controls["anomalies"].empty:
        st.markdown("### Transaction anomaly queue")
        st.dataframe(controls["anomalies"].head(200), use_container_width=True, hide_index=True)
    totals = daily_control_totals(data)
    if not totals.empty:
        st.markdown("### Daily control totals")
        st.dataframe(totals, use_container_width=True, hide_index=True)
    st.download_button("Download control totals", totals.to_csv(index=False), "daily_control_totals.csv", "text/csv")
    with st.expander("Control methodology"):
        st.markdown("""
The quality score combines date completeness and duplicate/numeric-control penalties.
Amount anomalies use a robust median/MAD approach rather than a normality assumption.
Daily totals provide an audit-friendly control trail. These checks identify items for
review; they do not establish fraud or accounting error on their own.
""")
