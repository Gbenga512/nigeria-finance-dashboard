import numpy as np
import pandas as pd

from analytics.ml_regime import build_regime_dataset, label_regimes, regime_ml_experiment


def synthetic_prices(n=420, seed=42):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0003, 0.012, n)
    returns[180:240] += rng.normal(0, 0.035, 60)
    returns[300:350] += rng.normal(0, 0.025, 50)
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=pd.date_range("2024-01-01", periods=n, freq="B"))


def test_regime_dataset_uses_forward_target():
    prices = synthetic_prices()
    dataset = build_regime_dataset(prices, feature_window=21, horizon=21)
    assert not dataset.empty
    assert set([
        "return_1d", "momentum_5d", "momentum_21d",
        "volatility_21d", "trend_21d", "future_volatility"
    ]).issubset(dataset.columns)
    assert dataset.index.max() < prices.index.max()


def test_label_regimes_has_three_categories():
    values = pd.Series([0.10, 0.20, 0.30])
    labels = label_regimes(values, (0.15, 0.25))
    assert list(labels) == ["Low volatility", "Normal volatility", "High volatility"]


def test_regime_ml_experiment_locks_test_set_and_is_reproducible():
    prices = synthetic_prices()
    result = regime_ml_experiment(prices, test_fraction=0.30, random_state=42)
    assert result["available"] is True
    assert result["train_end"] < result["validation_end"] < result["test_start"]
    assert result["validation_observations"] >= 30
    assert result["test_observations"] >= 30
    assert result["selected_model"] in {"Logistic regression", "Random forest"}
    assert result["evaluations"]["Model"].tolist() == [result["selected_model"], "Persistence baseline"]
    assert set(result["predictions"].columns) == {
        "Actual Regime",
        "Selected Model Prediction",
        "Persistence Baseline",
    }

    repeat = regime_ml_experiment(prices, test_fraction=0.30, random_state=42)
    assert repeat["selected_model"] == result["selected_model"]
    np.testing.assert_allclose(
        result["evaluations"].iloc[:, 1:].to_numpy(dtype=float),
        repeat["evaluations"].iloc[:, 1:].to_numpy(dtype=float),
        rtol=1e-12,
        atol=1e-12,
    )

    if result["selected_model"] == "Random forest":
        np.testing.assert_allclose(
            result["feature_importance"]["Importance"].sum(), 1.0, rtol=1e-6
        )
