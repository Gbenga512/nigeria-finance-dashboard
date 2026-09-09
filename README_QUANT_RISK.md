# NG Finance Pro — Quantitative Risk Layer

NG Finance Pro combines market intelligence, accounting analytics, treasury, reconciliation, budgeting and quantitative risk analytics.

## Quantitative Risk Layer

- Historical Value at Risk (VaR)
- Historical Expected Shortfall (ES)
- Parametric Normal VaR/ES
- Monte Carlo VaR/ES
- GARCH(1,1) conditional volatility and one-step forecast
- EWMA volatility benchmark
- Portfolio volatility
- Correlation analysis
- Component and marginal risk contribution
- Sharpe, Sortino and Calmar ratios
- Maximum drawdown and downside volatility
- Rolling historical VaR backtesting
- Kupiec unconditional-coverage VaR test
- Christoffersen independence and conditional-coverage tests
- USD/NGN FX volatility and exposure stress
- Liquidity runway and coverage metrics
- Liquidity stress scenarios under elevated cash outflows

## Methodology

Daily simple returns are calculated from historical price observations. Portfolio returns use normalized fixed weights. Annualized volatility uses 252 trading days. Historical VaR/ES are non-parametric tail estimates; parametric estimates assume normally distributed returns; Monte Carlo estimates use a reproducible normal simulation with a fixed seed. GARCH(1,1) parameters are estimated by Gaussian quasi-maximum likelihood subject to positivity and covariance-stationarity constraints. EWMA provides a transparent conditional-volatility benchmark. Formal VaR validation uses Kupiec unconditional coverage and Christoffersen independence/conditional-coverage likelihood-ratio tests. Risk-adjusted ratios currently assume a 0% annual risk-free rate.

The liquidity/FX module deliberately separates observed market statistics from user-supplied treasury assumptions. FX exposure stress applies explicit scenario shocks to a Naira-equivalent exposure; liquidity stress applies higher outflow multipliers and a cash haircut. These are scenario analyses, not forecasts.

## MScFE Research Direction

The quantitative layer supports empirical research into market risk, foreign-exchange risk, liquidity risk and portfolio decision support in emerging markets. The application is the demonstration layer; the research contribution should come from model specification, validation, backtesting, stress testing and comparative empirical evaluation.
