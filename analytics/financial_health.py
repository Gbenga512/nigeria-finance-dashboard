import pandas as pd


def _score(value, bands):
    if value is None or pd.isna(value):
        return None
    for threshold, score in bands:
        if value >= threshold:
            return score
    return 20


def financial_health_score(ratios: pd.DataFrame) -> tuple[float | None, pd.DataFrame]:
    if ratios.empty:
        return None, pd.DataFrame()

    values = dict(zip(ratios["Ratio"], ratios["Value"]))
    components = {
        "Liquidity": _score(values.get("Current Ratio"), [(2.0, 100), (1.5, 80), (1.0, 60), (0.75, 40)]),
        "Profitability": _score(values.get("Net Margin"), [(0.15, 100), (0.10, 80), (0.05, 60), (0.0, 40)]),
        "Solvency": None if values.get("Debt-to-Equity") is None else max(20, min(100, 100 - values["Debt-to-Equity"] * 30)),
        "Efficiency": _score(values.get("ROA"), [(0.10, 100), (0.05, 80), (0.02, 60), (0.0, 40)]),
        "Cash Flow": None if values.get("Operating Cash Flow") is None else (100 if values["Operating Cash Flow"] > 0 else 30),
    }

    valid = [v for v in components.values() if v is not None]
    overall = round(sum(valid) / len(valid), 1) if valid else None
    detail = pd.DataFrame({"Dimension": list(components), "Score": list(components.values())})
    return overall, detail
