from config.settings import get_secret


def rule_based_market_insight(snapshot) -> str:
    if snapshot is None or snapshot.empty:
        return "Market data is currently unavailable. Check the market feed and try again."

    lines = []
    for _, row in snapshot.iterrows():
        price = row.get("Price")
        change = row.get("Change %")
        if price is None:
            continue
        direction = "up" if (change or 0) > 0 else "down" if (change or 0) < 0 else "flat"
        lines.append(f"{row['Asset']} is {direction} at {price:,.2f} ({change:+.2f}% today)." if change is not None else f"{row['Asset']} is at {price:,.2f}.")

    return "\n\n".join(lines) + "\n\nUse this as market context, not as investment advice."


def generate_ai_insight(snapshot) -> tuple[str, bool]:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        return rule_based_market_insight(snapshot), False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        market_text = snapshot.to_json(orient="records")
        response = client.responses.create(
            model="gpt-5-mini",
            input=(
                "Act as a conservative Nigerian financial analyst. Analyze the following market snapshot. "
                "Highlight material movements, possible macroeconomic implications for Nigeria, and key risks. "
                "Do not provide personalized investment advice. Keep it concise.\n\n" + market_text
            ),
        )
        return response.output_text, True
    except Exception:
        return rule_based_market_insight(snapshot), False
