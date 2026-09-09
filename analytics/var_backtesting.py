"""Formal statistical backtests for Value-at-Risk forecasts."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.stats import chi2


def _safe_log(x: float) -> float:
    return math.log(max(float(x), 1e-12))


def exception_series(returns: pd.Series, var_forecast: pd.Series) -> pd.Series:
    r = pd.to_numeric(returns, errors="coerce")
    v = pd.to_numeric(var_forecast, errors="coerce")
    aligned = pd.concat([r.rename("return"), v.rename("var")], axis=1).dropna()
    if aligned.empty:
        return pd.Series(dtype=int)
    return (aligned["return"] < -aligned["var"].abs()).astype(int)


def rolling_historical_var(returns: pd.Series, confidence: float = 0.95, window: int = 252) -> pd.Series:
    """Generate genuine one-step-ahead historical VaR forecasts using only prior observations."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) <= window or not 0 < confidence < 1 or window < 20:
        return pd.Series(dtype=float)
    forecasts = []
    indices = []
    for i in range(window, len(clean)):
        sample = clean.iloc[i-window:i]
        var = max(0.0, -float(np.quantile(sample.to_numpy(), 1 - confidence, method="nearest")))
        forecasts.append(var)
        indices.append(clean.index[i])
    return pd.Series(forecasts, index=indices, name="VaR")


def kupiec_pof(exceptions: pd.Series, confidence: float = 0.95) -> dict:
    x = pd.Series(exceptions, dtype=float).dropna().astype(int)
    n = len(x)
    if n == 0 or not 0 < confidence < 1:
        return {"statistic": np.nan, "p_value": np.nan, "exceptions": 0, "observations": n, "expected_rate": 1-confidence, "exception_rate": np.nan, "reject_5pct": None}
    k = int(x.sum())
    p = 1.0 - confidence
    phat = k / n
    log_l0 = (n-k)*_safe_log(1-p) + k*_safe_log(p)
    log_l1 = (n-k)*_safe_log(1-phat) + k*_safe_log(phat)
    stat = max(0.0, -2.0*(log_l0-log_l1))
    p_value = float(chi2.sf(stat, 1))
    return {"statistic": float(stat), "p_value": p_value, "exceptions": k, "observations": n, "expected_rate": p, "exception_rate": phat, "reject_5pct": p_value < 0.05}


def christoffersen_independence(exceptions: pd.Series) -> dict:
    x = pd.Series(exceptions, dtype=int).dropna().to_numpy()
    if len(x) < 2:
        return {"statistic": np.nan, "p_value": np.nan, "n00": 0, "n01": 0, "n10": 0, "n11": 0, "reject_5pct": None}
    prev, curr = x[:-1], x[1:]
    n00 = int(((prev==0)&(curr==0)).sum()); n01 = int(((prev==0)&(curr==1)).sum())
    n10 = int(((prev==1)&(curr==0)).sum()); n11 = int(((prev==1)&(curr==1)).sum())
    pi0 = n01 / max(n00+n01, 1); pi1 = n11 / max(n10+n11, 1)
    total = n01+n11; pi = total / max(n00+n01+n10+n11, 1)
    ll_ind = n00*_safe_log(1-pi0)+n01*_safe_log(pi0)+n10*_safe_log(1-pi1)+n11*_safe_log(pi1)
    ll_null = (n00+n10)*_safe_log(1-pi)+(n01+n11)*_safe_log(pi)
    stat = max(0.0, -2.0*(ll_null-ll_ind)); p_value = float(chi2.sf(stat,1))
    return {"statistic": float(stat), "p_value": p_value, "n00": n00, "n01": n01, "n10": n10, "n11": n11, "reject_5pct": p_value < 0.05}


def christoffersen_conditional_coverage(exceptions: pd.Series, confidence: float = 0.95) -> dict:
    pof = kupiec_pof(exceptions, confidence); independence = christoffersen_independence(exceptions)
    if np.isnan(pof["statistic"]) or np.isnan(independence["statistic"]):
        return {**pof, "independence_statistic": independence["statistic"], "independence_p_value": independence["p_value"], "statistic": np.nan, "p_value": np.nan, "reject_5pct": None}
    stat = pof["statistic"] + independence["statistic"]
    p_value = float(chi2.sf(stat, 2))
    return {**pof, "independence_statistic": independence["statistic"], "independence_p_value": independence["p_value"], "statistic": float(stat), "p_value": p_value, "reject_5pct": p_value < 0.05}


def backtest_var(returns: pd.Series, var_forecast: pd.Series, confidence: float = 0.95) -> dict:
    exceptions = exception_series(returns, var_forecast)
    return {"exceptions": exceptions, "kupiec": kupiec_pof(exceptions, confidence), "independence": christoffersen_independence(exceptions), "conditional_coverage": christoffersen_conditional_coverage(exceptions, confidence)}
