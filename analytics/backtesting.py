"""Walk-forward strategy validation for NG Finance Pro research."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.regime import classify_volatility_regime, rolling_volatility

CANDIDATE_STRATEGIES = ("momentum", "mean_reversion", "buy_hold")


def _clean_prices(prices: pd.Series) -> pd.Series:
    clean = pd.to_numeric(prices, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return clean[clean > 0]


def _safe_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 2 or clean.std(ddof=1) == 0:
        return 0.0
    return float(clean.mean() / clean.std(ddof=1) * np.sqrt(periods_per_year))


def _max_drawdown(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    equity = (1.0 + clean).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min()) if not drawdown.empty else 0.0


def _sortino(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return 0.0
    downside_dev = float(np.sqrt(np.mean(np.minimum(clean.to_numpy(), 0.0) ** 2)))
    if downside_dev == 0:
        return 0.0
    return float(clean.mean() / downside_dev * np.sqrt(periods_per_year))


def _annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return 0.0
    growth = float((1.0 + clean).prod())
    if growth <= 0:
        return -1.0
    return float(growth ** (periods_per_year / len(clean)) - 1.0)


def strategy_signal(prices: pd.Series, strategy: str) -> pd.Series:
    """Create long/cash signals from information available at each close."""
    clean = _clean_prices(prices)
    if strategy not in CANDIDATE_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")
    if strategy == "buy_hold":
        signal = pd.Series(1.0, index=clean.index)
    elif strategy == "momentum":
        momentum = clean.pct_change(21)
        trend = clean / clean.rolling(21).mean() - 1.0
        signal = ((momentum > 0) & (trend > 0)).astype(float)
    else:
        distance = clean / clean.rolling(21).mean() - 1.0
        signal = (distance < 0).astype(float)
    return signal.shift(1).fillna(0.0).rename(strategy)


def apply_transaction_costs(gross_returns: pd.Series, signal: pd.Series, transaction_cost: float = 0.001) -> pd.Series:
    """Deduct proportional costs whenever the position changes."""
    if transaction_cost < 0:
        raise ValueError("transaction_cost must be non-negative")
    turnover = signal.diff().abs().fillna(signal.abs())
    return (gross_returns - turnover * transaction_cost).rename("strategy_return")


def performance_metrics(returns: pd.Series, benchmark: pd.Series | None = None) -> dict[str, float | int | None]:
    """Calculate standard out-of-sample performance statistics."""
    clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {"observations": 0, "cumulative_return": None, "annualized_return": None, "annualized_volatility": None, "sharpe": None, "sortino": None, "maximum_drawdown": None, "hit_rate": None, "turnover": None, "benchmark_cumulative_return": None}
    benchmark_clean = None if benchmark is None else pd.to_numeric(benchmark, errors="coerce").reindex(clean.index).dropna()
    return {
        "observations": int(len(clean)),
        "cumulative_return": float((1.0 + clean).prod() - 1.0),
        "annualized_return": _annualized_return(clean),
        "annualized_volatility": float(clean.std(ddof=1) * np.sqrt(252)) if len(clean) > 1 else 0.0,
        "sharpe": _safe_sharpe(clean),
        "sortino": _sortino(clean),
        "maximum_drawdown": _max_drawdown(clean),
        "hit_rate": float((clean > 0).mean()),
        "turnover": None,
        "benchmark_cumulative_return": None if benchmark_clean is None or benchmark_clean.empty else float((1.0 + benchmark_clean).prod() - 1.0),
    }


def select_strategy(train_prices: pd.Series, transaction_cost: float = 0.001) -> tuple[str, float]:
    """Select one candidate using net training Sharpe, including transaction costs."""
    scores: dict[str, float] = {}
    prices = _clean_prices(train_prices)
    returns = prices.pct_change().fillna(0.0)
    for strategy in CANDIDATE_STRATEGIES:
        signal = strategy_signal(prices, strategy)
        strategy_returns = apply_transaction_costs(returns * signal, signal, transaction_cost)
        scores[strategy] = _safe_sharpe(strategy_returns)
    selected = max(scores, key=scores.get)
    return selected, float(scores[selected])


def _regime_labels(prices: pd.Series, window: int = 21) -> pd.Series:
    returns = _clean_prices(prices).pct_change()
    volatility = rolling_volatility(returns, window)
    return classify_volatility_regime(volatility)


def regime_conditioned_performance(returns: pd.Series, prices: pd.Series, regime_window: int = 21) -> pd.DataFrame:
    """Summarize realized performance by volatility regime as an ex-post diagnostic."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    clean_prices = _clean_prices(prices).reindex(clean_returns.index).ffill()
    labels = _regime_labels(clean_prices, regime_window).reindex(clean_returns.index)
    data = pd.DataFrame({"Return": clean_returns, "Regime": labels}).dropna()
    if data.empty:
        return pd.DataFrame(columns=["Regime", "Observations", "Cumulative Return", "Annualized Volatility", "Sharpe", "Hit Rate"])
    rows = []
    for regime, group in data.groupby("Regime", sort=False):
        rows.append({
            "Regime": regime,
            "Observations": int(len(group)),
            "Cumulative Return": float((1.0 + group["Return"]).prod() - 1.0),
            "Annualized Volatility": float(group["Return"].std(ddof=1) * np.sqrt(252)) if len(group) > 1 else 0.0,
            "Sharpe": _safe_sharpe(group["Return"]),
            "Hit Rate": float((group["Return"] > 0).mean()),
        })
    return pd.DataFrame(rows).sort_values("Regime")


