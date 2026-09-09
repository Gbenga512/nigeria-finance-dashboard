"""Machine-learning regime prediction utilities for NG Finance Pro.

The pipeline is deliberately chronological. Features at time t use only
information available by t, while labels describe realized volatility over the
following horizon. Model selection uses a chronological validation sample and
an untouched final test sample.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REGIMES = ["Low volatility", "Normal volatility", "High volatility"]
FEATURE_COLUMNS = ["return_1d", "momentum_5d", "momentum_21d", "volatility_21d", "trend_21d"]

def _clean_prices(prices: pd.Series) -> pd.Series:
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    return clean[clean > 0]

def build_regime_dataset(prices: pd.Series, feature_window: int = 21, horizon: int = 21) -> pd.DataFrame:
    clean = _clean_prices(prices)
    if len(clean) < max(feature_window, horizon) + 20 or feature_window < 2 or horizon < 2:
        return pd.DataFrame()
    returns = clean.pct_change()
    features = pd.DataFrame(index=clean.index)
    features["return_1d"] = returns
    features["momentum_5d"] = clean.pct_change(5)
    features["momentum_21d"] = clean.pct_change(21)
    features["volatility_21d"] = returns.rolling(feature_window).std(ddof=1) * np.sqrt(252)
    features["trend_21d"] = clean / clean.rolling(21).mean() - 1.0
    future_vol = returns.rolling(horizon).std(ddof=1) * np.sqrt(252)
    features["future_volatility"] = future_vol.shift(-horizon)
    return features.dropna()

def _thresholds(train_future_vol: pd.Series) -> tuple[float, float] | None:
    clean = pd.to_numeric(train_future_vol, errors="coerce").dropna()
    if clean.empty:
        return None
    low, high = float(clean.quantile(0.33)), float(clean.quantile(0.67))
    return (low, high) if low < high else None

def label_regimes(volatility: pd.Series, thresholds: tuple[float, float]) -> pd.Series:
    low, high = thresholds
    clean = pd.to_numeric(volatility, errors="coerce")
    return pd.Series(np.select([clean <= low, clean >= high], [REGIMES[0], REGIMES[2]], default=REGIMES[1]), index=volatility.index, dtype="object")

def _metrics(y_true: pd.Series, y_pred: np.ndarray, labels: list[str]) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
    }

def _bootstrap_metric_ci(y_true: pd.Series, y_pred: np.ndarray, metric: str, labels: list[str], random_state: int = 42, n_bootstrap: int = 1000) -> tuple[float, float] | None:
    """Percentile bootstrap 95% CI using only held-out test predictions."""
    y_true_arr, y_pred_arr = np.asarray(y_true), np.asarray(y_pred)
    n = len(y_true_arr)
    if n < 30:
        return None
    rng = np.random.default_rng(random_state)
    values = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        yt, yp = y_true_arr[idx], y_pred_arr[idx]
        if metric == "accuracy":
            values[i] = accuracy_score(yt, yp)
        elif metric == "balanced_accuracy":
            values[i] = balanced_accuracy_score(yt, yp)
        elif metric == "macro_f1":
            values[i] = f1_score(yt, yp, labels=labels, average="macro", zero_division=0)
        else:
            raise ValueError(f"Unsupported bootstrap metric: {metric}")
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))

def _add_test_uncertainty(row: dict, y_true: pd.Series, y_pred: np.ndarray, random_state: int) -> dict:
    for metric in ["accuracy", "balanced_accuracy", "macro_f1"]:
        ci = _bootstrap_metric_ci(y_true, y_pred, metric, REGIMES, random_state)
        row[f"{metric}_ci_low"] = np.nan if ci is None else ci[0]
        row[f"{metric}_ci_high"] = np.nan if ci is None else ci[1]
    return row

def _persistence_predictions(current_vol: pd.Series, thresholds: tuple[float, float]) -> pd.Series:
    return label_regimes(current_vol, thresholds)

def _build_models(random_state: int) -> dict:
    logistic = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=1000, random_state=random_state))])
    forest = RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=5, class_weight="balanced", random_state=random_state, n_jobs=-1)
    return {"Logistic regression": logistic, "Random forest": forest}

def regime_ml_experiment(prices: pd.Series, test_fraction: float = 0.20, feature_window: int = 21, horizon: int = 21, random_state: int = 42) -> dict:
    dataset = build_regime_dataset(prices, feature_window, horizon)
    if dataset.empty or not 0.15 <= test_fraction <= 0.35:
        return {"available": False, "reason": "Insufficient data or invalid test fraction."}
    test_start = int(len(dataset) * (1.0 - test_fraction))
    if test_start < 120 or len(dataset) - test_start < 30:
        return {"available": False, "reason": "Insufficient observations for chronological train/validation/test validation."}
    development, test = dataset.iloc[:test_start].copy(), dataset.iloc[test_start:].copy()
    train_end = int(len(development) * 0.75)
    if train_end < 60 or len(development) - train_end < 30:
        return {"available": False, "reason": "Insufficient observations for training and validation samples."}
    train, validation = development.iloc[:train_end].copy(), development.iloc[train_end:].copy()
    thresholds = _thresholds(train["future_volatility"])
    if thresholds is None:
        return {"available": False, "reason": "Training volatility distribution is not sufficiently variable."}
    y_train = label_regimes(train["future_volatility"], thresholds)
    y_validation = label_regimes(validation["future_volatility"], thresholds)
    y_test = label_regimes(test["future_volatility"], thresholds)
    if y_train.nunique() < 3 or y_validation.nunique() < 2 or y_test.nunique() < 2:
        return {"available": False, "reason": "The selected sample does not contain enough regime variation."}
    X_train, X_validation, X_test = train[FEATURE_COLUMNS], validation[FEATURE_COLUMNS], test[FEATURE_COLUMNS]

    validation_evaluations = []
    for name, model in _build_models(random_state).items():
        model.fit(X_train, y_train)
        pred = model.predict(X_validation)
        metrics = _metrics(y_validation, pred, REGIMES)
        metrics["Model"] = name
        validation_evaluations.append(metrics)
    validation_table = pd.DataFrame(validation_evaluations)[["Model", "accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1"]]
    selected_model_name = str(validation_table.sort_values(["balanced_accuracy", "macro_f1", "accuracy"], ascending=False).iloc[0]["Model"])

    development_combined = pd.concat([train, validation])
    y_development = label_regimes(development_combined["future_volatility"], thresholds)
    selected_model = _build_models(random_state)[selected_model_name]
    selected_model.fit(development_combined[FEATURE_COLUMNS], y_development)
    final_predictions = selected_model.predict(X_test)
    final_row = _add_test_uncertainty(_metrics(y_test, final_predictions, REGIMES) | {"Model": selected_model_name}, y_test, final_predictions, random_state)

    baseline_pred = _persistence_predictions(test["volatility_21d"], thresholds)
    baseline = _add_test_uncertainty(_metrics(y_test, baseline_pred.to_numpy(), REGIMES) | {"Model": "Persistence baseline"}, y_test, baseline_pred.to_numpy(), random_state + 1)
    final_row["balanced_accuracy_delta_vs_baseline"] = final_row["balanced_accuracy"] - baseline["balanced_accuracy"]
    baseline["balanced_accuracy_delta_vs_baseline"] = 0.0

    prediction_frame = pd.DataFrame({"Actual Regime": y_test, "Selected Model Prediction": pd.Series(final_predictions, index=X_test.index), "Persistence Baseline": baseline_pred}, index=test.index)
    matrix = pd.DataFrame(confusion_matrix(y_test, final_predictions, labels=REGIMES), index=REGIMES, columns=REGIMES)
    importance = pd.DataFrame()
    if selected_model_name == "Random forest" and hasattr(selected_model, "feature_importances_"):
        importance = pd.DataFrame({"Feature": FEATURE_COLUMNS, "Importance": selected_model.feature_importances_}).sort_values("Importance", ascending=False)

    evaluation_columns = ["Model", "accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", "accuracy_ci_low", "accuracy_ci_high", "balanced_accuracy_ci_low", "balanced_accuracy_ci_high", "macro_f1_ci_low", "macro_f1_ci_high", "balanced_accuracy_delta_vs_baseline"]
    final_table = pd.DataFrame([final_row, baseline])
    for column in evaluation_columns:
        if column not in final_table:
            final_table[column] = np.nan

    return {
        "available": True,
        "observations": int(len(dataset)), "train_observations": int(len(train)), "validation_observations": int(len(validation)), "test_observations": int(len(test)),
        "train_end": train.index[-1], "validation_end": validation.index[-1], "test_start": test.index[0], "horizon": horizon,
        "thresholds": {"low": thresholds[0], "high": thresholds[1]}, "selected_model": selected_model_name,
        "validation_evaluations": validation_table, "evaluations": final_table[evaluation_columns],
        "confusion_matrices": {selected_model_name: matrix}, "predictions": prediction_frame, "feature_importance": importance,
        "methodology": {
            "split": "Chronological development/test split; development is split chronologically into train and validation",
            "development_fraction": 1.0 - test_fraction,
            "validation_selection": "Candidate selected using validation balanced accuracy, then macro F1 and accuracy as deterministic tie-breakers",
            "final_test": "Untouched until model specification was locked; final selected model refit on train + validation before one final test evaluation",
            "feature_lag": "Features at t use observations available through t",
            "target": f"Forward {horizon}-trading-day realized volatility regime",
            "thresholds": "33rd/67th percentiles estimated from training targets only and then held fixed",
            "models": "Standardized logistic regression and constrained random forest",
            "baseline": "Persistence using current volatility and training thresholds; reported separately from model selection",
            "uncertainty": "Percentile bootstrap 95% confidence intervals computed only on the untouched final test predictions",
            "bootstrap_resamples": 1000,
            "random_state": random_state,
        },
    }
