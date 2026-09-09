import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from analytics.financial_health import financial_health_score
from analytics.ratios import calculate_ratios
from ng_ui import hero

STATEMENT_ITEMS = {
    "Balance Sheet": ["Cash & Cash Equivalents", "Inventory", "Current Assets", "Current Liabilities", "Total Assets", "Total Liabilities", "Total Equity", "Total Debt"],
    "Income Statement": ["Revenue", "Gross Profit", "Operating Profit", "Net Income", "Interest Expense"],
    "Cash Flow": ["Operating Cash Flow"],
}


def _read(upload):
    return pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)


def _to_mapping(df):
    cols = {str(c).strip().lower(): c for c in df.columns}
    item_col = next((cols[k] for k in cols if k in {"account", "line item", "item", "description", "account name"}), None)
    value_col = next((cols[k] for k in cols if k in {"amount", "value", "balance"}), None)
    if not item_col or not value_col:
        raise ValueError("Each statement needs an Account/Line Item column and an Amount/Value column.")
    out = {}
    for _, row in df.iterrows():
        key = str(row[item_col]).strip()
        value = pd.to_numeric(row[value_col], errors="coerce")
        if key and pd.notna(value):
            out[key] = float(value)
    return out


def render():
    hero("Financial Statement Intelligence", "Convert statement extracts into ratios, financial health signals and management-ready diagnostics.", "Analytics workspace")
    files = {}
    cols = st.columns(3)
    for col, name in zip(cols, STATEMENT_ITEMS):
        with col:
            files[name] = st.file_uploader(f"{name}", type=["csv", "xlsx"], key=name)
    if not any(files.values()):
        st.info("Upload one or more statement extracts. Expected columns include Account/Line Item and Amount/Value.")
        with st.expander("Supported line items"):
            for statement, items in STATEMENT_ITEMS.items():
                st.write(f"**{statement}:** {', '.join(items)}")
        return
    try:
        mappings = {name: _to_mapping(_read(upload)) for name, upload in files.items() if upload}
        ratios = calculate_ratios(mappings.get("Balance Sheet", {}), mappings.get("Income Statement", {}), mappings.get("Cash Flow", {}))
        score, detail = financial_health_score(ratios)
    except Exception as exc:
        st.error(str(exc))
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Financial health", "N/A" if score is None else f"{score}/100")
    c2.metric("Ratios calculated", int(ratios["Value"].notna().sum()))
    c3.metric("Statements supplied", sum(bool(v) for v in files.values()))
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown("### Core financial ratios")
        st.dataframe(ratios[["Ratio", "Display"]], use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Health score")
        if score is None:
            st.info("Provide enough statement data to calculate the health score.")
        else:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={"axis": {"range": [0, 100]}}))
            fig.update_layout(height=270, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    if not detail.empty:
        st.markdown("### Health score components")
        st.bar_chart(detail.set_index("Dimension")["Score"])
    st.caption("Analytical outputs are decision-support indicators and should be reviewed alongside accounting policies and source records.")