def walk_forward_backtest(prices: pd.Series, train_window: int = 252, test_window: int = 63, transaction_cost: float = 0.001) -> dict[str, object]:
    """Run expanding-block walk-forward model selection without look-ahead bias."""
    clean = _clean_prices(prices)
    if train_window < 30 or test_window < 1 or transaction_cost < 0:
        raise ValueError("Invalid walk-forward parameters")
    if len(clean) <= train_window:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame(), "regime_summary": pd.DataFrame()}
    block_rows: list[dict[str, object]] = []
    oos_returns: list[pd.Series] = []
    benchmark_returns: list[pd.Series] = []
    start = train_window
    while start < len(clean):
        train = clean.iloc[:start]
        test = clean.iloc[start : start + test_window]
        if test.empty:
            break
        selected, train_sharpe = select_strategy(train, transaction_cost)
        test_signal = strategy_signal(pd.concat([train.tail(21), test]), selected).reindex(test.index)
        test_gross = test.pct_change().fillna(test.iloc[0] / train.iloc[-1] - 1.0) * test_signal
        test_strategy = apply_transaction_costs(test_gross, test_signal, transaction_cost)
        test_benchmark = test.pct_change().fillna(test.iloc[0] / train.iloc[-1] - 1.0)
        metrics = performance_metrics(test_strategy, test_benchmark)
        turnover = float(test_signal.diff().abs().fillna(test_signal.abs()).sum())
        block_rows.append({"Block": len(block_rows) + 1, "Test Start": test.index[0], "Test End": test.index[-1], "Selected Strategy": selected, "Training Sharpe": train_sharpe, "Test Return": metrics["cumulative_return"], "Test Sharpe": metrics["sharpe"], "Test Max Drawdown": metrics["maximum_drawdown"], "Benchmark Return": metrics["benchmark_cumulative_return"], "Turnover": turnover})
        oos_returns.append(test_strategy)
        benchmark_returns.append(test_benchmark)
        start += test_window
    if not oos_returns:
        return {"summary": {}, "blocks": pd.DataFrame(), "equity": pd.DataFrame(), "regime_summary": pd.DataFrame()}
    oos = pd.concat(oos_returns).sort_index()
    benchmark = pd.concat(benchmark_returns).sort_index()
    summary = performance_metrics(oos, benchmark)
    summary["turnover"] = float(sum(row["Turnover"] for row in block_rows))
    summary["benchmark_annualized_return"] = _annualized_return(benchmark)
    summary["oos_alpha"] = float(summary["annualized_return"] - summary["benchmark_annualized_return"])
    summary["blocks"] = len(block_rows)
    equity = pd.DataFrame({"Strategy": (1.0 + oos).cumprod(), "Benchmark": (1.0 + benchmark).cumprod()})
    return {"summary": summary, "blocks": pd.DataFrame(block_rows), "equity": equity, "regime_summary": regime_conditioned_performance(oos, clean.reindex(oos.index).ffill())}
