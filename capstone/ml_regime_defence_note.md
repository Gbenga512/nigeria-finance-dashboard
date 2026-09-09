# ML Volatility-Regime Experiment — Defence Note

## What problem does this experiment address?

The experiment examines whether observable market characteristics contain information about future volatility regimes. It does not claim that future prices can be predicted reliably.

## Why classify volatility regimes?

Risk conditions can change over time. A model that identifies whether the future environment is relatively low, normal or high volatility can potentially provide useful context for risk management and portfolio decisions.

## Why these features?

The feature set contains recent return, short- and medium-horizon momentum, rolling volatility and trend relative to a moving average. These variables represent recent price movement, directional persistence and current risk intensity.

## Why Logistic Regression?

Logistic Regression provides a transparent statistical classification benchmark and gives a relatively simple relationship between standardized features and class probabilities.

## Why Random Forest?

Random Forest can capture nonlinear interactions between financial features without requiring a linear decision boundary. Its constrained depth and minimum leaf size reduce unnecessary model complexity.

## Why a persistence benchmark?

A learned model should beat a simple alternative to justify its additional complexity. The persistence benchmark classifies the future regime using the current volatility state and thresholds estimated from training data.

## How is the future target constructed?

At time t, the target represents realized volatility over the following horizon. Future observations are therefore used only to create the target and are not available to the predictor at time t.

## How is data leakage controlled?

The regime thresholds are estimated from training targets only. Features use information available through the prediction date. Model selection occurs on a chronological validation sample, while the final test sample remains untouched until the model specification is locked.

## Why chronological validation instead of random cross-validation?

Financial observations are temporally dependent and future information must not influence earlier decisions. Chronological splitting better represents the information set available to a real-time decision-maker.

## How is the final model selected?

Candidate models are fitted on the training sample and evaluated on the validation sample. The candidate with the highest validation balanced accuracy is selected, with macro F1 and accuracy used as deterministic tie-breakers. The selected specification is then refitted using training plus validation observations and evaluated once on the final test period.

## Why balanced accuracy?

Volatility regimes may not occur equally often. Balanced accuracy gives each class equal importance through the average of class-specific recall, reducing the risk that a dominant class masks poor performance in less frequent regimes.

## What would constitute a useful result?

A useful result requires more than a model having a high accuracy number. We should compare it with the persistence benchmark, examine class-level performance, inspect the confusion matrix and consider whether the improvement is economically meaningful and stable.

## What if the ML model performs poorly?

That is a valid research finding. It would indicate that the selected features and models do not provide sufficient predictive information for the tested regime definition and sample. The result should be reported rather than hidden.

## Important defence statement

**The ML component is evaluated as a predictive classification experiment, not as evidence that financial markets are fully predictable.** Its purpose is to test whether regime information can be extracted from observable market characteristics under a strict out-of-sample design.
