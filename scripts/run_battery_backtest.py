"""Reuse frozen Stage 1 predictions; never train or select a forecasting model."""
import argparse
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
import importlib.metadata
import numpy as np
import pandas as pd
from jepx_forecasting.battery import BatteryConfig
from jepx_forecasting.backtest import run_backtest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen_predictions(path, stage1, plan):
    frame=pd.read_csv(path,parse_dates=['date'])
    cols=['actual','naive_previous_day','naive_week','naive_weekday','lear_lasso']
    days=pd.date_range(plan['test_start'],plan['test_end'],freq='D')
    expected=pd.MultiIndex.from_product([days,range(1,49)],names=['date','slot'])
    if not pd.MultiIndex.from_frame(frame[['date','slot']]).equals(expected):
        raise ValueError('Predictions must contain exactly the original 365 x 48 ordered observations')
    if not np.isfinite(frame[cols].to_numpy()).all():raise ValueError('Nonfinite predictions')
    published=pd.read_csv(stage1/'metrics.csv').set_index('model')
    for model in cols[1:]:
        error=frame[model]-frame.actual
        if not np.allclose([np.abs(error).mean(),np.sqrt((error**2).mean())],published.loc[model,['mae','rmse']].astype(float),rtol=1e-9,atol=1e-9):
            raise ValueError('Input does not reproduce published Stage 1 metrics')
    sample=pd.read_csv(stage1/'predictions_sample.csv',parse_dates=['date'])
    pd.testing.assert_frame_equal(frame.head(len(sample)).reset_index(drop=True),sample,check_exact=False,atol=1e-10,rtol=1e-10)
    daily_mae=pd.read_csv(stage1/'daily_mae.csv',parse_dates=['date'])
    for model in cols[1:]:
        expected_mae=daily_mae[daily_mae.model==model].set_index('date').mae.reindex(days)
        observed=(frame[model]-frame.actual).abs().groupby(frame.date).mean().reindex(days)
        if not np.allclose(expected_mae,observed,atol=1e-9,rtol=1e-9):raise ValueError('Daily Stage 1 MAE mismatch')
    # Existing test ranking was explicitly requested, not a new battery-revenue selection.
    naive=published.loc[published.index.str.startswith('naive_'),'mae'].idxmin()
    if naive!=plan['naive_model']:raise ValueError('Baseline differs from frozen design')
    return frame,{name:frame.pivot(index='date',columns='slot',values=name) for name in cols}


