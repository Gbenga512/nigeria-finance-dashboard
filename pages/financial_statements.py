import pandas as pd
import streamlit as st

from analytics.financial_health import financial_health_score
from analytics.ratios import calculate_ratios

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
    st.title("📑 Financial Statement Analyzer")
    st.caption("Upload standardized statement extracts to calculate core ratios and a financial health score.")
    files = {}
    cols = st.columns(3)
    for col, name in zip(cols, STATEMENT_ITEMS):
        with col:
            files[name] = st.file_uploader(f"{name} (CSV/XLSX)", type=["csv", "xlsx"], key=name)

    if not any(files.values()):
        st.info("Expected format: two columns such as 'Account' and 'Amount'.")
        with st.expander("Required line items"):
            for statement, items in STATEMENT_ITEMS.items():
                st.write(f"**{statement}:** {', '.join(items)}")
        return

    try:
        mappings = {name: _to_mapping(_read(upload)) for name, upload in files.items() if upload}
        bs = mappings.get("Balance Sheet", {})
        pnl = mappings.get("Income Statement", {})
        cf = mappings.get("Cash Flow", {})
        ratios = calculate_ratios(bs, pnl, cf)
        score, detail = financial_health_score(ratios)
    except Exception as exc:
        st.error(str(exc))
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Financial Health Score", "N/A" if score is None else f"{score}/100")
    with c2:
        st.metric("Ratios Calculated", int(ratios["Value"].notna().sum()))

    st.subheader("Core Ratios")
    st.dataframe(ratios[["Ratio", "Display"]], use_container_width=True, hide_index=True)
    if not detail.empty:
        st.subheader("Health Score Components")
        st.bar_chart(detail.set_index("Dimension")["Score"])
