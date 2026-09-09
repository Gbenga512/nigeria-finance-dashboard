# MScFE Capstone Reproducibility Standard

## Objective

A reader should be able to understand how the reported results were produced and reproduce the principal experiments from the repository without relying on undocumented manual steps.

## Required Record for Each Final Result

1. Experiment ID.
2. Git commit SHA.
3. Data source and retrieval date.
4. Asset universe.
5. Observation period.
6. Frequency.
7. Return definition.
8. Training/validation/test boundaries.
9. Model specification.
10. Hyperparameters.
11. Random seed where applicable.
12. Transaction-cost assumption where applicable.
13. Evaluation metrics.
14. Statistical tests.
15. Output tables/figures.
16. Short financial interpretation.

## Reproducibility Rules

- Preserve chronological ordering for financial time series.
- Do not use the final test set for model selection.
- Document every material preprocessing rule.
- Fix random seeds for stochastic experiments.
- Keep analytical functions covered by automated tests where practical.
- Keep the CI test suite passing before treating an implementation as stable.
- Distinguish exploratory findings from primary final findings.
- Never manually alter a reported result without retaining the underlying generated output.

## Research-to-Software Traceability

Every major capstone claim should map to:

**Claim → Experiment ID → Code module → Configuration → Dataset → Result → Interpretation**

This traceability is required for the final paper and recorded presentation.

## Defence Preparation

For each final experiment, the defence notes should answer:

- What question does this experiment answer?
- Why was this method selected?
- What assumptions does it make?
- How was look-ahead bias controlled?
- How was data leakage controlled?
- What benchmark was used?
- What was the out-of-sample result?
- Is the result economically meaningful?
- Is it statistically supported?
- Is it robust to reasonable alternatives?
- What are the limitations?

## Version Control

The final report should identify the Git commit associated with the final analytical results. If the application continues to evolve after the research results are frozen, production/UI changes must be distinguished from changes that alter the empirical methodology.
