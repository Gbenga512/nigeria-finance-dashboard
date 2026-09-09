"""Integrated risk decision engine for NG Finance Pro.

Combines observable market movements with treasury liquidity and FX exposure
inputs into a transparent management risk score. Thresholds are heuristics and
must be calibrated before production risk governance use.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def integrated_risk_score(snapshot: pd.DataFrame, runway_days: float | None = None, fx_exposure: float = 0.0) -> dict:
    """Return an explainable 0-100 risk score and management actions."""
    score = 0.0
    drivers: list[str] = []
    if snapshot is not None and not snapshot.empty and "Change %" in snapshot.columns:
        changes = pd.to_numeric(snapshot["Change %"], errors="coerce").dropna()
        high = int((changes.abs() >= 3).sum())
        moderate = int(((changes.abs() >= 1) & (changes.abs() < 3)).sum())
        score += min(35.0, high * 10.0 + moderate * 4.0)
        if high:
            drivers.append(f"{high} material market movement(s)")
        elif moderate:
            drivers.append(f"{moderate} moderate market movement(s)")
    if runway_days is not None and np.isfinite(runway_days):
        if runway_days < 15:
            score += 40.0; drivers.append("critical liquidity runway")
        elif runway_days < 30:
            score += 25.0; drivers.append("tight liquidity runway")
        elif runway_days < 60:
            score += 10.0; drivers.append("moderate liquidity runway")
    if abs(float(fx_exposure)) > 0:
        fx_score = min(25.0, abs(float(fx_exposure)) / 1_000_000 * 5.0)
        score += fx_score
        if fx_score >= 15: drivers.append("material FX exposure")
        elif fx_score > 0: drivers.append("FX exposure present")
    score = min(100.0, round(score, 1))
    level = "Critical" if score >= 75 else "High" if score >= 50 else "Elevated" if score >= 25 else "Normal"
    actions = {
        "Critical": "Escalate to management; review liquidity, FX hedging and market-sensitive exposures immediately.",
        "High": "Increase monitoring frequency and review material liquidity and market exposures.",
        "Elevated": "Maintain heightened monitoring and investigate the principal risk drivers.",
        "Normal": "Continue routine monitoring and control procedures.",
    }
    return {"score": score, "level": level, "drivers": drivers, "action": actions[level]}


def risk_driver_table(snapshot: pd.DataFrame, runway_days: float | None, fx_exposure: float) -> pd.DataFrame:
    """Return a compact, auditable risk-driver table."""
    result = integrated_risk_score(snapshot, runway_days, fx_exposure)
    rows = [{"Driver": "Market movement", "Status": "Reviewed", "Contribution": None}]
    if runway_days is not None:
        rows.append({"Driver": "Liquidity runway", "Status": f"{runway_days:.1f} days", "Contribution": None})
    rows.append({"Driver": "FX exposure", "Status": f"{fx_exposure:,.2f}", "Contribution": None})
    rows.append({"Driver": "Integrated score", "Status": result["level"], "Contribution": result["score"]})
    return pd.DataFrame(rows)
