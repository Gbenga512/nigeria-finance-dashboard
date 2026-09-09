"""Statistical validation tools for VaR model backtests."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from analytics.quant_risk import historical_var


def _clean_returns(returns):
    return pd.to_numeric(returns, errors="coerce").dropna().reset_index(drop=True)


def var_exception_series(returns, confidence=0.95, window=252):
    clean = _clean_returns(returns)
    if len(clean) <= window or not 0 < confidence < 1 or window < 1:
        return pd.Series(dtype="int64")
    values = []
    for i in range(window, len(clean)):
        var = historical_var(clean.iloc[i-window:i], confidence)
        values.append(int(var is not None and float(clean.iloc[i]) < -var))
    return pd.Series(values, dtype="int64")


def _chi_square1_pvalue(statistic):
    return float(math.erfc(math.sqrt(max(0.0, statistic) / 2.0)))


def kupiec_pof_test(returns, confidence=0.95, window=252):
    """Kupiec proportion-of-failures test for unconditional VaR coverage."""
    exceptions = var_exception_series(returns, confidence, window)
    n = len(exceptions)
    x = int(exceptions.sum())
    alpha = 1.0 - confidence
    if n == 0:
        return {"observations": 0, "exceptions": 0, "exception_rate": None, "expected_rate": alpha, "lr_stat": None, "p_value": None, "pass_5pct": None}
    phat = x / n
    eps = 1e-12
    p0 = min(max(alpha, eps), 1 - eps)
    p1 = min(max(phat, eps), 1 - eps)
    log_l0 = (n-x) * math.log(1-p0) + x * math.log(p0)
    log_l1 = (n-x) * math.log(1-p1) + x * math.log(p1)
    lr = max(0.0, -2.0 * (log_l0 - log_l1))
    p_value = _chi_square1_pvalue(lr)
    return {"observations": n, "exceptions": x, "exception_rate": phat, "expected_rate": alpha, "lr_stat": lr, "p_value": p_value, "pass_5pct": bool(p_value >= 0.05)}


def christoffersen_independence_test(returns, confidence=0.95, window=252):
    """Christoffersen independence test for serial dependence in exceptions."""
    exceptions = var_exception_series(returns, confidence, window).to_numpy()
    n = len(exceptions)
    if n < 2:
        return {"observations": n, "exceptions": int(exceptions.sum()), "lr_stat": None, "p_value": None, "pass_5pct": None}
    n00 = n01 = n10 = n11 = 0
    for previous, current in zip(exceptions[:-1], exceptions[1:]):
        if previous == 0 and current == 0: n00 += 1
        elif previous == 0 and current == 1: n01 += 1
        elif previous == 1 and current == 0: n10 += 1
        else: n11 += 1
    total = n00+n01+n10+n11
    pi = (n01+n11)/total if total else 0.0
    pi01 = n01/(n00+n01) if (n00+n01) else 0.0
    pi11 = n11/(n10+n11) if (n10+n11) else 0.0
    eps = 1e-12
    def term(count, probability):
        p = min(max(probability, eps), 1-eps)
        return count * math.log(p)
    log_l0 = term(n00+n10, 1-pi) + term(n01+n11, pi)
    log_l1 = term(n00, 1-pi01) + term(n01, pi01) + term(n10, 1-pi11) + term(n11, pi11)
    lr = max(0.0, -2.0 * (log_l0-log_l1))
    p_value = _chi_square1_pvalue(lr)
    return {"observations": n, "exceptions": int(exceptions.sum()), "lr_stat": lr, "p_value": p_value, "pass_5pct": bool(p_value >= 0.05), "n00": n00, "n01": n01, "n10": n10, "n11": n11}


def conditional_coverage_test(returns, confidence=0.95, window=252):
    """Christoffersen conditional-coverage test: coverage plus independence."""
    kupiec = kupiec_pof_test(returns, confidence, window)
    independence = christoffersen_independence_test(returns, confidence, window)
    if kupiec["lr_stat"] is None or independence["lr_stat"] is None:
        combined = p_value = passed = None
    else:
        combined = float(kupiec["lr_stat"] + independence["lr_stat"])
        # Chi-square(2) survival function is exp(-x/2).
        p_value = float(math.exp(-combined / 2.0))
        passed = bool(p_value >= 0.05)
    return {"observations": kupiec["observations"], "exceptions": kupiec["exceptions"], "exception_rate": kupiec["exception_rate"], "expected_rate": kupiec["expected_rate"], "kupiec_lr": kupiec["lr_stat"], "kupiec_p_value": kupiec["p_value"], "independence_lr": independence["lr_stat"], "independence_p_value": independence["p_value"], "conditional_coverage_lr": combined, "conditional_coverage_p_value": p_value, "pass_5pct": passed}


def bootstrap_exception_rate_ci(returns, confidence=0.95, window=252, bootstrap_samples=2000, seed=42):
    """Bootstrap percentile interval for the observed VaR exception rate."""
    exceptions = var_exception_series(returns, confidence, window).to_numpy(dtype=float)
    n = len(exceptions)
    if n == 0 or bootstrap_samples < 100:
        return {"observations": n, "exception_rate": None, "ci_lower": None, "ci_upper": None, "bootstrap_samples": bootstrap_samples}
    rng = np.random.default_rng(seed)
    sampled = rng.choice(exceptions, size=(bootstrap_samples, n), replace=True).mean(axis=1)
    return {"observations": n, "exception_rate": float(exceptions.mean()), "ci_lower": float(np.quantile(sampled, 0.025)), "ci_upper": float(np.quantile(sampled, 0.975)), "bootstrap_samples": bootstrap_samples}


def validate_var_model(returns, confidence=0.95, window=252, bootstrap_samples=2000):
    """Run coverage, independence and bootstrap uncertainty diagnostics together."""
    return {"kupiec": kupiec_pof_test(returns, confidence, window), "christoffersen": christoffersen_independence_test(returns, confidence, window), "conditional_coverage": conditional_coverage_test(returns, confidence, window), "bootstrap": bootstrap_exception_rate_ci(returns, confidence, window, bootstrap_samples)}
