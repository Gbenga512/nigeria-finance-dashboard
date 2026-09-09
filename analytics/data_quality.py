"""Advanced financial-data quality and control analytics.

The functions are deterministic and operate only on supplied data. They are
intended to sit between ingestion/normalisation and downstream accounting,
reconciliation, treasury and risk workflows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def quality_score(frame: pd.DataFrame) -> dict:
    """Return an auditable 0-100 data-quality score and control statistics."""
    if frame is None or frame.empty:
        return {"score": 0.0, "rows": 0, "duplicate_rows": 0, "missing_dates": 0, "numeric_nulls": 0, "completeness": 0.0}
    work = frame.copy()
    rows = len(work)
    duplicate_rows = int(work.duplicated().sum())
    date_col = next((c for c in ["date", "Date", "transaction_date"] if c in work.columns), None)
    missing_dates = int(pd.to_datetime(work[date_col], errors="coerce").isna().sum()) if date_col else rows
    numeric_cols = [c for c in ["debit", "credit", "amount"] if c in work.columns]
    numeric_nulls = int(sum(pd.to_numeric(work[c], errors="coerce").isna().sum() for c in numeric_cols))
    completeness = float(1.0 - missing_dates / rows)
    duplicate_rate = duplicate_rows / rows
    penalty = min(1.0, duplicate_rate + min(1.0, numeric_nulls / max(rows * max(len(numeric_cols), 1), 1)))
    score = max(0.0, min(100.0, 100.0 * (0.65 * completeness + 0.35 * (1.0 - penalty))))
    return {"score": round(score, 2), "rows": rows, "duplicate_rows": duplicate_rows, "missing_dates": missing_dates, "numeric_nulls": numeric_nulls, "completeness": round(completeness, 4)}


def duplicate_records(frame: pd.DataFrame) -> pd.DataFrame:
    """Return all duplicate records, preserving their original rows."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    return frame[frame.duplicated(keep=False)].copy()


def amount_anomalies(frame: pd.DataFrame, z_threshold: float = 3.0) -> pd.DataFrame:
    """Flag unusually large absolute transaction amounts using robust MAD."""
    if frame is None or frame.empty or "amount" not in frame.columns:
        return pd.DataFrame()
    work = frame.copy()
    amount = pd.to_numeric(work["amount"], errors="coerce")
    median = float(amount.median()) if amount.notna().any() else 0.0
    mad = float(np.median(np.abs(amount.dropna().to_numpy() - median))) if amount.notna().any() else 0.0
    scale = 1.4826 * mad
    if scale <= 1e-12:
        std = float(amount.std(ddof=1)) if amount.notna().sum() > 1 else 0.0
        scale = std
    if scale <= 1e-12:
        return pd.DataFrame()
    score = (amount - median).abs() / scale
    flagged = work.loc[score >= z_threshold].copy()
    if flagged.empty:
        return flagged
    flagged["Anomaly Score"] = score.loc[flagged.index].round(2)
    return flagged.sort_values("Anomaly Score", ascending=False)


def daily_control_totals(frame: pd.DataFrame) -> pd.DataFrame:
    """Produce daily transaction counts and debit/credit/amount control totals."""
    if frame is None or frame.empty or "date" not in frame.columns:
        return pd.DataFrame()
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    for col in ["debit", "credit", "amount"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    aggregations = {"Transaction Count": ("date", "size")}
    if "debit" in work.columns: aggregations["Debit Total"] = ("debit", "sum")
    if "credit" in work.columns: aggregations["Credit Total"] = ("credit", "sum")
    if "amount" in work.columns: aggregations["Net Amount"] = ("amount", "sum")
    return work.dropna(subset=["date"]).groupby("date").agg(**aggregations).reset_index()


def control_summary(frame: pd.DataFrame) -> dict:
    """Generate management-ready control observations from normalized finance data."""
    quality = quality_score(frame)
    anomalies = amount_anomalies(frame)
    duplicates = duplicate_records(frame)
    observations = []
    if quality["missing_dates"]: observations.append(f"{quality['missing_dates']:,} rows have missing or invalid dates.")
    if quality["duplicate_rows"]: observations.append(f"{quality['duplicate_rows']:,} duplicate rows require review.")
    if not anomalies.empty: observations.append(f"{len(anomalies):,} unusually large transactions were flagged for review.")
    if not observations: observations.append("No material structural control exception was detected by the configured checks.")
    return {"quality": quality, "anomalies": anomalies, "duplicates": duplicates, "observations": observations}
