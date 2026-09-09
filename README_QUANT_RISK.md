# NG Finance Pro — Quantitative Risk Layer

NG Finance Pro combines market intelligence, accounting analytics, treasury, reconciliation, budgeting and quantitative risk analytics.

## Quantitative Risk Layer

- Historical Value at Risk (VaR)
- Historical Expected Shortfall (ES)
- Parametric Normal VaR/ES
- Monte Carlo VaR/ES
- Portfolio volatility
- Correlation analysis
- Component and marginal risk contribution
- Sharpe, Sortino and Calmar ratios
- Maximum drawdown and downside volatility
- Rolling historical VaR backtesting

## Methodology

Daily simple returns are calculated from historical price observations. Portfolio returns use normalized fixed weights. Annualized volatility uses 252 trading days. Historical VaR/ES are non-parametric tail estimates; parametric estimates assume normally distributed returns; Monte Carlo estimates use a reproducible normal simulation with a fixed seed. Risk-adjusted ratios currently assume a 0% annual risk-free rate.

## MScFE Research Direction

The quantitative layer supports empirical research into market risk and portfolio decision support in emerging markets. The application is the demonstration layer; the research contribution should come from model specification, validation, backtesting, stress testing and comparative empirical evaluation.
