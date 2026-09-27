# Methodology and reproducibility contract

## Forecast event, units and information set

Let p[d,s] denote the **day-ahead auction** system price for delivery date d and
half-hour slot s=1,...,48, in JPY/kWh. Dates refer to Japan Standard Time
(Asia/Tokyo). Slot 1 is 00:00–00:30; slot 48 is 23:30–24:00.
This is not the intraday market, realized demand, or an imbalance settlement price.

The conceptual forecast is issued on d−1 before the auction for d.
The [JEPX market overview](https://www.jepx.jp/electricpower/outline/) explains
next-day trading and 48 products. The official
[trading change notice](https://www.jepx.jp/company/news/pdf/jepx20151216.pdf)
states a 10:00 preceding-day bid deadline; operational deployment must recheck
current rules. We do not infer a publication timestamp from a delivery timestamp.

The d−1 price curve was auctioned on d−2. Consequently even late d−1 slots can be
used at the d−1 morning forecast origin, provided that auction results were already
available. The CSV archive does not preserve original publication/revision times;
this is an explicit as-of availability assumption, not experimentally verified latency.

## Data contract

Only the system-price column is selected, by its Japanese name, never column position.
Read UTF-8 (with optional BOM) or CP932, normalize fullwidth parentheses, parse dates
and numeric prices. Reject duplicate delivery-date/slot pairs (even across files),
missing dates, incomplete days, invalid slots and missing/infinite prices.
All calendar days are retained; there is no outlier deletion, forward/back filling,
interpolation, holiday deletion, clipping, or full-sample normalization.
Data loading and validation are in `data.py`; downloading is an optional script.
The processed matrix has dates as rows and slots 1..48 as columns.

## Features and model

One day is one feature row. Each of the 48 target regressions receives 247 columns:

| Block | Columns | Latest delivery day used |
|---|---:|---|
| Full previous-day curve | 48 | d−1 |
| Full two-day lag curve | 48 | d−2 |
| Full weekly lag curve | 48 | d−7 |
| Per-slot mean over d−7,...,d−1 | 48 | d−1 |
| Per-slot standard deviation over d−7,...,d−1 (ddof=0) | 48 | d−1 |
| Seven weekday indicators for d | 7 | Known calendar |

The first seven days are warm-up and cannot be target training rows. With a separate
model per slot, an hour/slot indicator is constant within each regression. Weekend
is already encoded by two weekday columns. No holiday or weather variables are used.
Rolling statistics refer to the same slot across seven days, not a moving window
of 336 adjacent half-hour prices. Extra summaries are correlated with price lags;
LASSO selects among them, but selection should not be interpreted causally.

Each fit uses `Pipeline(StandardScaler(), Lasso(...))` with an intercept and
untransformed targets. StandardScaler learns means/standard deviations on the
eligible training rows only. Each fit starts fresh; there is no test-fitted scaler.
The LASSO squared-loss objective differs from the MAE used for model selection.
MAE-oriented quantile regression is a possible later extension.

Multi-output `Lasso` is used for computational convenience: its elementwise L1
objective separates over the 48 outputs. It is **not** `MultiTaskLasso`, which
couples the outputs. A unit test compares one output to a single-target Lasso.
Penalty alpha is shared by slots, while coefficients and intercepts differ.
See [scikit-learn Lasso](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Lasso.html)
and [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).

## Predeclared experiment

These dates/grid were chosen before viewing the test metrics. The initial experiment
uses fiscal years 2022–2024, representing 2022-04-01 through 2025-03-31.

| Role | Delivery dates | Use |
|---|---|---|
| Lag warm-up | 2022-04-01–2022-04-07 | Construct first feature rows |
| Initial training | 2022-04-08–2023-12-31 | Estimate first validation fit |
| Validation | 2024-01-01–2024-03-31 | Choose alpha by pooled MAE |
| Test | 2024-04-01–2025-03-31 | Final sequential comparison |

Alpha grid: `{0.03, 0.1, 0.3, 1.0}`. Each candidate is evaluated by daily refitting
on all earlier eligible rows throughout validation. The validation MAE averages all
48 slots and all validation days equally. Lowest MAE wins; an exact tie selects
smaller alpha. The pipeline passes only the pre-test prefix to alpha selection.
All candidate scores are saved. This is a chronological holdout, not shuffled CV.

After selection, alpha remains fixed throughout test. For each day d, train on
eligible target dates strictly before d, then predict all 48 prices together.
Earlier test targets may enter subsequent fits because they become known auction
outcomes. This does not make the evaluation a fixed-origin multi-day forecast.
Scaler, intercept and coefficients are recalibrated every day. The default is an
expanding history; `--window-days N` keeps only target rows in [d−N,d−1].
Window choice is not optimized using test data.

The LASSO maximum is 30,000 coordinate-descent iterations with tolerance 1e−4;
non-convergence raises an error. Training-date ranges and iterations are logged in
`fit_audit.csv`. The algorithm is deterministic cyclic coordinate descent; no random
seed or randomized split is used in the real experiment.

## Baselines and scoring

1. Previous day: prediction[d,s] = p[d−1,s].
2. Weekly: prediction[d,s] = p[d−7,s].
3. Weekday-aware: previous day for Tuesday–Friday; weekly for Saturday–Monday.

All four models are scored on exactly the same observations. MAE is primary;
RMSE emphasizes large errors; rMAE divides by the weekly baseline's **test** MAE.
If that denominator is zero, CSV contains a missing value. No MAPE is used.
Date/column alignment and finite values are mandatory. Equal slot weights do not
represent any particular retailer's load profile or battery exposure.

Daily losses permit time-dependent error inspection, but no DM/GW test, confidence
interval or statistical significance claim is included. A descriptive improvement
is not proof of superiority in future regimes or profitable trading.

## Audit artifacts

`run_metadata.json` records dates, grid, selected alpha, versions, runtime, source
code hashes and raw CSV hashes. `validation_scores.csv`, `fit_audit.csv`,
`metrics.csv`, `daily_mae.csv` and `slot_errors.csv` preserve numerical evidence.
`predictions_full.csv` is local and Git-ignored; `predictions_sample.csv` contains
the first seven test days. The sample cannot reproduce full-period scores by itself.
Recreate full predictions from the official files whose SHA-256 values are recorded.
The first-week plot is fixed by chronology, not chosen after looking at performance.

Raw archives can be revised by the publisher. Equal filenames do not imply equal
bytes; use hashes when comparing runs. Package ranges support normal installation;
`requirements-lock.txt` records the environment actually used. Cross-platform
floating-point results can vary slightly.

Source metadata keeps both original working-file SHA-256 values and LF-normalized
source SHA-256 values, since Git can normalize Windows line endings. This does
not change the computation; raw data hashes are always hashes of original bytes.
