import streamlit as st

from analytics.management_report import build_market_report
from ng_ui import hero


def render(snapshot, insight):
    hero(
        "Executive Reports",
        "Generate a management-ready market intelligence brief from the current data snapshot.",
        "Report workspace",
    )

    report = build_market_report(snapshot, insight)

    c1, c2, c3 = st.columns(3)
    valid = int(snapshot["Price"].notna().sum()) if not snapshot.empty else 0
    c1.metric("Tracked instruments", valid)
    c2.metric("Report type", "Executive brief")
    c3.metric("Generation", "On demand")

    st.markdown("### Management brief")
    st.code(report, language="text")

    st.download_button(
        "Download executive report",
        data=report,
        file_name="ng_finance_pro_executive_report.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("### Reporting roadmap")
    st.info("Next reporting layers: PDF board packs, Excel management packs, treasury reports, budget variance reports and scheduled management alerts.")
