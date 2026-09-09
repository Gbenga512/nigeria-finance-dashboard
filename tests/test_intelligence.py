import pandas as pd

from analytics.intelligence import build_market_intelligence, management_summary


def test_market_intelligence_prioritizes_large_moves():
    snapshot = pd.DataFrame({
        "Asset": ["USD/NGN", "Gold", "BTC/USD"],
        "Price": [1300.0, 4400.0, 78000.0],
        "Change %": [3.5, -1.2, 0.2],
        "Data": ["Live", "Live", "Live"],
    })
    result = build_market_intelligence(snapshot)
    assert result["overall"] == "Elevated"
    assert result["breadth"] == {"gainers": 2, "decliners": 1, "flat": 0}
    assert result["alerts"][0]["Severity"] == "High"
    assert result["alerts"][0]["Area"] == "Market"


def test_empty_snapshot_is_safe():
    result = build_market_intelligence(pd.DataFrame())
    assert result["score"] is None
    assert result["alerts"] == []
    assert "unavailable" in management_summary(result).lower()
