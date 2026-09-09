# MScFE Capstone Recorded Presentation — Defence Master Note

> This document is a living preparation note. Final numerical results and claims must be inserted only after the corresponding experiments are completed.

## 1. Opening

**What I will say:**

Good day. My name is Gbenga Olufisayo. My MScFE capstone project focuses on the development and evaluation of NG Finance Pro, a quantitative financial intelligence system designed to support market-risk measurement, portfolio-risk analysis and financial decision-making across emerging and global financial markets.

**Core point to defend:**
The application is the implementation layer. The academic contribution comes from the quantitative methodology, empirical evaluation, validation and evidence.

## 2. Why This Problem?

**Likely examiner concern:** Why is a new system needed?

**Answer:** Financial decision-makers need more than descriptive market information. They need quantitative estimates of tail risk, portfolio risk, changing market regimes and model reliability. NG Finance Pro integrates these analytical tasks into a reproducible decision-support environment.

## 3. Why Is This an MScFE Project?

**Answer:** The project applies mathematical, statistical and computational financial-engineering methods to a real financial decision problem. These include risk modelling, portfolio optimization, stochastic simulation, machine learning, time-series features, out-of-sample evaluation and statistical validation.

## 4. Why These Assets?

**Answer:** The asset universe combines a Nigerian-linked currency instrument with selected global cross-asset instruments. This provides an emerging-market perspective while allowing analysis of different risk characteristics and correlations. The final universe and period will be justified and frozen in the final methodology.

## 5. Why VaR and Expected Shortfall?

**Answer:** VaR provides a specified loss threshold at a chosen confidence level, while Expected Shortfall evaluates the severity of losses beyond that threshold. Using both provides a more complete view of tail risk.

## 6. Why Three VaR Models?

**Answer:** Different VaR approaches rely on different assumptions. Historical VaR is empirical, parametric VaR imposes a distributional assumption, and Monte Carlo VaR uses simulated outcomes. Comparing them allows model risk and sensitivity to assumptions to be examined.

## 7. Why Portfolio Optimization?

**Answer:** Investors are exposed to portfolios rather than isolated assets. Correlation and covariance determine how individual risks combine. Minimum-variance allocation therefore provides a quantitative framework for evaluating whether risk can be reduced through diversification.

## 8. Why Equal-Weight Benchmark?

**Answer:** An optimized portfolio needs a meaningful benchmark. Equal weighting is transparent, reproducible and does not depend on the optimization procedure. Comparing both portfolios provides evidence about whether the optimization adds value rather than simply producing a different allocation.

## 9. Why Machine Learning?

**Answer:** The machine-learning component does not attempt to claim that prices can be predicted reliably. It investigates whether observable market characteristics provide information about future volatility regimes.

## 10. Why These Features?

The selected features represent different dimensions of market behaviour:

- return captures recent price movement;
- momentum captures medium-term directional behaviour;
- volatility captures risk intensity;
- trend measures price position relative to a moving average.

The final feature set will be justified based on the research question and literature.

## 11. How Was Look-Ahead Bias Controlled?

**Answer:** Features are constructed using information available at the prediction date. Future volatility is used only to construct the target, not as an input feature. Walk-forward evaluation preserves chronological ordering so future observations cannot influence earlier decisions.

## 12. How Was Data Leakage Controlled?

**Answer:** The final test period is kept separate from model-selection decisions. Training and validation information are used to choose the model, while the final test set is used only for the final performance assessment.

## 13. Why Walk-Forward Testing?

**Answer:** Financial data are time ordered and market relationships can change. Walk-forward testing more closely represents the real decision process because each model is evaluated on observations that occur after the information used to estimate it.

## 14. Why Transaction Costs?

**Answer:** A strategy that appears profitable before costs may not be economically useful after implementation costs. Transaction costs therefore provide a more realistic evaluation of strategy and portfolio performance.

## 15. How Do You Know the VaR Model Works?

**Answer:** We compare VaR forecasts with subsequent realized returns and examine exception frequency and independence. Kupiec, Christoffersen and conditional-coverage tests provide formal statistical evidence where the available sample is sufficient.

## 16. Why Stress Testing?

**Answer:** Historical models cannot guarantee adequate representation of extreme future events. Stress testing therefore evaluates portfolio sensitivity to explicitly defined adverse scenarios outside the normal historical distribution.

## 17. Why Robustness Testing?

**Answer:** Quantitative conclusions can depend on modelling assumptions. We therefore vary confidence levels, estimation windows and risk-model specifications and use bootstrap procedures to examine uncertainty. This allows us to distinguish stable findings from assumption-sensitive findings.

## 18. What Is the Main Contribution?

**Answer:** The intended contribution is an integrated, reproducible quantitative financial intelligence framework connecting market-risk measurement, portfolio allocation, volatility-regime analysis, machine learning, out-of-sample evaluation, statistical validation, stress testing and robustness analysis within one operational environment. The final contribution statement will be tied to the empirical results.

## 19. What Are the Limitations?

**Answer:** Limitations include historical-data dependence, distributional assumptions, parameter uncertainty, non-stationarity, structural market changes, transaction-cost assumptions and the fact that model performance in historical samples does not guarantee future performance.

## 20. Closing

**What I will say:**

The project demonstrates how financial engineering can transform raw market observations into measurable risk information and decision-support evidence. The system does not rely on a single model; instead, it combines multiple quantitative approaches and evaluates them through out-of-sample testing, statistical validation, stress analysis and robustness testing. NG Finance Pro provides the operational environment through which this quantitative framework can be applied and interpreted.

## Final Defence Rule

Never defend a result that has not been empirically established. If the evidence is mixed, the presentation must report the mixed evidence. If a model performs poorly, that result is part of the research rather than something to hide.
