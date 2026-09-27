import numpy as np
import pandas as pd
from jepx_forecasting.features import make_features
from jepx_forecasting.lear import walk_forward
from jepx_forecasting.pipeline import run_experiment, Config


def test_future_and_current_target_prices_do_not_change_past_features(daily):
    mutated = daily.copy()
    mutated.iloc[80:] += 10000
    pd.testing.assert_frame_equal(make_features(daily).iloc[:81], make_features(mutated).iloc[:81])


def test_target_and_future_mutation_preserves_origin_prediction(daily):
    origin = daily.index[80:81]
    X = make_features(daily)
    first, audit = walk_forward(X,daily,origin,.3)
    mutated = daily.copy()
    mutated.iloc[80:] = 50000
    second, _ = walk_forward(make_features(mutated),mutated,origin,.3)
    np.testing.assert_allclose(first,second,rtol=0,atol=0)
    assert audit.iloc[0].train_end < origin[0]
    prefix = daily.iloc[:81].copy()
    prefix.iloc[-1] = np.nan
    third, _ = walk_forward(make_features(prefix),prefix,origin,.3)
    np.testing.assert_allclose(first,third,rtol=0,atol=0)


def test_test_targets_do_not_tune_alpha(daily):
    config=Config("2023-03-15","2023-03-17","2023-03-18",(.1,1.))
    a=run_experiment(daily,config)
    mutated=daily.copy()
    mutated.loc["2023-03-17":] += 4000
    b=run_experiment(mutated,config)
    assert a["alpha"]==b["alpha"]
    pd.testing.assert_frame_equal(a["tuning"],b["tuning"])
    np.testing.assert_allclose(a["predictions"]["lear_lasso"].iloc[0],b["predictions"]["lear_lasso"].iloc[0])
