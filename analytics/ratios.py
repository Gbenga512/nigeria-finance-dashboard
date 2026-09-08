import pandas as pd


def safe_div(numerator, denominator):
    try:
        if denominator in (0, None) or pd.isna(denominator):
            return None
        return float(numerator) / float(denominator)
    except (TypeError, ValueError):
        return None


def calculate_ratios(bs: dict, pnl: dict, cashflow: dict | None = None) -> pd.DataFrame:
    revenue = pnl.get("Revenue")
    gross_profit = pnl.get("Gross Profit")
    operating_profit = pnl.get("Operating Profit")
    net_income = pnl.get("Net Income")
    current_assets = bs.get("Current Assets")
    current_liabilities = bs.get("Current Liabilities")
    cash = bs.get("Cash & Cash Equivalents")
    inventory = bs.get("Inventory")
    total_assets = bs.get("Total Assets")
    total_liabilities = bs.get("Total Liabilities")
    equity = bs.get("Total Equity")
    debt = bs.get("Total Debt")
    interest = pnl.get("Interest Expense")
    cfo = (cashflow or {}).get("Operating Cash Flow")

    rows = [
        ("Current Ratio", safe_div(current_assets, current_liabilities), "x"),
        ("Quick Ratio", safe_div((current_assets or 0) - (inventory or 0), current_liabilities), "x"),
        ("Cash Ratio", safe_div(cash, current_liabilities), "x"),
        ("Gross Margin", safe_div(gross_profit, revenue), "%"),
        ("Operating Margin", safe_div(operating_profit, revenue), "%"),
        ("Net Margin", safe_div(net_income, revenue), "%"),
        ("ROA", safe_div(net_income, total_assets), "%"),
        ("ROE", safe_div(net_income, equity), "%"),
        ("Debt-to-Equity", safe_div(debt, equity), "x"),
        ("Interest Coverage", safe_div(operating_profit, interest), "x"),
        ("Liabilities-to-Assets", safe_div(total_liabilities, total_assets), "%"),
        ("Operating Cash Flow", cfo, "₦"),
    ]

    result = pd.DataFrame(rows, columns=["Ratio", "Value", "Unit"])
    result["Display"] = result.apply(
        lambda r: "N/A" if pd.isna(r["Value"]) else (
            f"{r['Value'] * 100:.1f}%" if r["Unit"] == "%" and r["Ratio"] != "Operating Cash Flow" else
            f"₦{r['Value']:,.0f}" if r["Unit"] == "₦" else f"{r['Value']:.2f}x"
        ), axis=1
    )
    return result
