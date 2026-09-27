# Future work: forecast-driven battery scheduling (design only)

No battery optimizer, trading simulation or profit experiment has been implemented.
This is a research extension relevant to energy optimization work, including the
kind of questions one could discuss when applying to Bluefield Energy. It is not
an endorsed company project and implies neither commercial suitability nor hiring.

## Deterministic prototype

For half-hour t, let c[t], q[t] be grid-side charging/discharging power (kW),
e[t] stored energy (kWh), delta=0.5 h, efficiencies eta_c, eta_d in (0,1],
and forecast price p_hat[t] in JPY/kWh. Optimize:

`maximize sum_t p_hat[t] * (q[t] - c[t]) * delta`

subject to

- `e[t+1] = e[t] + eta_c*c[t]*delta - q[t]*delta/eta_d`;
- `E_min <= e[t] <= E_max` (capacity/SOC limits);
- `0 <= c[t] <= P_charge_max` and `0 <= q[t] <= P_discharge_max`;
- fixed initial SOC and a terminal SOC target (e.g. `e[T]=e[0]`), to prevent
  an artificial benefit from consuming free initial stored energy;
- a binary u[t] with `c[t] <= u[t]*P_charge_max` and
  `q[t] <= (1-u[t])*P_discharge_max` if simultaneous operation must be excluded.

Without the binary restriction this is an LP; with it this is a MILP.
Do not assume simultaneous charge/discharge is always ruled out by the objective,
especially under unusual prices or other payments. Specify whether capacity is
usable energy or nameplate capacity and how SOC percentages are converted.

## Honest backtest

Create schedules using only forecasts available at the auction deadline. Freeze
those schedules before observing realized settlement prices. Compare to a feasible
fixed schedule and a no-operation strategy. A schedule optimized on actual future
prices is a perfect-foresight upper bound, not an achievable strategy.
Keep efficiency, capacity, power and terminal conditions identical across methods.
A separate test period must be preserved for policy/forecast selection.

System price is not necessarily the battery's settlement price. Use the correct
area price and add grid connection limits, fees, degradation/throughput costs,
imbalance charges, bid acceptance and execution rules before discussing economics.
Distinguish price-taking assumptions from market impact; forecast MAE alone cannot
rank the value of schedules. Report realized net revenue, throughput, constraint
violations, downside risk and sensitivity to uncertain prices. Scenario or robust
optimization is a later extension; no profitability conclusion is made here.
