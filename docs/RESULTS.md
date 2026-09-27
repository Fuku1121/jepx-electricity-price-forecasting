# Executed results

Run recorded in [run_metadata.json](../results/run_metadata.json), using official
JEPX fiscal 2022–2024 CSVs acquired on 2026-09-27. Source: [JEPX](https://www.jepx.jp/electricpower/market-data/spot/).
Original data rights remain with JEPX; this report and the figures identify that source.
No synthetic fixture contributes to the figures or scores below.

## Actual experiment

- Data: 2022-04-01–2025-03-31; 1096 complete days / 52608 slots.
- Initial usable training: 2022-04-08–2023-12-31 (633 days).
- Validation: 2024-01-01–2024-03-31 (91 days).
- Test: 2024-04-01–2025-03-31 (365 days / 17520 slots).
- Daily expanding recalibration, 247 inputs, 48 independent outputs, selected alpha=0.1.
- Runtime for ingestion, selection and test fitting: 429.4 seconds on this machine (not a hardware benchmark).
- Package versions and source/raw hashes: metadata; retrieval details: acquisition.json.

| Model | MAE (JPY/kWh) | RMSE (JPY/kWh) | rMAE (weekly) |
|---|---:|---:|---:|
| naive_previous_day | 1.8547 | 2.9903 | 0.7011 |
| naive_week | 2.6453 | 3.9525 | 1.0000 |
| naive_weekday | 1.8981 | 2.9987 | 0.7175 |
| lear_lasso | 1.5581 | 2.2918 | 0.5890 |

## Difference from every baseline

Negative delta means LASSO has lower MAE. Positive reduction means improvement.

| Baseline | LASSO MAE minus baseline (JPY/kWh) | Relative MAE reduction |
|---|---:|---:|
| naive_previous_day | -0.2967 | +16.00% |
| naive_week | -1.0873 | +41.10% |
| naive_weekday | -0.3400 | +17.91% |

The LEAR-style model changes MAE by -0.2967 JPY/kWh versus the strongest tested naive baseline (`naive_previous_day`), a 16.00% reduction. All baselines are reported; no losing comparison is hidden.
These differences do not have a confidence interval or significance test.

## Validation choice

- alpha=0.1: validation MAE=1.575341 JPY/kWh.
- alpha=0.3: validation MAE=1.579894 JPY/kWh.
- alpha=0.03: validation MAE=1.598123 JPY/kWh.
- alpha=1: validation MAE=1.768089 JPY/kWh.

No test outcome was used to choose the candidate grid or alpha. Fixed alpha is a
simplification: the paper recalibrates its regularization parameter daily.

## How to verify

1. Obtain official files and compare SHA-256 values with run_metadata.json.
2. Reproduce with the recorded dependency versions and default command.
3. Compute errors from local predictions_full.csv and compare metrics.csv.
4. Mean daily MAE should match each full-period MAE, because all days have 48 slots.
5. Every row of fit_audit.csv must have train_end < date and fixed selected alpha.
6. The committed predictions_sample.csv is exactly the first seven test days;
   annual performance cannot be checked using this short sample alone.

## Figures and interpretation

- actual_vs_predicted.png: the first seven test days, selected chronologically.
- model_mae.png: equal observations and identical test dates for all models.
- slot_errors.png: per-slot mean absolute errors, with LASSO 10th–90th percentiles.
  The band describes variation across days; it is not a confidence band for the mean.

MAE/RMSE are in JPY/kWh, rMAE is dimensionless. Test-period spikes are neither removed
nor clipped. Predictions are unconstrained linear estimates and can fall below the
market's feasible floor; no post-hoc clipping was applied. This limitation should be
considered before turning forecasts into operational decisions.

## What is and is not supported

Supported: these implemented models yielded the recorded point errors on this
specific historical year under the stated timing assumptions. The unit tests check
code-level information boundaries and exact alignment.

Not supported: full reproduction of the paper, state-of-the-art status, superiority
across years/markets, significant gains, executable trading profit, or evidence that
the current CSV version was available at each original forecast origin. The strongest
next step is correctly timestamped exogenous forecasts and untouched additional years.

## Failure cases worth discussing

Unconstrained LASSO produced **54 forecasts below 0.01 JPY/kWh**,
with a minimum of **-2.0382 JPY/kWh**. These outputs were kept in all
metrics and not clipped after looking at test outcomes. A market-aware output
constraint is a candidate for a separately validated experiment.

LASSO had higher daily MAE than the previous-day baseline on **156 of 365 days**.
The aggregate improvement therefore does not mean it won every day. Its largest
daily MAE was **5.2845 JPY/kWh on 2025-03-03**.
The cause of that day’s errors has not been established; do not infer weather or
supply events from the error alone. These statements are computed from full local
predictions and committed daily_mae.csv.
