import pandas as pd


def build_market_intelligence(snapshot: pd.DataFrame) -> dict:
    """Create deterministic, explainable alerts from the current market snapshot."""
    if snapshot is None or snapshot.empty:
        return {
            "overall": "Data unavailable",
            "score": None,
            "alerts": [],
            "movers": pd.DataFrame(),
            "breadth": {"gainers": 0, "decliners": 0, "flat": 0},
        }

    work = snapshot.copy()
    work["Change %"] = pd.to_numeric(work["Change %"], errors="coerce")
    valid = work.dropna(subset=["Change %"]).copy()
    alerts = []

    for _, row in valid.iterrows():
        change = float(row["Change %"])
        asset = str(row["Asset"])
        if abs(change) >= 3:
            severity = "High"
            message = f"{asset} moved {change:+.2f}% today — review exposure and liquidity sensitivity."
        elif abs(change) >= 1:
            severity = "Moderate"
            message = f"{asset} moved {change:+.2f}% today — monitor for further deterioration or reversal."
        else:
            continue
        alerts.append({"Severity": severity, "Area": "Market", "Signal": message, "Change %": change})

    gainers = int((valid["Change %"] > 0).sum())
    decliners = int((valid["Change %"] < 0).sum())
    flat = int((valid["Change %"] == 0).sum())
    avg_abs = float(valid["Change %"].abs().mean()) if not valid.empty else 0.0
    high_count = sum(a["Severity"] == "High" for a in alerts)
    moderate_count = sum(a["Severity"] == "Moderate" for a in alerts)
    score = min(100, round(high_count * 25 + moderate_count * 12 + avg_abs * 5))
    overall = "High attention" if score >= 60 else "Elevated" if score >= 30 else "Normal"

    movers = valid[["Asset", "Change %"]].copy().sort_values("Change %", ascending=False)
    movers["Direction"] = movers["Change %"].map(lambda x: "Gainer" if x > 0 else "Decliner" if x < 0 else "Flat")

    return {
        "overall": overall,
        "score": score,
        "alerts": sorted(alerts, key=lambda x: (x["Severity"] != "High", -abs(x["Change %"]))),
        "movers": movers,
        "breadth": {"gainers": gainers, "decliners": decliners, "flat": flat},
    }


def management_summary(intelligence: dict) -> str:
    if intelligence.get("score") is None:
        return "No management signal can be generated until market data is available."
    breadth = intelligence["breadth"]
    if intelligence["overall"] == "High attention":
        tone = "Several material market movements warrant management review."
    elif intelligence["overall"] == "Elevated":
        tone = "Market conditions show elevated movement and should remain under observation."
    else:
        tone = "Current tracked market movements are within the platform's normal monitoring thresholds."
    return f"{tone} Breadth: {breadth['gainers']} gainers, {breadth['decliners']} decliners and {breadth['flat']} flat."
