# Future work after the battery decision layer

The deterministic daily MILP prototype is now implemented and evaluated in
[Battery optimization](BATTERY_OPTIMIZATION.md) and [Battery results](BATTERY_RESULTS.md).
It is not an endorsed company project or a commercially validated operation.

Further work should use new validation/out-of-sample periods rather than optimize
against the already reported test year:

- Area-specific settlement, grid fees, imbalance charges, bids and acceptance.
- Transmission/site limits, ramping, degradation linked to SOC/temperature/cycle age,
  capacity fade, capex and operating expenses.
- Robust/scenario optimization and calibrated forecast uncertainty.
- Interday energy carryover and terminal value design, with comparable information
  sets and no free initial energy.
- Publication-time data snapshots and an auditable live forecast/decision clock.
- Multi-year stability and appropriate paired inference, acknowledging serial dependence.

These extensions have not been implemented or evaluated in the current results.
Do not interpret simplified system-price cashflows as a battery investment case.
