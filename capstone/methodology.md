# MScFE Capstone Methodology Framework

## 1. Research Design

The study follows a quantitative empirical research design. Historical financial-market observations are transformed into returns and engineered features, which are then used in risk measurement, portfolio allocation, volatility-regime analysis and machine-learning experiments.

The project separates descriptive analysis from predictive and decision-making experiments. Predictive and portfolio claims must be evaluated out of sample.

## 2. Data Principles

- Use documented historical market data from the selected data provider.
- Record the instruments, symbols, observation period, frequency and retrieval date.
- Clean numeric observations and remove invalid/missing values using explicit rules.
- Compute simple returns consistently unless an experiment explicitly requires another definition.
- Preserve chronological ordering.
- Do not use future observations in features available at the prediction date.
- Freeze the principal dataset specification before final experiments.

## 3. Risk Measurement

The primary risk measures are historical VaR, parametric normal VaR, Monte Carlo normal VaR, historical Expected Shortfall, parametric Expected Shortfall and Monte Carlo Expected Shortfall.

For a confidence level c, historical VaR is estimated from the empirical lower-tail return quantile. Expected Shortfall measures the average loss conditional on returns falling beyond the VaR threshold.

Annualized volatility uses daily standard deviation multiplied by sqrt(252), where appropriate. Maximum drawdown measures the largest peak-to-trough decline in the observed wealth path.

## 4. Portfolio Analysis

Portfolio returns are formed from aligned asset returns and specified portfolio weights. Portfolio risk is assessed using volatility, VaR, Expected Shortfall and component-risk diagnostics.

The principal optimization experiment uses a long-only minimum-variance portfolio. Its performance is compared with an equal-weight benchmark. The optimizer is estimated using information available in the training period and applied to subsequent out-of-sample observations.

Transaction costs are incorporated into portfolio/strategy evaluation where specified by the experiment protocol.

## 5. Volatility-Regime Analysis

Volatility regimes are identified from rolling volatility using training-period thresholds where the experiment is predictive. The framework distinguishes low, normal and high volatility states.

Ex-post regime analysis may be used for descriptive interpretation, but it must not be presented as a predictive result.

## 6. Machine Learning

Candidate models include Logistic Regression and Random Forest. Features include one-day return, five-day momentum, twenty-one-day momentum, twenty-one-day annualized volatility and twenty-one-day trend.

The target is future volatility regime constructed from future observations. Feature rows must therefore be aligned so that future target information cannot enter the predictors.

The final test set must remain untouched during model and hyperparameter selection. A chronological training/validation process will be used for candidate selection, followed by one final evaluation on the locked test period.

Performance should include balanced accuracy and appropriate classification metrics such as accuracy, macro precision, macro recall and macro F1. A persistence benchmark is reported separately from learned models.

## 7. Walk-Forward Evaluation

Financial strategies and dynamic portfolios are evaluated chronologically. At each walk-forward step, the training sample contains only information available before the test block. Candidate strategy selection occurs within training/validation data, and the selected approach is then evaluated on the next unseen block.

The methodology explicitly controls look-ahead bias, including signal timing and the boundary between training and test observations.

## 8. VaR Model Validation

VaR forecasts are compared with subsequent realized returns. Validation includes exception counts and rates, Kupiec proportion-of-failures testing, Christoffersen independence testing and conditional-coverage testing where sufficient observations are available.

Bootstrap confidence intervals may be used to quantify uncertainty around observed exception rates and risk estimates.

## 9. Stress Testing

Stress tests apply explicitly defined adverse shocks to individual assets or the portfolio. Stress analysis is deterministic scenario analysis and is not interpreted as a probability forecast.

Where relevant, scenarios should include common market shocks and asset-specific shocks. Scenario assumptions must be documented and kept separate from historical model estimates.

## 10. Robustness and Sensitivity

Robustness analysis changes material assumptions, including VaR confidence levels, estimation windows and risk-model specifications. Bootstrap procedures are used to examine statistical uncertainty around selected historical risk metrics.

A finding will be described as robust only when the relevant evidence supports stability across the predefined sensitivity tests.

## 11. Performance Metrics

Depending on the experiment, evaluation includes:

- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- maximum drawdown
- hit rate
- VaR exception rate
- balanced accuracy
- macro F1
- model-validation statistics
- transaction-cost-adjusted performance.

No metric will be interpreted in isolation. Risk-adjusted and benchmark-relative evidence will be considered together.

## 12. Reproducibility

All experiments must use fixed random seeds where stochastic simulation is involved, record model parameters, document data assumptions and produce outputs that can be regenerated from source code.

The repository should retain tests for core analytical functions and CI should remain passing before major research results are treated as final.

## 13. Limitations to Address

The final report must discuss data availability, distributional assumptions, parameter uncertainty, non-stationarity, structural breaks, transaction-cost assumptions, model risk and the limits of historical evidence for forecasting future market behaviour.

## 14. Decision Rule for Conclusions

Conclusions must be evidence-led. The project must not claim that one model, strategy or portfolio is superior unless the predefined out-of-sample experiment and robustness evidence support that conclusion.
