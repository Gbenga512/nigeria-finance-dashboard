"""Personal finance scenario planning engine."""
from __future__ import annotations
from dataclasses import dataclass
from analytics import personal_cashflow_forecast

@dataclass(frozen=True)
class Scenario:
    name: str
    income_change_pct: float = 0.0
    expense_change_pct: float = 0.0
    savings_change_pct: float = 0.0
    debt_change_pct: float = 0.0

SCENARIOS = (
    Scenario("Base Case"),
    Scenario("Conservative", income_change_pct=-10.0, expense_change_pct=10.0, savings_change_pct=-10.0),
    Scenario("Custom"),
)

def project(start: str, months: int, scenario: Scenario):
    df=personal_cashflow_forecast.forecast(start,months).copy()
    if df.empty: return df
    df["Scenario"]=scenario.name
    df["Adjusted Income"]=df["Forecast Income"]*(1+scenario.income_change_pct/100)
    df["Adjusted Outflows"]=df["Forecast Outflows"]*(1+scenario.expense_change_pct/100)
    df["Adjusted Net Cash Flow"]=df["Adjusted Income"]-df["Adjusted Outflows"]
    opening=float(df.iloc[0]["Opening Cash"])
    closes=[]
    for net in df["Adjusted Net Cash Flow"]:
        opening += float(net); closes.append(opening)
    df["Projected Closing Cash"]=closes
    df["Status"]="ESTIMATE / SCENARIO"
    return df

def compare(start: str, months: int, scenarios=None):
    scenarios=scenarios or SCENARIOS[:2]
    frames=[project(start,months,s) for s in scenarios]
    return __import__("pandas").concat(frames,ignore_index=True) if frames else __import__("pandas").DataFrame()
