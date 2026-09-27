"""Synthetic decision-layer tests, including adversarial actual-price mutation."""
from dataclasses import replace, FrozenInstanceError
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from jepx_forecasting.battery import BatteryConfig, BatterySchedule, no_operation
from jepx_forecasting.optimization import optimize_battery_schedule, perfect_foresight_optimizer
from jepx_forecasting.backtest import evaluate_schedule, run_backtest, freeze_forecast_schedules

@pytest.fixture
def cheap_then_expensive():
    return np.r_[np.full(24,10.),np.full(24,50.)]

def panel(values):
    return pd.DataFrame([values],index=pd.to_datetime(["2024-04-01"]),columns=range(1,49))

def test_soc_bounds_and_dynamics(cheap_then_expensive):
    s=optimize_battery_schedule(cheap_then_expensive)
    c,d,z=map(np.asarray,(s.charge_mw,s.discharge_mw,s.soc_mwh))
    assert z.min()>=0.1-1e-6 and z.max()<=0.9+1e-6
    np.testing.assert_allclose(np.diff(z),.95*c*.5-d*.5/.95,atol=1e-6)

def test_power_limits(cheap_then_expensive):
    b=BatteryConfig(charge_power_mw=.17,discharge_power_mw=.23)
    s=optimize_battery_schedule(cheap_then_expensive,b)
    assert min(s.charge_mw)>=-1e-6 and max(s.charge_mw)<=.17+1e-6
    assert min(s.discharge_mw)>=-1e-6 and max(s.discharge_mw)<=.23+1e-6

def test_initial_terminal_soc(cheap_then_expensive):
    b=BatteryConfig(capacity_mwh=2,initial_soc_fraction=.3)
    s=optimize_battery_schedule(cheap_then_expensive,b)
    assert s.soc_mwh[0]==pytest.approx(.6)
    assert s.soc_mwh[-1]==pytest.approx(.6)

@pytest.mark.parametrize('prices',[np.full(48,-20.),np.linspace(-50,50,48),np.full(48,20.)])
def test_no_simultaneous_even_negative_prices(prices):
    s=optimize_battery_schedule(prices)
    assert not ((np.asarray(s.charge_mw)>1e-6)&(np.asarray(s.discharge_mw)>1e-6)).any()

def test_optimizer_has_forecast_only_interface(cheap_then_expensive):
    with pytest.raises(TypeError):
        optimize_battery_schedule(cheap_then_expensive,actual_prices=cheap_then_expensive)

def test_settlement_only_actual_and_units():
    b=BatteryConfig(charge_efficiency=1,discharge_efficiency=1,min_soc_fraction=0,max_soc_fraction=1)
    c=np.zeros(48);d=c.copy();c[0]=.5;d[1]=.5
    soc=np.r_[.5,.5+np.cumsum((c-d)*.5)]
    s=BatterySchedule(c,d,soc,b)
    p=np.zeros(48);p[0]=10;p[1]=50
    result=evaluate_schedule(s,p)
    assert result['market_revenue_jpy']==pytest.approx(10000)
    assert result['charged_mwh']==pytest.approx(.25)
    assert evaluate_schedule(s,p*2)['net_revenue_jpy']==pytest.approx(20000)

def test_synthetic_optimum_and_determinism(cheap_then_expensive):
    b=BatteryConfig(charge_efficiency=1,discharge_efficiency=1,initial_soc_fraction=.1)
    s=optimize_battery_schedule(cheap_then_expensive,b)
    # 0.8 MWh transferred from 10 to 50 JPY/kWh, exactly 32,000 JPY.
    assert evaluate_schedule(s,cheap_then_expensive)['net_revenue_jpy']==pytest.approx(32000)
    assert sum(s.charge_mw[24:])==pytest.approx(0)
    assert sum(s.discharge_mw[:24])==pytest.approx(0)
    assert s==optimize_battery_schedule(cheap_then_expensive,b)

def test_flat_positive_prices_idle():
    s=optimize_battery_schedule(np.full(48,10.))
    assert sum(s.charge_mw)==pytest.approx(0)
    assert sum(s.discharge_mw)==pytest.approx(0)

