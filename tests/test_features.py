import numpy as np
import pandas as pd
import pytest
from jepx_forecasting.features import make_features


def test_exact_lags_and_past_rolling(daily):
    X = make_features(daily)
    assert X.shape == (100,247)
    for lag in (1,2,7):
        for slot in (1,23,48):
            assert X.iloc[20][f"lag{lag}_slot{slot}"] == daily.iloc[20-lag][slot]
    assert X.iloc[20]["mean7_slot1"] == pytest.approx(daily.iloc[13:20][1].mean())
    assert X.iloc[20]["std7_slot1"] == pytest.approx(daily.iloc[13:20][1].std(ddof=0))
    assert X.iloc[:7].isna().any(axis=1).all()
    assert not X.iloc[7:].isna().any().any()
    assert (X.filter(like="weekday").sum(axis=1) == 1).all()


def test_unknown_target_does_not_block_feature(daily):
    historical = daily.iloc[:81].copy()
    expected = make_features(historical).iloc[-1]
    historical.iloc[-1] = np.nan
    pd.testing.assert_series_equal(make_features(historical).iloc[-1],expected)


def test_missing_calendar_day_rejected(daily):
    with pytest.raises(ValueError, match="contiguous"):
        make_features(daily.drop(daily.index[20]))
