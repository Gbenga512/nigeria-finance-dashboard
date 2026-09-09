"""Portfolio-level quantitative risk analytics for NG Finance Pro."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.quant_risk import historical_var, historical_expected_shortfall


def align_returns(price_map: dict[str, pd.Series]) -> pd.DataFrame:
    """Align named price series into a common daily return matrix."""
    series = {}
    for asset, prices in price_map.items():
        clean = pd.to_numeric(prices, errors="coerce").dropna()
        if len(clean) >= 2:
            series[asset] = clean.pct_change()
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).dropna(how="any")


def portfolio_returns(price_map: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """Compute daily portfolio returns using fixed normalized weights."""
    returns = align_returns(price_map)
    if returns.empty:
        return pd.Series(dtype="float64")
    valid_weights = {k: float(v) for k, v in weights.items() if k in returns.columns}
    if not valid_weights:
        return pd.Series(dtype="float64")
    total = sum(valid_weights.values())
    if total == 0:
        return pd.Series(dtype="float64")
    w = pd.Series({k: v / total for k, v in valid_weights.items()})
    return returns[w.index].mul(w, axis=1).sum(axis=1)


def correlation_matrix(price_map: dict[str, pd.Series]) -> pd.DataFrame:
    """Return the daily-return correlation matrix."""
    returns = align_returns(price_map)
    return returns.corr() if not returns.empty else pd.DataFrame()


def monte_carlo_var_es(returns: pd.Series, confidence: float = 0.95, simulations: int = 10000, seed: int = 42) -> tuple[float | None, float | None]:
    """Estimate Monte Carlo VaR and ES from a normal return model."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2 or not 0 < confidence < 1 or simulations < 100:
        return None, None
    rng = np.random.default_rng(seed)
    simulated = rng.normal(float(clean.mean()), float(clean.std(ddof=1)), simulations)
    threshold = float(np.quantile(simulated, 1 - confidence))
    tail = simulated[simulated <= threshold]
    return max(0.0, -threshold), max(0.0, -float(tail.mean()))


def portfolio_risk(price_map: dict[str, pd.Series], weights: dict[str, float], confidence: float = 0.95) -> dict[str, float | int | None]:
    """Return portfolio VaR, ES and volatility metrics."""
    returns = portfolio_returns(price_map, weights)
    if returns.empty:
        return {"observations": 0, "volatility": None, "historical_var": None, "historical_es": None, "monte_carlo_var": None, "monte_carlo_es": None}
    mc_var, mc_es = monte_carlo_var_es(returns, confidence)
    return {"observations": int(len(returns)), "volatility": float(returns.std(ddof=1) * np.sqrt(252)) if len(returns) > 1 else None, "historical_var": historical_var(returns, confidence), "historical_es": historical_expected_shortfall(returns, confidence), "monte_carlo_var": mc_var, "monte_carlo_es": mc_es}


def component_var(price_map: dict[str, pd.Series], weights: dict[str, float], confidence: float = 0.95) -> pd.DataFrame:
    """Approximate component volatility risk using covariance marginal contributions."""
    returns = align_returns(price_map)
    if returns.empty:
        return pd.DataFrame()
    names = [name for name in weights if name in returns.columns]
    if not names:
        return pd.DataFrame()
    w = pd.Series({name: float(weights[name]) for name in names})
    if w.sum() == 0:
        return pd.DataFrame()
    w = w / w.sum()
    cov = returns[names].cov() * 252
    portfolio_vol = float(np.sqrt(w.to_numpy() @ cov.to_numpy() @ w.to_numpy()))
    if portfolio_vol == 0:
        contributions = pd.Series(0.0, index=names)
    else:
        marginal = cov.dot(w) / portfolio_vol
        contributions = w * marginal
    total = float(contributions.sum())
    rows = []
    for name in names:
        rows.append({"Asset": name, "Weight": float(w[name]), "Marginal Risk": float(contributions[name] / w[name]) if w[name] != 0 else 0.0, "Component Volatility Risk": float(contributions[name]), "% of Portfolio Risk": float(contributions[name] / total) if total != 0 else 0.0})
    return pd.DataFrame(rows).sort_values("Component Volatility Risk", ascending=False)