def test_forecast_schedule_unchanged_when_actual_mutated(cheap_then_expensive):
    f=panel(cheap_then_expensive)
    m1,d1,s1=run_backtest(f,f,f)
    m2,d2,s2=run_backtest(f,f,panel(cheap_then_expensive[::-1]*7))
    for name in ('naive_forecast','lear_forecast'):
        assert s1[name]==s2[name]
    assert d1[d1.strategy=='lear_forecast'].net_revenue_jpy.iloc[0] != d2[d2.strategy=='lear_forecast'].net_revenue_jpy.iloc[0]

def test_forecasts_frozen_before_oracle(monkeypatch,cheap_then_expensive):
    import jepx_forecasting.backtest as bt
    events=[]
    original_forecast=bt.optimize_battery_schedule
    original_oracle=bt.perfect_foresight_optimizer
    def forecast(p,b):events.append('forecast');return original_forecast(p,b)
    def oracle(p,b):events.append('oracle');return original_oracle(p,b)
    monkeypatch.setattr(bt,'optimize_battery_schedule',forecast)
    monkeypatch.setattr(bt,'perfect_foresight_optimizer',oracle)
    f=panel(cheap_then_expensive)
    metrics,_,_=bt.run_backtest(f,f,f)
    assert events==['forecast','forecast','oracle']
    assert 'perfect_foresight_upper_bound' in set(metrics.strategy)

def test_upper_bound_dominates_bad_forecast(cheap_then_expensive):
    f=panel(cheap_then_expensive);bad=panel(cheap_then_expensive[::-1])
    metrics,_,_=run_backtest(bad,bad,f)
    v=metrics.set_index('strategy').total_realized_revenue_jpy
    assert v['perfect_foresight_upper_bound']>=max(v)-.01
    assert v['lear_forecast']<0 and v['no_operation']==0

def test_throughput_cost_charged_and_discharged(cheap_then_expensive):
    b=BatteryConfig(degradation_jpy_per_kwh=3)
    s=optimize_battery_schedule(cheap_then_expensive,b)
    v=evaluate_schedule(s,cheap_then_expensive)
    assert v['degradation_cost_jpy']==pytest.approx(3000*(v['charged_mwh']+v['discharged_mwh']))
    assert v['net_revenue_jpy']==pytest.approx(v['market_revenue_jpy']-v['degradation_cost_jpy'])

def test_large_cost_changes_decision_to_idle(cheap_then_expensive):
    s=optimize_battery_schedule(cheap_then_expensive,BatteryConfig(degradation_jpy_per_kwh=100))
    assert sum(s.charge_mw)==pytest.approx(0)
    assert sum(s.discharge_mw)==pytest.approx(0)

def test_solver_failure_raises(monkeypatch,cheap_then_expensive):
    import jepx_forecasting.optimization as opt
    monkeypatch.setattr(opt,'milp',lambda *a,**k:SimpleNamespace(status=1,success=False,x=None,message='time limit'))
    with pytest.raises(RuntimeError,match='time limit'):opt.optimize_battery_schedule(cheap_then_expensive)

@pytest.mark.parametrize('kwargs',[{'charge_efficiency':0},{'capacity_mwh':-1},{'initial_soc_fraction':1.1},{'degradation_jpy_per_kwh':-1},{'charge_power_mw':float('nan')}])
def test_invalid_battery_rejected(kwargs):
    with pytest.raises(ValueError):BatteryConfig(**kwargs)

@pytest.mark.parametrize('prices',[np.ones(47),np.full(48,np.nan),np.full(48,np.inf)])
def test_invalid_prices_rejected(prices):
    with pytest.raises(ValueError):optimize_battery_schedule(prices)

def test_schedule_immutable():
    s=no_operation()
    with pytest.raises(FrozenInstanceError):s.charge_mw=(1.,)*48
    with pytest.raises(TypeError):s.charge_mw[0]=1

def test_bad_actual_alignment(cheap_then_expensive):
    f=panel(cheap_then_expensive);a=f.copy();a.index=a.index+pd.Timedelta(days=1)
    with pytest.raises(ValueError,match='align'):run_backtest(f,f,a)

def test_schedule_rejects_simultaneous():
    b=BatteryConfig(charge_efficiency=1,discharge_efficiency=1)
    with pytest.raises(ValueError,match='Simultaneous'):
        BatterySchedule((.1,)*48,(.1,)*48,(.5,)*49,b)
