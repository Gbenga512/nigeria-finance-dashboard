import pandas as pd

from analytics.integrated_risk import integrated_risk_score, risk_driver_table


def test_integrated_risk_escalates_for_tight_liquidity():
    snapshot = pd.DataFrame({"Asset": ["USD/NGN", "Gold"], "Change %": [0.5, 3.5]})
    result = integrated_risk_score(snapshot, runway_days=10, fx_exposure=2_000_000)
    assert result["score"] >= 50
    assert result["level"] in {"High", "Critical"}
    assert result["drivers"]


def test_integrated_risk_normal_case():
    snapshot = pd.DataFrame({"Asset": ["USD/NGN"], "Change %": [0.2]})
    result = integrated_risk_score(snapshot, runway_days=90, fx_exposure=0)
    assert result["level"] == "Normal"
    assert result["score"] == 0


def test_risk_driver_table_is_auditable():
    snapshot = pd.DataFrame({"Asset": ["Gold"], "Change %": [1.2]})
    table = risk_driver_table(snapshot, 25, 500_000)
    assert "Integrated score" in set(table["Driver"])