def risk_ratios(returns: pd.Series, risk_free_rate: float = 0.0) -> dict[str, float | None]:
    """Calculate annualized Sharpe, Sortino and Calmar ratios."""
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2:
        return {"sharpe": None, "sortino": None, "calmar": None}
    annual_return = float((1 + clean).prod() ** (252 / len(clean)) - 1)
    excess = clean - risk_free_rate / 252
    annual_vol = float(clean.std(ddof=1) * np.sqrt(252))
    downside = float(np.sqrt(np.mean(np.minimum(excess, 0.0) ** 2)) * np.sqrt(252))
    wealth = (1 + clean).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    max_dd = abs(float(drawdown.min()))
    return {"sharpe": float(excess.mean() / clean.std(ddof=1) * np.sqrt(252)) if annual_vol else None, "sortino": float(excess.mean() * 252 / downside) if downside else None, "calmar": float((annual_return - risk_free_rate) / max_dd) if max_dd else None}


def _normalized_weights(weights: dict[str, float], names: list[str]) -> pd.Series | None:
    valid = pd.Series({k: float(weights[k]) for k in names if k in weights}, dtype=float)
    valid = valid.replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty or float(valid.sum()) == 0:
        return None
    return valid / valid.sum()


def portfolio_walk_forward(price_map: dict[str, pd.Series], weights: dict[str, float], train_window: int = 252, test_window: int = 63, transaction_cost: float = 0.001) -> dict[str, object]:
    """Validate a fixed-weight portfolio through sequential out-of-sample blocks."""
    returns = align_returns(price_map)
    if returns.empty or train_window < 30 or test_window < 1 or transaction_cost < 0 or len(returns) <= train_window:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame()}
    w = _normalized_weights(weights, list(returns.columns))
    if w is None:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame()}
    portfolio = returns[w.index].mul(w, axis=1).sum(axis=1)
    benchmark = returns.mean(axis=1)
    blocks, oos, bench_oos = [], [], []
    start = train_window
    while start < len(portfolio):
        test = portfolio.iloc[start:start + test_window]
        bench = benchmark.iloc[start:start + test_window]
        if test.empty:
            break
        net = test.copy()
        net.iloc[0] -= transaction_cost
        sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(252)) if len(net) > 1 and net.std(ddof=1) else 0.0
        blocks.append({"Block": len(blocks) + 1, "Test Start": test.index[0], "Test End": test.index[-1], "Test Return": float((1 + net).prod() - 1), "Test Sharpe": sharpe, "Benchmark Return": float((1 + bench).prod() - 1), "Turnover": 1.0})
        oos.append(net)
        bench_oos.append(bench)
        start += test_window
    if not oos:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame()}
    oos_series = pd.concat(oos).sort_index()
    bench_series = pd.concat(bench_oos).sort_index()
    ratios = risk_ratios(oos_series)
    summary = {"observations": int(len(oos_series)), "cumulative_return": float((1 + oos_series).prod() - 1), "annualized_return": float((1 + oos_series).prod() ** (252 / len(oos_series)) - 1), "annualized_volatility": float(oos_series.std(ddof=1) * np.sqrt(252)) if len(oos_series) > 1 else 0.0, "sharpe": ratios["sharpe"], "sortino": ratios["sortino"], "calmar": ratios["calmar"], "historical_var": historical_var(oos_series), "historical_es": historical_expected_shortfall(oos_series), "benchmark_cumulative_return": float((1 + bench_series).prod() - 1), "blocks": len(blocks)}
    equity = pd.DataFrame({"Portfolio": (1 + oos_series).cumprod(), "Equal Weight Benchmark": (1 + bench_series).cumprod()})
    return {"summary": summary, "blocks": pd.DataFrame(blocks), "equity": equity}