def plot_artifacts(daily, metrics, sample, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=output/'figures';out.mkdir(exist_ok=True)
    colors={'no_operation':'#707070','naive_forecast':'#d58936','lear_forecast':'#007f86','perfect_foresight_upper_bound':'#8659a5'}
    labels={'no_operation':'No operation','naive_forecast':'Naive forecast','lear_forecast':'LEAR forecast','perfect_foresight_upper_bound':'Perfect-foresight upper bound'}
    for cumulative,name in [(True,'cumulative_revenue'),(False,'daily_revenue')]:
        fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
        for strategy,block in daily.groupby('strategy',sort=False):
            v=block.net_revenue_jpy.cumsum() if cumulative else block.net_revenue_jpy
            ax.plot(block.date,v/1000,label=labels[strategy],color=colors[strategy],linewidth=1 if cumulative else .65,alpha=.9)
        ax.axhline(0,color='black',linewidth=.5);ax.set(xlabel='Delivery day (JST)',ylabel='Thousand JPY',title=('Cumulative' if cumulative else 'Daily')+' proxy net revenue | base case; no fees')
        ax.legend(fontsize=8);fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
    values=metrics.total_realized_revenue_jpy/1000
    bars=ax.barh([labels[n] for n in metrics.strategy],values,color=[colors[n] for n in metrics.strategy])
    ax.bar_label(bars,fmt='%.1f',padding=4);ax.set_xlim(0,values.max()*1.2)
    ax.set(xlabel='Thousand JPY / test year',title='Base-case proxy net revenue | oracle is not deployable')
    fig.savefig(out/'strategy_revenue_comparison.png',dpi=160);plt.close(fig)
    first=sample.date.min();block=sample[(sample.date==first)&(sample.strategy=='lear_forecast')]
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    axes[0].plot(block.slot,block.forecast_price,label='Frozen LEAR forecast');axes[0].plot(block.slot,block.actual_price,label='Actual (evaluation only)',alpha=.7)
    axes[0].set(ylabel='JPY/kWh',title='First test day: '+str(first.date())+' | not selected by return');axes[0].legend(fontsize=8)
    axes[1].bar(block.slot,block.charge_mw,label='Charge',color='#007f86');axes[1].bar(block.slot,-block.discharge_mw,label='Discharge (negative)',color='#d58936')
    axes[1].set(ylabel='MW',xlabel='Half-hour slot (1 = 00:00 JST)');axes[1].legend(fontsize=8)
    fig.savefig(out/'sample_battery_schedule.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
    for strategy in colors:
        b=sample[(sample.date==first)&(sample.strategy==strategy)]
        ax.step(range(49),np.r_[b.soc_start_mwh.to_numpy(),b.soc_end_mwh.iloc[-1]],where='post',label=labels[strategy],color=colors[strategy])
    ax.axhline(.1,color='black',ls=':');ax.axhline(.9,color='black',ls=':')
    ax.set(xlabel='Half-hour boundary (0 = start, 48 = end)',ylabel='Stored energy (MWh)',title='First-day SOC | fixed 0.5 MWh endpoints');ax.legend(fontsize=8)
    fig.savefig(out/'soc_example.png',dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions',type=Path,default=Path('results/predictions_full.csv'))
    parser.add_argument('--stage1-results',type=Path,default=Path('results'))
    parser.add_argument('--plan',type=Path,default=Path('configs/battery_experiment.json'))
    parser.add_argument('--output',type=Path,default=Path('results/battery'))
    args=parser.parse_args();started=time.perf_counter()
    plan=json.loads(args.plan.read_text());base=BatteryConfig(**plan['base'])
    frame,panels=load_frozen_predictions(args.predictions,args.stage1_results,plan)
    scenarios=[('base',base)]+[(f'rte_{int(e*100)}',replace(base,charge_efficiency=np.sqrt(e),discharge_efficiency=np.sqrt(e))) for e in plan['sensitivity']['round_trip_efficiency']]+[(f'cost_{cost:g}',replace(base,degradation_jpy_per_kwh=cost)) for cost in plan['sensitivity']['degradation_jpy_per_kwh']]
    all_metrics=[];all_daily=[];base_schedules=None;max_gap=0.
    for name,config in scenarios:
        print('Running '+name,flush=True)
        metrics,daily,schedules=run_backtest(panels[plan['naive_model']],panels['lear_lasso'],panels['actual'],config)
        max_gap=max(max_gap,max(s.solver_gap for plans in schedules.values() for s in plans.values()))
        metrics.insert(0,'scenario',name);daily.insert(0,'scenario',name)
        all_metrics.append(metrics);all_daily.append(daily)
        if name=='base':base_schedules=schedules
        print(metrics[['strategy','total_realized_revenue_jpy']].to_string(index=False),flush=True)
    # Nothing is written until all scenarios pass; failed solvers cannot masquerade as results.
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    metrics=pd.concat(all_metrics,ignore_index=True);daily=pd.concat(all_daily,ignore_index=True)
    metrics[metrics.scenario=='base'].to_csv(out/'strategy_metrics.csv',index=False)
    daily[daily.scenario=='base'].to_csv(out/'daily_revenue.csv',index=False)
    daily[daily.scenario=='base'].pivot(index='date',columns='strategy',values='net_revenue_jpy').resample('MS').sum().to_csv(out/'monthly_revenue.csv')
    metrics.to_csv(out/'sensitivity_metrics.csv',index=False)
    daily.to_csv(out/'sensitivity_daily_revenue.csv',index=False)
    rows=[]
    for name,plans in base_schedules.items():
        for day,s in plans.items():
            forecast=None if name in ('no_operation','perfect_foresight_upper_bound') else panels[plan['naive_model'] if name=='naive_forecast' else 'lear_lasso'].loc[day].to_numpy()
            for t in range(48):
                rows.append(dict(date=day,strategy=name,slot=t+1,charge_mw=s.charge_mw[t],discharge_mw=s.discharge_mw[t],soc_start_mwh=s.soc_mwh[t],soc_end_mwh=s.soc_mwh[t+1],forecast_price=forecast[t] if forecast is not None else np.nan,actual_price=panels['actual'].loc[day].iloc[t]))
    schedules=pd.DataFrame(rows);schedules.to_csv(out/'battery_schedules_full.csv',index=False)
    sample=schedules[schedules.date<panels['actual'].index[0]+pd.Timedelta(days=7)]
    sample.to_csv(out/'battery_schedules_sample.csv',index=False)
    (out/'battery_config.json').write_text(json.dumps({name:asdict(c) for name,c in scenarios},indent=2)+'\n')
    plot_artifacts(daily[daily.scenario=='base'],metrics[metrics.scenario=='base'],sample,out)
    source=Path(__file__).resolve().parents[1]
    paths=[source/'src/jepx_forecasting'/f for f in ['battery.py','optimization.py','backtest.py']]+[Path(__file__).resolve(),args.plan]
    metadata={'status':'executed_on_frozen_stage1_predictions','created_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,'test_start':plan['test_start'],'test_end':plan['test_end'],'days':365,'slots_per_day':48,'stage1_commit':plan['stage1_commit'],'predictions_sha256':sha(args.predictions),'stage1_metrics_sha256':sha(args.stage1_results/'metrics.csv'),'plan_sha256':sha(args.plan),'source_sha256':{p.name:sha(p) for p in paths},'python':platform.python_version(),'versions':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','matplotlib']},'solver':'scipy.optimize.milp / HiGHS','solver_time_limit_seconds':60,'mip_rel_gap':1e-9,'maximum_observed_gap':max_gap,'solver_failures':0,'operational_forecast_only':True,'initial_and_terminal_soc_equal_each_day':True,'degradation_basis':'grid-side charge plus discharge kWh','round_trip_base':base.round_trip_efficiency,'interpretation':'Hypothetical system-price proxy, not commercial profit; perfect foresight is an infeasible upper bound','baseline_selection':'Existing Stage 1 test-MAE ranking at user request; not battery-return selection','data_source':'JEPX official system prices; original data rights remain with JEPX','artifacts_sha256':{str(p.relative_to(out)).replace(chr(92),'/'):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ['battery_run_metadata.json','battery_schedules_full.csv']}}
    (out/'battery_run_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')

if __name__=='__main__':main()
