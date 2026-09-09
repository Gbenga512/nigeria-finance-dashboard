# MScFE Capstone Experiment Protocol

## Purpose

This protocol defines how final quantitative experiments will be conducted so that model comparisons are reproducible and the final test set is not used for model selection.

## 1. Data Freeze

Before final experiments, record:

- data provider
- asset universe
- symbols
- frequency
- start and end dates
- retrieval date
- missing-data treatment
- return definition
- any transformations

The final evaluation dataset must not be changed after the test protocol is locked except for documented data corrections that apply independently of model results.

## 2. Chronological Dataset Structure

Use chronological partitions rather than random shuffling for time-series experiments.

Recommended structure:

**Training → Validation → Final Test**

Training data are used for estimation. Validation data are used for model/parameter selection. The final test set remains untouched until the selected specification is frozen.

For walk-forward experiments, use sequential training and test blocks with no future information entering the training or selection process.

## 3. Model Selection

Candidate models may include historical risk, parametric risk, Monte Carlo risk, Logistic Regression, Random Forest and portfolio allocation alternatives, depending on the experiment.

Model selection must be based on predefined training/validation criteria. The final test period must not determine which candidate is reported as the preferred model.

A benchmark must be retained even when it is not the preferred method.

## 4. Primary Experiment Register

### Experiment R1 — Risk Model Comparison

**Question:** How do alternative VaR/ES methodologies differ in measured tail risk?

**Models:** Historical, Parametric Normal, Monte Carlo Normal.

**Outputs:** VaR, Expected Shortfall, model disagreement, sensitivity by confidence level.

### Experiment R2 — VaR Forecast Validation

**Question:** Do VaR forecasts produce exception behaviour consistent with the selected confidence level?

**Methods:** rolling historical VaR, exception rate, Kupiec POF, Christoffersen independence and conditional coverage where feasible.

**Outputs:** exception count, exception rate, p-values/statistics and interpretation.

### Experiment R3 — Portfolio Allocation

**Question:** Does dynamic long-only minimum-variance allocation improve risk-adjusted out-of-sample performance relative to equal weighting?

**Benchmark:** equal-weight portfolio.

**Outputs:** annualized return, volatility, Sharpe, Sortino, maximum drawdown, turnover, transaction-cost-adjusted equity curve.

### Experiment R4 — Volatility Regime Prediction

**Question:** Can observable market characteristics predict future volatility regimes?

**Candidates:** Logistic Regression, Random Forest.

**Benchmark:** persistence classifier.

**Outputs:** balanced accuracy, macro precision, macro recall, macro F1, confusion matrix and feature importance where applicable.

### Experiment R5 — Robustness

**Question:** Are principal findings stable under reasonable alternative assumptions?

**Perturbations:** confidence levels, estimation windows, model specification, bootstrap samples and stress scenarios.

**Outputs:** sensitivity tables, confidence intervals, stress losses and interpretation of stability.

## 5. Transaction Costs

Where strategies or dynamic portfolios trade, transaction costs must be explicitly parameterized and applied consistently. Gross and net results should be distinguishable.

The selected cost assumption must be documented and justified as a modelling assumption rather than presented as an observed market fact unless supported by data.

## 6. Randomness and Reproducibility

All stochastic simulations and bootstrap experiments use a documented fixed random seed by default. Final reports must state the seed and simulation/bootstrap count where applicable.

## 7. Statistical Reporting

Report point estimates together with relevant uncertainty or validation evidence. Avoid interpreting a small numerical difference as economically meaningful without considering sampling uncertainty, model risk and transaction costs.

## 8. Multiple Comparisons

Where many models, assets or specifications are evaluated, clearly distinguish exploratory analysis from primary confirmatory comparisons. The final report should avoid selecting the most favourable result merely because many alternatives were tested.

## 9. Final Test Lock

Once the candidate methodology and hyperparameters are frozen, run the final test exactly once for the principal result set. Any subsequent change that affects the model specification requires documenting whether the final test has been reopened and, if so, why.

## 10. Result Archive

For every final experiment, retain:

- experiment identifier
- code version/commit
- configuration
- data specification
- model parameters
- random seed
- sample sizes
- performance metrics
- statistical tests
- generated figures/tables
- interpretation

This creates an auditable chain from source code to capstone conclusion.
