# Design decisions

This is a retrospective record of the implemented choices and their documented
technical basis. It does not establish who first proposed every choice or that
the author personally reviewed every result. The project brief specified the JEPX
adaptation, chronological evaluation, naive comparisons and the battery extension;
implementation details were developed with AI assistance. No percentage of human
versus AI work is asserted.

各Reasonは既存文書で確認できる技術的理由です。本人が当時そう考えて選んだこととは区別します。
**TODO(author)の記述は、本人が本当にそう考えたか確認してください。**
Record corrections and confirmation dates in future commits; do not invent earlier decisions.

## Chronological split instead of random split

**Decision:** Use initial training through 2023-12-31, validation in 2024-01–03 and test in 2024-04–2025-03.

**Reason:** The methodology defines a forecast origin using earlier auction outcomes. Chronological partitions preserve that ordering; the original brief explicitly excluded random splitting.

**Trade-off:** One holdout year gives limited evidence across market regimes.

**Evidence:** [Methodology: predeclared experiment](METHODOLOGY.md#predeclared-experiment).

**TODO(author):** confirm the rationale for the exact dates; chronological ordering was required in the brief, but the dates are not attributed to an independent author choice.

## Naive baselines

**Decision:** Compare previous-day, previous-week and weekday-aware persistence. Stage 2 reuses the previous-day baseline.

**Reason:** The paper notes describe these reference methods; evaluation uses identical days and slots. The battery brief requested the strongest existing Stage 1 baseline.

**Trade-off:** Stage 2 selection reuses the Stage 1 test-MAE ranking, rather than a new untouched selection set.

**Evidence:** [Paper notes: baselines](PAPER_NOTES.md#baselines-and-metrics-sections-5255); [Battery comparison](BATTERY_OPTIMIZATION.md).

**TODO(author):** confirm your understanding of why all three baselines matter and the limitation of reusing the test ranking.

## LASSO / LEAR-style model

**Decision:** Fit 48 independent LASSO outputs on 247 price-history/calendar features, using training-only StandardScaler.

**Reason:** The project brief requested a simplified LEAR-style adaptation. Paper notes describe L1 regularization for a large lagged regressor set and distinguish this implementation from the benchmark.

**Trade-off:** No external forecasts, robust target transformation or DNN comparison; shared alpha simplifies slot-specific tuning.

**Evidence:** [Paper notes: LEAR and inputs](PAPER_NOTES.md#lear-lasso-and-inputs-sections-4142); [Methodology](METHODOLOGY.md#features-and-model).

**TODO(author):** confirm the rationale for the particular lag set, rolling summaries and scaling choices; these are recorded implementation choices, not claimed personal inventions.

## Validation-only alpha selection

**Decision:** Choose shared alpha from 0.03, 0.1, 0.3 and 1.0 using validation MAE; retain the selected 0.1 during test.

**Reason:** The pipeline limits selection to the pre-test prefix. This separates hyperparameter selection from final sequential evaluation.

**Trade-off:** The fixed grid and shared penalty are simpler than daily slot-specific selection; LASSO squared loss differs from selection MAE.

**Evidence:** [Methodology](METHODOLOGY.md#predeclared-experiment); [Validation scores](../results/validation_scores.csv).

**TODO(author):** confirm why this grid and primary metric were accepted; the recorded outcome is evidence of execution, not evidence of who proposed them.

## Expanding-window refitting

**Decision:** Refit scaler and coefficients daily using all earlier eligible targets; keep alpha fixed.

**Reason:** The methodology explicitly describes recalibration as earlier auction outcomes become available. It distinguishes this from forecasting an entire year at one fixed origin.

**Trade-off:** Expanding history retains old regimes; a rolling-window option exists but was not selected using test results.

**Evidence:** [Methodology](METHODOLOGY.md#predeclared-experiment); [Paper notes](PAPER_NOTES.md#calibration-and-evaluation-sections-42-44-5).

**TODO(author):** confirm the rationale for expanding history over a fixed-length window; no author-specific rationale is inferred from the default.

## Battery optimization as Stage 2

**Decision:** Feed frozen forecasts into a daily constrained plan, then value that plan at actual prices.

**Reason:** The author explicitly requested the forecasting → optimization → backtest extension and a comparison of accuracy with decision value.

**Trade-off:** This is a simplified daily decision problem with hypothetical equipment and incomplete execution costs.

**Evidence:** [Battery research question](BATTERY_OPTIMIZATION.md); [Executed results](BATTERY_RESULTS.md).

**TODO(author):** confirm your own interpretation of the 43 days with lower MAE but lower revenue; that conclusion was computed with AI assistance.

## MILP and binary operating state

**Decision:** Use SciPy/HiGHS MILP with binary charging mode, SOC dynamics, power bounds and identical daily initial/terminal energy.

**Reason:** The battery brief required preventing simultaneous charging and discharging. The formulation enforces it even for negative forecasts; SciPy was already a dependency.

**Trade-off:** Integer variables add solver work. Daily terminal equality limits interday opportunities while avoiding free depletion of initial energy.

**Evidence:** [Formulation and solver](BATTERY_OPTIMIZATION.md#solver--解法).

**TODO(author):** confirm the solver/constraint rationale; the brief permitted MILP, but selecting this implementation was AI-assisted.

## System-price proxy

**Decision:** Use the original JEPX system-price target in both stages, with hypothetical battery parameters and all fixed sensitivities reported.

**Reason:** The methodology identifies the existing target; the battery brief required keeping the forecasts/results unchanged and declaring a system-price proxy.

**Trade-off:** Area settlement, grid fees, imbalance, acceptance, transmission and capital costs are missing, so proxy cashflow cannot establish commercial profitability.

**Evidence:** [Methodology: data contract](METHODOLOGY.md#data-contract); [Battery limitations](BATTERY_RESULTS.md).

**TODO(author):** confirm the economic interpretation and which missing assumption you would investigate next; no personal priority is invented.

