import numpy as np
import pandas as pd
import pytest
from jepx_forecasting.baseline import naive_predictions
from jepx_forecasting.features import make_features
from jepx_forecasting.lear import make_model, walk_forward
from jepx_forecasting.metrics import evaluate
from jepx_forecasting.pipeline import Config,run_experiment,save_results


def test_baseline_mapping(daily):
    days = daily.index[70:77]
    p = naive_predictions(daily,days)
    for day in days:
        lag=1 if day.dayofweek in (1,2,3,4) else 7
        np.testing.assert_array_equal(p["naive_weekday"].loc[day],daily.loc[day-pd.Timedelta(days=lag)])


def test_training_only_scaling_and_independent_slots(daily):
    X=make_features(daily).dropna()
    train=X.iloc[:60]
    y=daily.loc[train.index]
    model=make_model(.3).fit(train,y)
    np.testing.assert_allclose(model.named_steps["standardscaler"].mean_,train.mean())
    single=make_model(.3).fit(train,y[1])
    np.testing.assert_allclose(model.predict(X.iloc[60:61])[:,0],single.predict(X.iloc[60:61]))


def test_rolling_window_and_no_current_day(daily):
    _, audit=walk_forward(make_features(daily),daily,daily.index[90:92],.3,window_days=60)
    assert (audit.n_train_days==60).all()
    assert (audit.train_end<audit.date).all()


def test_metrics_known_values_and_alignment():
    y=pd.DataFrame([[1.,3.]])
    p={"naive_week":pd.DataFrame([[2.,5.]]),"lear_lasso":pd.DataFrame([[1.,3.]])}
    scores=evaluate(y,p).set_index("model")
    assert scores.loc["naive_week","mae"]==1.5
    assert scores.loc["naive_week","rmse"]==pytest.approx(np.sqrt(2.5))
    assert scores.loc["lear_lasso","rmae_week"]==0
    assert np.isnan(evaluate(y,{"naive_week":y}).iloc[0].rmae_week)
    with pytest.raises(ValueError,match="identical"):
        evaluate(y,{"naive_week":y.rename(index={0:1})})


def test_end_to_end_pipeline_and_artifacts(daily,tmp_path):
    config=Config("2023-03-15","2023-03-17","2023-03-18",(.3,))
    result=run_experiment(daily,config)
    assert set(result["metrics"].n_observations)=={96}
    assert len(result["metrics"])==4
    # Synthetic artifacts live only in pytest's temporary directory.
    save_results(daily,result,tmp_path,[],0.)
    assert len(pd.read_csv(tmp_path/"predictions_full.csv"))==96
    for name in ("actual_vs_predicted.png","model_mae.png","slot_errors.png"):
        assert (tmp_path/"figures"/name).stat().st_size>1000


@pytest.mark.parametrize("alpha",[0,-1,np.nan])
def test_bad_alpha(alpha):
    with pytest.raises(ValueError): make_model(alpha)
