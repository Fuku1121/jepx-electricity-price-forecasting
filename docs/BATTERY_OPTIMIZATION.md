# Battery optimization / 蓄電池運用の数理最適化

## Research question / 研究の問い

Under identical hypothetical battery constraints, does a frozen LEAR-style LASSO
price forecast deliver higher realized proxy revenue than the strongest existing
naive forecast? 予測の誤差だけでなく、その予測から作る意思決定の価値を評価します。
Stage 1のモデル、split、alpha、予測値、既存結果は変更しません。

## Prediction → Decision → Evaluation

1. **Prediction:** reuse the existing 365 × 48 out-of-sample predictions for
   2024-04-01 through 2025-03-31. The original daily expanding fit uses only earlier
   delivery dates; d−1 auction curves are assumed known at the decision deadline.
2. **Decision:** `freeze_forecast_schedules()` receives only forecast panels and
   `BatteryConfig`. `optimize_battery_schedule(forecast_prices, config)` has no
   actual-price argument. Both operational strategies' plans are frozen as tuples
   before settlement. No ex-post redispatch, clipping or actual-based abstention.
3. **Evaluation:** `evaluate_schedule(schedule, actual_prices)` values those fixed
   volumes at actual prices. It cannot optimize them. Only the separately named
   `perfect_foresight_optimizer(actual_prices, config)` sees future prices in its
   objective, for the explicitly infeasible benchmark.

Input integrity checks compare cached predictions to published Stage 1 aggregate
and daily MAE, RMSE and first-week sample; this gate reads actuals to detect file
mismatch, never to select a battery parameter or modify an operational decision.
These are retrospectively computed out-of-sample forecasts, not evidence of a
historical live forecasting service or publication-time data snapshots.

## Hypothetical research battery / 仮想研究設定

| Parameter | Base case |
|---|---:|
| Nameplate energy capacity | 1.0 MWh |
| Charge / discharge maximum, grid side | 0.5 / 0.5 MW |
| SOC minimum / maximum | 10% / 90% = 0.1 / 0.9 MWh |
| Initial and terminal energy each day | 50% = 0.5 MWh |
| Charge / discharge efficiency | 0.95 / 0.95 |
| Round-trip efficiency | 0.95 × 0.95 = **90.25%** |
| Interval | 0.5 hour |
| Throughput cost | 0 JPY/kWh in base case |

The 1 MWh / 0.5 MW scale makes units transparent (two-hour nameplate duration);
10–90% reserves avoid assuming all nameplate energy is usable; 50% is a symmetric
initial state; 95% each direction illustrates conversion losses. These are the
user-proposed pedagogical assumptions, **not** a specification, fitted equipment
model, empirically estimated costs or recommended investment. Usable SOC range
is 0.8 MWh, so 1 MWh nameplate does not mean 1 MWh available for every cycle.

All methods share the same constraints. Terminal equality physically links the
end of each day to the next day's initial state without a free SOC reset. It also
restricts interday arbitrage and makes this a sequence of daily problems, not an
unrestricted full-year optimum. There is no cycle-count or ramp-rate constraint.

## Objective / 目的関数

For t = 0,...,47, c_t and q_t are grid-side charging and discharging power (MW),
e_t is internal stored energy (MWh); forecast price is in JPY/kWh. Let δ = 0.5 h,
k = 1000 kWh/MWh, and λ be cost per grid-side charged **plus discharged** kWh.

$$\max_{c,q,e,u}\; k\delta\sum_{t=0}^{47}
\left[\hat p_t(q_t-c_t)-\lambda(c_t+q_t)\right].$$

The base case has λ = 0. Sensitivity costs enter the objective **before** the
schedule is chosen, and the same cost is deducted in settlement. They are not
post-hoc deductions from an unchanged base schedule. This symmetric throughput
definition charges both sides; it is not a cost per discharged kWh or per cycle.

## SOC dynamics and constraints / SOC・出力制約

$$e_{t+1}=e_t+\eta_c c_t\delta-q_t\delta/\eta_d,$$
$$E_{\min}\leq e_t\leq E_{\max}\quad(t=0,...,48),$$
$$0\leq c_t\leq u_tP_c,\qquad 0\leq q_t\leq(1-u_t)P_d,$$
$$u_t\in\{0,1\},\qquad e_0=e_{48}=E_{\mathrm{initial}}.$$

u_t=1 permits charging; u_t=0 permits discharging; either permits idling.
初期蓄電エネルギーを使い切って見かけの収益を増やさないよう、日末SOCを固定します。
Binary constraints rule out simultaneous charge/discharge even with negative
forecast prices. An LP relaxation alone does not guarantee this property.

## Solver / 解法

193 variables (48 charge, 48 discharge, 49 energy, 48 binary mode), 144 linear rows
plus bounds. SciPy's [milp API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
wraps HiGHS; minimize the negative JPY objective. SciPy was already present as a
scikit-learn dependency and is now explicit (`scipy>=1.11,<2`); the existing lock
already pins the executed version. No commercial solver or extra modeling package.

