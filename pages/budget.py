import pandas as pd
import streamlit as st


def render():
    st.title("📊 Budget vs Actual Analysis")
    st.caption("Upload a budget file or enter departmental figures for variance analysis.")
    upload = st.file_uploader("Budget/Actual CSV or XLSX", type=["csv", "xlsx"])

    if upload:
        df = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
        df.columns = [str(c).strip() for c in df.columns]
        required = {"Department", "Budget", "Actual"}
        if not required.issubset(df.columns):
            st.error("File must contain Department, Budget and Actual columns.")
            return
    else:
        df = pd.DataFrame({"Department": ["Finance", "HR", "Operations"], "Budget": [5_000_000, 3_000_000, 8_000_000], "Actual": [4_500_000, 3_500_000, 7_600_000]})

    df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce")
    df["Actual"] = pd.to_numeric(df["Actual"], errors="coerce")
    df = df.dropna(subset=["Budget", "Actual"])
    df["Variance"] = df["Actual"] - df["Budget"]
    df["Variance %"] = df["Variance"].div(df["Budget"].replace(0, pd.NA)) * 100

    overspend = float(df.loc[df["Variance"] > 0, "Variance"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Budget", f"₦{df['Budget'].sum():,.0f}")
    c2.metric("Total Actual", f"₦{df['Actual'].sum():,.0f}")
    c3.metric("Gross Overspend", f"₦{overspend:,.0f}")

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("Department")[["Budget", "Actual"]])
