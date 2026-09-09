"""Out-of-sample volatility forecasting and model comparison.

Compares a historical rolling-variance benchmark, EWMA and GARCH(1,1) using
strictly chronological one-step-ahead forecasts. GARCH is refit periodically
using only observations available before each forecast date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.garch import clean_returns, fit_garch11


def _daily_variance_forecast_from_ewma(history: pd.Series, lam: float = 0.94) -> float | None:
    x = clean_returns(history)
    if len(x) < 2 or not 0 < lam < 1:
        return None
    variance = max(float(x.iloc[0] ** 2), 1e-12)
    for value in x.iloc[1:]:
        variance = lam * variance + (1.0 - lam) * float(value) ** 2
    return max(variance, 1e-12)


def _daily_variance_forecast_historical(history: pd.Series, window: int = 21) -> float | None:
    x = clean_returns(history)
    if len(x) < window or window < 2:
        return None
    return max(float(x.iloc[-window:].var(ddof=1)), 1e-12)


def _garch_daily_forecast(history: pd.Series) -> float | None:
    result = fit_garch11(history)
    if not result.get("success"):
        return None
    return max(float(result["forecast_volatility"]) ** 2, 1e-12)


def _qlike(realized_variance: float, forecast_variance: float) -> float:
    r = max(float(realized_variance), 1e-12)
    f = max(float(forecast_variance), 1e-12)
    return r / f - np.log(r / f) - 1.0


def benchmark_volatility_models(
    returns: pd.Series,
    train_window: int = 252,
    test_window: int | None = 126,
    historical_window: int = 21,
    ewma_lambda: float = 0.94,
    garch_refit: int = 21,
) -> dict:
    """Run a chronological OOS benchmark for historical, EWMA and GARCH models.

    Forecasts at date t use observations strictly before t. GARCH is refit only
    every ``garch_refit`` forecast dates to control computation while retaining
    a genuine sequential evaluation design.
    """
    x = clean_returns(returns).reset_index(drop=True)
    if train_window < 80 or len(x) <= train_window:
        return {"available": False, "reason": "Insufficient observations for the requested training window."}

    end = len(x) if test_window is None else min(len(x), train_window + max(int(test_window), 1))
    rows: list[dict] = []
    garch_forecast = None

    for i in range(train_window, end):
        history = x.iloc[:i]
        if i == train_window or (i - train_window) % max(garch_refit, 1) == 0:
            garch_forecast = _garch_daily_forecast(history)

        forecasts = {
            "Historical": _daily_variance_forecast_historical(history, historical_window),
            "EWMA": _daily_variance_forecast_from_ewma(history, ewma_lambda),
            "GARCH(1,1)": garch_forecast,
        }
        realized = float(x.iloc[i] ** 2)
        for model, forecast in forecasts.items():
            if forecast is None:
                continue
            rows.append({
                "Observation": i,
                "Model": model,
                "Forecast Variance": forecast,
                "Realized Variance Proxy": realized,
                "QLIKE": _qlike(realized, forecast),
                "Squared Error": (realized - forecast) ** 2,
                "Absolute Error": abs(realized - forecast),
            })

    detail = pd.DataFrame(rows)
    if detail.empty:
        return {"available": False, "reason": "No valid out-of-sample forecasts could be generated."}

    summary = (
        detail.groupby("Model", as_index=False)
        .agg(
            Observations=("QLIKE", "size"),
            Mean_QLIKE=("QLIKE", "mean"),
            RMSE=("Squared Error", lambda s: float(np.sqrt(np.mean(s)))),
            MAE=("Absolute Error", "mean"),
        )
        .sort_values("Mean_QLIKE")
        .reset_index(drop=True)
    )
    summary["Rank"] = np.arange(1, len(summary) + 1)
    return {
        "available": True,
        "detail": detail,
        "summary": summary,
        "winner": str(summary.iloc[0]["Model"]),
        "train_window": train_window,
        "test_observations": int(detail["Observation"].nunique()),
        "garch_refit": garch_refit,
    }
