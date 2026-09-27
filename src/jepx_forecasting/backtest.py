"""Freeze all forecast-driven plans before actual-price settlement or oracle work."""
import numpy as np
import pandas as pd
from .battery import BatteryConfig, BatterySchedule, prices48, no_operation, DELTA_HOURS, KWH_PER_MWH
from .optimization import optimize_battery_schedule, perfect_foresight_optimizer

STRATEGIES = ("no_operation", "naive_forecast", "lear_forecast", "perfect_foresight_upper_bound")


def validate_panel(frame):
    if not isinstance(frame, pd.DataFrame) or frame.shape[1] != 48 or frame.empty:
        raise ValueError("Expected a nonempty days by 48 panel")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates or not frame.index.is_monotonic_increasing or frame.index.hasnans:
        raise ValueError("Expected unique increasing delivery dates")
    if not frame.columns.equals(pd.Index(range(1,49))):
        raise ValueError("Slots must be ordered 1..48")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite panel")


def freeze_forecast_schedules(forecasts, config=BatteryConfig()):
    """Accept forecasts only. Return immutable schedules keyed by day."""
    validate_panel(forecasts)
    return {day: optimize_battery_schedule(row.to_numpy(), config)
            for day, row in forecasts.iterrows()}


def evaluate_schedule(schedule: BatterySchedule, actual_prices):
    """Settlement has no forecast argument and never changes the frozen schedule."""
    schedule.validate()
    actual = prices48(actual_prices)
    c, d = np.asarray(schedule.charge_mw), np.asarray(schedule.discharge_mw)
    charged, discharged = c.sum()*DELTA_HOURS, d.sum()*DELTA_HOURS
    market = float(actual @ (d-c) * DELTA_HOURS * KWH_PER_MWH)
    cost = float((charged+discharged)*KWH_PER_MWH*schedule.config.degradation_jpy_per_kwh)
    return dict(market_revenue_jpy=market, degradation_cost_jpy=cost,
                net_revenue_jpy=market-cost, charged_mwh=float(charged),
                discharged_mwh=float(discharged), charging_intervals=int((c>1e-6).sum()),
                discharging_intervals=int((d>1e-6).sum()))


def run_backtest(naive_forecasts, lear_forecasts, actual, config=BatteryConfig()):
    validate_panel(naive_forecasts)
    validate_panel(lear_forecasts)
    if not naive_forecasts.index.equals(lear_forecasts.index):
        raise ValueError("Forecast dates do not align")
    # Decision stage: actual never reaches either forecast optimizer.
    naive = freeze_forecast_schedules(naive_forecasts, config)
    lear = freeze_forecast_schedules(lear_forecasts, config)
    # All operational schedules now frozen. Evaluate only after this boundary.
    validate_panel(actual)
    if not actual.index.equals(lear_forecasts.index):
        raise ValueError("Actual dates do not align")
    schedules = {"no_operation": {d:no_operation(config) for d in actual.index},
                 "naive_forecast":naive, "lear_forecast":lear}
    schedules["perfect_foresight_upper_bound"] = {
        day:perfect_foresight_optimizer(row.to_numpy(), config) for day,row in actual.iterrows()}
    rows=[]
    for name, plans in schedules.items():
        for day, schedule in plans.items():
            rows.append(dict(date=day, strategy=name,
                             **evaluate_schedule(schedule, actual.loc[day].to_numpy())))
    daily=pd.DataFrame(rows)
    pivot=daily.pivot(index="date",columns="strategy",values="net_revenue_jpy")
    if (pivot.drop(columns="perfect_foresight_upper_bound").max(axis=1) > pivot.perfect_foresight_upper_bound+0.01).any():
        raise RuntimeError("Perfect-foresight upper bound violated")
    metrics=[]
    for name, block in daily.groupby("strategy", sort=False):
        v=block.net_revenue_jpy
        metrics.append(dict(strategy=name,total_realized_revenue_jpy=float(v.sum()),
            total_market_revenue_jpy=float(block.market_revenue_jpy.sum()),
            total_degradation_cost_jpy=float(block.degradation_cost_jpy.sum()),
            average_daily_revenue_jpy=float(v.mean()),median_daily_revenue_jpy=float(v.median()),
            std_daily_revenue_jpy=float(v.std(ddof=0)),positive_revenue_days=int((v>0.01).sum()),
            negative_revenue_days=int((v < -0.01).sum()),zero_revenue_days=int((v.abs()<=0.01).sum()),
            maximum_daily_profit_jpy=float(max(0,v.max())),maximum_daily_loss_jpy=float(min(0,v.min())),
            best_day=str(block.loc[v.idxmax(),'date'].date()),worst_day=str(block.loc[v.idxmin(),'date'].date()),
            total_charged_mwh=float(block.charged_mwh.sum()),total_discharged_mwh=float(block.discharged_mwh.sum()),
            charging_intervals=int(block.charging_intervals.sum()),discharging_intervals=int(block.discharging_intervals.sum())))
    return pd.DataFrame(metrics), daily, schedules
