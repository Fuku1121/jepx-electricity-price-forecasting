"""Forecast-only scheduling; oracle access is confined to a named benchmark."""
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import csc_matrix
from .battery import BatteryConfig, BatterySchedule, prices48, DELTA_HOURS, KWH_PER_MWH


def _solve(prices, config):
    p = prices48(prices)
    b = config
    # x = [charge(48), discharge(48), SOC(49), binary charge-mode(48)]
    n, size = 48, 193
    c = np.zeros(size)
    scale = DELTA_HOURS * KWH_PER_MWH
    c[:n] = (p+b.degradation_jpy_per_kwh)*scale
    c[n:2*n] = (-p+b.degradation_jpy_per_kwh)*scale
    low, high = np.zeros(size), np.ones(size)
    high[:n], high[n:2*n] = b.charge_power_mw, b.discharge_power_mw
    low[96:145], high[96:145] = b.capacity_mwh*b.min_soc_fraction, b.capacity_mwh*b.max_soc_fraction
    low[96] = high[96] = low[144] = high[144] = b.initial_mwh
    A = np.zeros((3*n, size))
    lb, ub = np.full(3*n, -np.inf), np.zeros(3*n)
    for t in range(n):
        A[t,96+t+1], A[t,96+t] = 1, -1
        A[t,t], A[t,n+t] = -b.charge_efficiency*DELTA_HOURS, DELTA_HOURS/b.discharge_efficiency
        lb[t] = 0
        A[n+t,t], A[n+t,145+t] = 1, -b.charge_power_mw
        A[2*n+t,n+t], A[2*n+t,145+t] = 1, b.discharge_power_mw
        ub[2*n+t] = b.discharge_power_mw
    integer = np.zeros(size)
    integer[145:] = 1
    result = milp(c, integrality=integer, bounds=Bounds(low, high),
                  constraints=LinearConstraint(csc_matrix(A), lb, ub),
                  options={"time_limit": 60.0, "mip_rel_gap": 1e-9, "presolve": True})
    if result.status != 0 or not result.success or result.x is None:
        raise RuntimeError(f"Battery MILP failed: status={result.status}; {result.message}")
    if not np.isfinite(result.x).all() or np.max(np.abs(result.x[145:]-np.round(result.x[145:]))) > 1e-6:
        raise RuntimeError("Invalid MILP solution")
    # No clipping or ex-post redispatch: validate and preserve the solver's plan.
    return BatterySchedule(tuple(result.x[:48]), tuple(result.x[48:96]),
                           tuple(result.x[96:145]), b, float(result.mip_gap))


def optimize_battery_schedule(forecast_prices, config=BatteryConfig()):
    """No actual-price argument; maximize forecast net cashflow in JPY."""
    return _solve(forecast_prices, config)


def perfect_foresight_optimizer(actual_prices, config=BatteryConfig()):
    """INFEASIBLE IN PRACTICE: perfect-foresight upper bound, not a strategy."""
    return _solve(actual_prices, config)
