# JEPX price forecasting and battery scheduling

[日本語](README.ja.md) · [Technical documentation](docs/README.md) · [Design decisions](docs/DESIGN_DECISIONS.md)

## Project overview

A Python study connecting electricity price forecasting to constrained battery
scheduling. Stage 1 adapts the LEAR-style LASSO approach discussed by
[Lago et al. (2021)](https://doi.org/10.1016/j.apenergy.2021.116983) to JEPX half-hourly
system prices. Stage 2 uses those frozen forecasts to choose charge/discharge
schedules, then evaluates them at actual prices.

The dataset covers fiscal years 2022–2024. Both stages use the same 365-day test
period, **2024-04-01–2025-03-31**. This is a simplified adaptation of the paper.

## Research question

1. Can price-history-based LASSO improve next-day forecasts over simple persistence baselines?
2. Does that improvement translate into higher battery cashflow under the same physical constraints?

## Main results

Stage 1 evaluates 17,520 half-hour observations. Units are JPY/kWh.

| Model | MAE | RMSE |
|---|---:|---:|
| Previous-day naive | 1.8547 | 2.9903 |
| Previous-week naive | 2.6453 | 3.9525 |
| Weekday-aware naive | 1.8981 | 2.9987 |
| LEAR-style LASSO | **1.5581** | **2.2918** |

LASSO reduced MAE by **16.00%** against the strongest naive baseline, but lost to
it on **156 of 365 days**. Its 54 predictions below 0.01 JPY/kWh were retained
without clipping. [Full results and failure cases](docs/RESULTS.md) ·
[Metrics CSV](results/metrics.csv).

## Method

- **Data:** official JEPX system prices; 1,096 days and 52,608 observations.
- **Features:** 247 columns combining lagged daily price curves, seven-day
  per-slot statistics and weekday indicators.
- **Model:** 48 independent LASSO outputs with training-only standardization.
- **Evaluation:** chronological train/validation/test split; validation-only
  selection of alpha = 0.1; daily expanding-window refits with alpha fixed in test.
- **Checks:** future-price mutation tests, aligned observations and strict data
  validation. **52 tests passed** locally and on GitHub Actions, Python 3.11/3.12.

The earlier delivery day's auction curve is assumed available at forecast time.
See [methodology and leakage safeguards](docs/METHODOLOGY.md),
[paper-to-implementation differences](docs/PAPER_NOTES.md), and
[design decisions](docs/DESIGN_DECISIONS.md).

## Stage 2: Battery optimization

A SciPy/HiGHS MILP turns forecast prices into a daily schedule. The hypothetical
battery has **1 MWh** capacity, **0.5 MW** charge/discharge limits, 10–90% SOC,
50% initial and terminal SOC, and 95% efficiency each way (90.25% round trip).
Binary operating states prevent simultaneous charging and discharging.

Operational plans are frozen before actual-price evaluation. A separate
**Perfect-foresight upper bound** uses future prices as an infeasible benchmark.
Base-case annual proxy cashflows, with zero degradation cost:

| Strategy | JPY | Negative days |
|---|---:|---:|
| No-operation | 0 | 0 |
| Previous-day naive forecast | 2,233,270 | 8 |
| LEAR forecast | **2,532,089** | 2 |
| Perfect-foresight upper bound | 2,899,726 | 0 |

LEAR improved the annual proxy cashflow by **298,819 JPY (+13.38%)**, but
underperformed Naive on **112 days**. All six fixed sensitivity cases are reported:
base, round-trip efficiencies 80/90/95%, and throughput costs 1/3 JPY/kWh.

[Formulation and reproduction](docs/BATTERY_OPTIMIZATION.md) ·
[Results, downside and all sensitivity cases](docs/BATTERY_RESULTS.md).

## Key findings

- Previous-day persistence was the strongest simple baseline; LASSO's annual
  advantage did not mean winning every day.
- On **43 days**, LEAR had lower MAE but lower battery revenue than Naive.
  **Lower forecast error does not automatically imply higher operational value.**
- The mutation tests check two information boundaries: future targets cannot
  affect an earlier forecast, and actual settlement prices cannot change a frozen plan.
- System-price cashflows alone are insufficient to assess an operating battery.

## Limitations

One market and one test year support a descriptive comparison, not a general
performance or significance claim. External forecasts, holiday features and
publication-time data snapshots are absent. The battery comparison reuses the
Stage 1 test-MAE baseline ranking and fixes daily terminal SOC.

Battery values are **hypothetical system-price proxies**, not commercial profit.
Actual settlement may use area prices. Grid fees, imbalance costs, market impact,
bid acceptance, transmission constraints, capex and fixed operating costs are
omitted; degradation is a simplified throughput charge. Perfect foresight is
unavailable in practice. [Remaining work](docs/FUTURE_WORK.md).

## Reproduction

Python 3.11+. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
# Obtain official CSVs first; see data/README.md.
python scripts/download_or_prepare_data.py --download-years 2022 2023 2024
python scripts/run_experiment.py --output results/stage1_reproduction
python scripts/run_battery_backtest.py --predictions results/stage1_reproduction/predictions_full.csv
```

On Windows activate with `.venv\Scripts\Activate.ps1`. Use the
[data instructions](data/README.md) for manual downloads. The separate Stage 1
output directory preserves published evidence. Raw data, full predictions and
full schedules stay Git-ignored. Recorded versions are in `requirements-lock.txt`;
[reproduction details](docs/BATTERY_OPTIMIZATION.md#reproduction--再現) cover input
checks and platform differences.

## Repository structure

```text
src/jepx_forecasting/  forecasting, battery model, MILP and backtest
scripts/              data preparation and experiment entry points
configs/              fixed battery experiment design
tests/               synthetic checks for both stages
docs/                methodology, results and design decisions
results/              Stage 1 evidence and battery/ outputs
```

## Project ownership

The author set the project brief: apply the cited electricity-price literature to
JEPX, compare against naive forecasts using chronological evaluation, and extend
the study to forecast-driven battery decisions. The author also required that
unfavorable results and the original experiments be preserved.

[Design decisions](docs/DESIGN_DECISIONS.md) distinguishes these instructions from
implementation choices and rationales still awaiting the author's confirmation.
[Development workflow](docs/DEVELOPMENT.md) describes how future decisions will be recorded.

## AI-assisted development

Codex supported literature interpretation, implementation, code review, test
development, result analysis and documentation editing. Suggestions were checked
where applicable against referenced literature, source data, code execution and
tests; the corresponding evidence is linked in the technical documents.

The author directs project scope and is responsible for reviewing the work.
This disclosure does not attribute every implementation choice or interpretation
to the author; personal review and rationale should be confirmed in the decision record.

Original code and documentation: [MIT](LICENSE). JEPX data and the cited paper
retain their own rights. [Data-use and provenance review](docs/RELEASE_REVIEW.md).
