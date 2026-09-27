import numpy as np
import pandas as pd
import pytest
from jepx_forecasting.data import load_daily


def official(daily):
    return pd.DataFrame({"受渡日":np.repeat(daily.index.strftime("%Y/%m/%d"),48),
                         "時刻コード":np.tile(np.arange(1,49),len(daily)),
                         "システムプライス(円/kWh)":daily.to_numpy().ravel()})


@pytest.mark.parametrize("encoding",["utf-8-sig","cp932"])
def test_official_encodings(daily,tmp_path,encoding):
    path=tmp_path/"spot.csv"
    official(daily).to_csv(path,index=False,encoding=encoding)
    loaded,manifest=load_daily([path])
    np.testing.assert_allclose(loaded,daily)
    assert len(manifest[0]["sha256"])==64


@pytest.mark.parametrize("problem",["duplicate","missing_slot","missing_day","infinity","bad_slot","null_date"])
def test_bad_data_rejected(daily,tmp_path,problem):
    frame=official(daily)
    if problem=="duplicate": frame=pd.concat([frame,frame.iloc[:1]])
    if problem=="missing_slot": frame=frame.iloc[1:]
    if problem=="missing_day": frame=frame.drop(index=range(48,96))
    if problem=="infinity": frame.iloc[0,2]=np.inf
    if problem=="bad_slot": frame.iloc[0,1]=49
    if problem=="null_date": frame.iloc[0,0]=None
    path=tmp_path/"bad.csv"
    frame.to_csv(path,index=False)
    with pytest.raises(ValueError): load_daily([path])
