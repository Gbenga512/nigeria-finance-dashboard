from datetime import datetime

import pandas as pd


def build_market_report(snapshot: pd.DataFrame, insight: str) -> str:
    now = datetime.now().strftime("%d %B %Y, %H:%M")
    lines = [
        "NG FINANCE PRO — EXECUTIVE MARKET REPORT",
        "=" * 48,
        f"Generated: {now}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 20,
    ]

    if snapshot is None or snapshot.empty:
        lines.append("Market data was unavailable at the time of generation.")
        return "\n".join(lines)

    valid = snapshot.dropna(subset=["Price", "Change %"]).copy()
    if not valid.empty:
        gainers = valid.sort_values("Change %", ascending=False).head(3)
        decliners = valid.sort_values("Change %", ascending=True).head(3)
        lines.append(f"Tracked instruments with valid observations: {len(valid)}.")
        lines.append("")
        lines.append("TOP MOVERS")
        for _, row in gainers.iterrows():
            lines.append(f"+ {row['Asset']}: {row['Change %']:+.2f}% at {row['Price']:,.2f}")
        lines.append("")
        lines.append("DECLINERS")
        for _, row in decliners.iterrows():
            lines.append(f"- {row['Asset']}: {row['Change %']:+.2f}% at {row['Price']:,.2f}")

    lines.extend([
        "",
        "ANALYST CONTEXT",
        "-" * 20,
        insight.strip(),
        "",
        "DISCLAIMER",
        "This report is for financial analysis and decision support only. It is not personalized investment advice.",
    ])
    return "\n".join(lines)