def minimum_variance_weights(returns: pd.DataFrame) -> pd.Series | None:
    """Compute long-only minimum-variance weights from the training covariance matrix."""
    clean = returns.dropna(how="any")
    if clean.shape[0] < 2 or clean.shape[1] < 1:
        return None
    cov = clean.cov().to_numpy()
    cov = cov + np.eye(cov.shape[0]) * 1e-8
    inv = np.linalg.pinv(cov)
    ones = np.ones(cov.shape[0])
    raw = inv @ ones
    raw = np.maximum(raw, 0.0)
    if raw.sum() == 0:
        raw = ones
    return pd.Series(raw / raw.sum(), index=clean.columns)


def optimized_portfolio_walk_forward(price_map: dict[str, pd.Series], train_window: int = 252, test_window: int = 63, transaction_cost: float = 0.001) -> dict[str, object]:
    """Walk-forward minimum-variance portfolio validation against equal weight."""
    returns = align_returns(price_map)
    if returns.empty or train_window < 30 or test_window < 1 or transaction_cost < 0 or len(returns) <= train_window:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame(), "weights": pd.DataFrame()}
    blocks, oos, benchmark_oos, weight_rows = [], [], [], []
    start = train_window
    while start < len(returns):
        train = returns.iloc[start - train_window:start]
        test = returns.iloc[start:start + test_window]
        if test.empty:
            break
        w = minimum_variance_weights(train)
        if w is None:
            break
        port = test[w.index].mul(w, axis=1).sum(axis=1)
        net = port.copy()
        net.iloc[0] -= transaction_cost
        bench = test.mean(axis=1)
        turnover = 0.0 if not weight_rows else float(np.abs(w - weight_rows[-1]["_weights"]).sum())
        blocks.append({"Block": len(blocks) + 1, "Test Start": test.index[0], "Test End": test.index[-1], "Test Return": float((1 + net).prod() - 1), "Benchmark Return": float((1 + bench).prod() - 1), "Turnover": turnover})
        oos.append(net)
        benchmark_oos.append(bench)
        weight_rows.append({"Block": len(blocks), "Date": test.index[0], "_weights": w, **{asset: float(w.get(asset, 0.0)) for asset in returns.columns}})
        start += test_window
    if not oos:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame(), "weights": pd.DataFrame()}
    oos_series = pd.concat(oos).sort_index()
    bench_series = pd.concat(benchmark_oos).sort_index()
    ratios = risk_ratios(oos_series)
    bench_ratios = risk_ratios(bench_series)
    summary = {"observations": int(len(oos_series)), "cumulative_return": float((1 + oos_series).prod() - 1), "annualized_return": float((1 + oos_series).prod() ** (252 / len(oos_series)) - 1), "annualized_volatility": float(oos_series.std(ddof=1) * np.sqrt(252)), "sharpe": ratios["sharpe"], "sortino": ratios["sortino"], "calmar": ratios["calmar"], "benchmark_cumulative_return": float((1 + bench_series).prod() - 1), "benchmark_sharpe": bench_ratios["sharpe"]}
    weights_df = pd.DataFrame([{k: v for k, v in row.items() if k != "_weights"} for row in weight_rows]).set_index("Date")
    equity = pd.DataFrame({"Minimum Variance": (1 + oos_series).cumprod(), "Equal Weight Benchmark": (1 + bench_series).cumprod()})
    return {"summary": summary, "blocks": pd.DataFrame(blocks), "equity": equity, "weights": weights_df}


def portfolio_stress_matrix(price_map: dict[str, pd.Series], weights: dict[str, float], shocks: list[float]) -> pd.DataFrame:
    """Calculate deterministic portfolio losses under common and asset-specific shocks."""
    if not shocks:
        return pd.DataFrame()
    returns = align_returns(price_map)
    if returns.empty:
        return pd.DataFrame()
    w = _normalized_weights(weights, list(returns.columns))
    if w is None:
        return pd.DataFrame()
    rows = []
    for shock in shocks:
        rows.append({"Scenario": f"Common shock {shock:.0%}", "Portfolio Loss": float(-shock) if shock < 0 else 0.0})
    for asset in w.index:
        for shock in shocks:
            loss = max(0.0, -float(w[asset] * shock))
            rows.append({"Scenario": f"{asset} shock {shock:.0%}", "Portfolio Loss": loss})
    return pd.DataFrame(rows)