A 60-second per-day limit and relative MIP gap 1e−9 are fixed. Any nonoptimal status,
missing/nonfinite solution or constraint failure raises an exception; there is no
silent fallback to idle or best incumbent. Plans are checked to 1e−6 MW/MWh
feasibility tolerance. Multiple optimal schedules may differ by solver version;
compare objectives and constraints rather than promising universal bit equality.

## Realized revenue / 実価格による評価

$$R_{\mathrm{market}}=1000\delta\sum_t p_t^{\mathrm{actual}}(q_t-c_t),$$
$$C_{\mathrm{throughput}}=1000\delta\lambda\sum_t(c_t+q_t),\qquad
R_{\mathrm{net}}=R_{\mathrm{market}}-C_{\mathrm{throughput}}.$$

MW × h = MWh; multiply by 1000 to get kWh before multiplying by JPY/kWh.
For 0.5 MW charged over half an hour at 10 JPY/kWh then discharged at 50 JPY/kWh,
with unit efficiencies, cashflow is (50−10) × 0.5 × 0.5 × 1000 = 10,000 JPY.
No-operation has zero cashflow, throughput and operating intervals.

## Frozen comparison / 比較設計

- No-operation: always idle.
- Naive forecast: `naive_previous_day`, the best existing Stage 1 **test MAE**
  baseline, selected at the user's request before battery revenues were computed.
  This is an acknowledged reuse of the earlier test ranking, not fresh policy
  selection on an untouched dataset or a battery-return optimization.
- LEAR forecast: existing `lear_lasso`; no retraining or retuning in Stage 2.
- **Perfect-foresight upper bound**: same daily constraints, actual prices in the
  objective; not deployable. This bounds this simplified daily problem, not every
  possible battery business or an interday optimization.

[Design file](../configs/battery_experiment.json) was written before the first
battery backtest. Its base and all five one-factor sensitivities are reported:
round-trip efficiency 80%, 90%, 95%, using sqrt(RTE) in each direction; throughput
cost 1 and 3 JPY/kWh with base efficiencies. Other settings remain fixed. No
winning scenario is selected; the predeclared base remains the headline case.
Sensitivity evaluation on this same test year is descriptive, not validation for
choosing hardware or policy. Do not tune future designs against these results.

## Reproduction / 再現

From the repository root, after the README installation steps:

```bash
# Reuse a local full prediction file, if available:
python scripts/run_battery_backtest.py --predictions results/predictions_full.csv
```

The full Stage 1 forecast file is intentionally ignored because it contains a
full JEPX-derived series. In a new clone, obtain official CSVs per
[data instructions](../data/README.md) and regenerate Stage 1 into a separate directory:

```bash
python scripts/run_experiment.py --output results/stage1_reproduction
python scripts/run_battery_backtest.py --predictions results/stage1_reproduction/predictions_full.csv
python -m pytest -q
```

Do not overwrite the published Stage 1 evidence when regenerating forecasts.
The integrity gate uses the published `results` metrics/sample and rejects a
changed period or mismatching forecasts. Use matching data hashes/dependencies;
archive revisions or solver versions can affect reproducibility. No cloud
credentials are needed for computation. On the recorded machine all six battery
cases take about two minutes; runtime depends on the machine.

Public output: metrics, daily and monthly revenues, all sensitivity summaries,
first **seven chronological days** of schedules, configuration, run metadata,
and five figures. The full 70,080-row base schedule is local and Git-ignored.
The sample is not selected by performance and cannot reproduce annual cashflows
on its own. The runner checks every base and sensitivity plan and verifies the
oracle bound each day to 0.01 JPY. Standard deviation uses ddof=0. Revenue day
classification treats absolute values ≤0.01 JPY as zero; operating interval counts
use power >1e−6 MW. Maximum loss is signed (zero if no loss); an idle strategy's
best/worst dates are arbitrary tied dates.

## Limitations / 限界

This is a **JEPX system-price research proxy**; an actual battery may settle on area prices or different contracts. Grid fees, imbalance costs, market impact, bid acceptance, transmission constraints, capex and fixed operating costs are omitted. All planned volumes are assumed executable. Degradation is only a hypothetical linear throughput charge, not a lifetime model. Battery parameters are hypothetical. Perfect foresight is infeasible in practice. These revenues do **not** demonstrate commercial operation or profitability.

JEPX system priceを用いた**研究用proxy**です。実設備はarea priceや別契約で決済される可能性があります。grid fees（系統料金）、imbalance costs、market impact、bid acceptance、transmission constraints、設備投資・固定運転費を考慮せず、全計画量の約定を仮定します。劣化コストは仮想の線形throughput費用で、寿命モデルではありません。電池条件も仮想設定です。Perfect foresightは実行不可能であり、この収益は商用運用・利益の証明ではありません。

AI assistance was used for implementation, testing and documentation; the owner remains responsible for understanding and explaining the choices.
