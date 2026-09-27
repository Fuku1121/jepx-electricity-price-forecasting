# Paper notes — literature to an independent implementation

Prepared before implementation, 2026-09-27. These are AI-assisted reading notes;
the portfolio owner should verify and explain them independently.

Lago, J., Marcjasz, G., De Schutter, B., & Weron, R. (2021).
*Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms,
best practices and an open-access benchmark*. Applied Energy, 293, 116983.
[DOI](https://doi.org/10.1016/j.apenergy.2021.116983) ·
[Author-hosted published paper](https://jesuslago.com/wp-content/uploads/1-s2.0-S0306261921004529-main-1.pdf) ·
[Preprint](https://arxiv.org/abs/2008.08004).
The published PDF is CC BY 4.0; these notes paraphrase it and do not reproduce its tables.
Section references below refer to the published article, not the preprint.
No epftoolbox source or other forecasting repository was consulted to implement this project.

## Problem and market timing (Sections 1–3)

**Paper:** Much forecasting literature compares models on incompatible datasets,
short test periods, weak baselines, or unclear evaluation procedures. The contribution
combines a review, five multi-year benchmark markets, LEAR/DNN reference models,
and recommendations for reproducible comparisons. Day-ahead prediction produces
the whole delivery-day price vector before the auction closes on the preceding day.
Intraday seasonality, weekly cycles, spikes, near-zero/negative prices in some
markets, and changing generation conditions make generic time-series recipes unsafe.

**This implementation:** Predict 48 half-hourly JEPX system prices for delivery day
d before its auction on d−1. JEPX is a different market; do not transfer European
market facts (such as negative prices) without checking its rules. Historical spot
prices for delivery d−1 were determined on d−2, so the complete d−1 auction curve
can be used even before delivery d−1 has finished. This assumes timely availability
of auction results; historical CSVs do not prove their original publication timestamps.

## LEAR, LASSO, and inputs (Sections 4.1–4.2)

**Paper:** LEAR means Lasso Estimated AutoRegressive. It is a parameter-rich
autoregression with exogenous variables, estimated using L1 regularization.
For each of 24 hours, the input set contains all hourly prices from d−1, d−2,
d−3 and d−7; two external forecast curves for d, d−1 and d−7; and seven weekday
indicators (247 candidate regressors). External forecasts for d must be available
on d−1. Sparse estimation can discard unhelpful regressors while shrinking others.

**This implementation:** Fit 48 independent LASSO regressions, one per slot, with
the full 48-price curves from d−1, d−2 and d−7, seven-day lagged per-slot means
and standard deviations, and seven weekday indicators. Same-slot lags are included
within these curves. Slot identity is represented by choosing a separate model;
a constant hour/slot column adds no information within one model. A weekend dummy
is redundant with Saturday/Sunday indicators and is omitted. No external forecasts
or d−3 curve initially. This is LEAR-style, not a reproduction of the benchmark.

For each slot s, our scikit-learn objective is

`min(b,w) (1/(2n)) * sum_d (y[d,s] − b − X[d]w)^2 + alpha * sum_j |w[j]|`.

The intercept is unpenalized. The article writes `RSS + lambda * ||w||_1`;
for otherwise identical data and conventions, `lambda = 2*n*alpha`.
Numerical regularization parameters are not portable across scales or conventions.
L1 penalization yields exact zero coefficients, but correlated regressors make
selection unstable: nonzero coefficients are not causal evidence.

## Scaling and regularization (Sections 4.2–4.2.2)

**Paper:** Prices undergo an inverse hyperbolic sine transformation after robust
centering/scaling using in-sample median and adjusted median absolute deviation.
Daily LARS with AIC chooses the penalty, followed by coordinate-descent LASSO.

**This implementation:** StandardScaler on X using training data only; y remains
in yen/kWh and there is no asinh transformation. This deliberately simple variant
is more exposed to spikes. Scaling prevents column magnitude alone from determining
the L1 penalty. Choose a single shared alpha from a fixed grid using a later
validation period's MAE, with daily recalibration during validation. Freeze alpha
before test. Do not use shuffled K-fold or default LassoCV splitting.

## Calibration and evaluation (Sections 4.2, 4.4, 5)

**Paper:** LEAR is recalibrated daily on 8-week, 12-week, 3-year and 4-year windows;
their predictions also form an ensemble. Benchmark test periods span two years;
the guidelines recommend at least a year and multiple markets. Strong benchmarks,
statistical comparison (DM/GW), and disclosed splits are central to the argument.

**This implementation:** One expanding training history, recalibrated daily.
Validation follows initial training; test follows validation. An earlier test day's
auction outcomes may enter later fits, but no current/future target day can enter
its own fit. This is sequential out-of-sample evaluation, not a single fixed-origin
forecast of an entire year. A rolling-window option restricts each fit to the most
recent specified number of eligible days. Fixed windows and ensembles are future work.
Prefer a full-year test; publish exact dates and disclose if data access prevents it.
No significance claim without an appropriate dependence-aware analysis.

## Baselines and metrics (Sections 5.2–5.5)

**Paper:** Natural naive predictions copy d−1 or d−7; a weekday-aware alternative
copies d−1 on Tuesday–Friday and d−7 on Saturday–Monday. rMAE is normalized by
the weekly naive MAE on the *same out-of-sample observations*.

**This implementation:** Include all three baselines on identical target days/slots.
Report MAE as primary, RMSE as a spike-sensitive secondary metric, and weekly rMAE.

`MAE = mean(|y − prediction|)`; `RMSE = sqrt(mean((y − prediction)^2))`;
`rMAE = MAE(model) / MAE(weekly naive)`.

MAE and RMSE have yen/kWh units; rMAE is dimensionless. A zero denominator makes
rMAE undefined and must be recorded as missing, not infinity. RMSE weights large
errors more strongly and is not a profit measure. MAPE can be dominated by prices
near zero; it is omitted. Lower error alone does not demonstrate tradable profits.

## Leakage safeguards and departures

**Paper:** Reproducible ex-ante forecasting requires correctly timed predictors,
calibration, validation and transparent out-of-sample comparisons.

**This implementation:** Calendar days are contiguous and complete (48 slots).
Reject duplicates, missing dates, missing/nonfinite prices; do not interpolate with
future values. Shift full daily curves *before* computing rolling statistics.
Fit scalers separately on each training prefix. Test-time tuning is forbidden.
Tests perturb prices on/after an origin and require identical earlier features and
predictions at that origin. Also test feature generation with a missing target-day
placeholder, to ensure a prediction does not require its own actual prices.

The major departures are Japan/30-minute system prices, fewer price lags, no demand
or renewable forecasts, ordinary scaling, shared validation-selected alpha, one
expanding calibration history, no DNN/ensemble, and descriptive rather than DM/GW
inference. None should be presented as matching the paper's reported accuracy.
