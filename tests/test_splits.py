import pytest
from jepx_forecasting.splits import chronological_split


def test_chronological_split(daily):
    s = chronological_split(daily.index, "2023-03-01", "2023-04-01", "2023-04-10")
    assert s.train.max() < s.validation.min() <= s.validation.max() < s.test.min()
    assert len(s.test)==10
    assert len(s.train)+len(s.validation)+len(s.test)==len(daily)


@pytest.mark.parametrize("v,t,e", [("2023-04-01","2023-03-01","2023-04-10"),
                                   ("2023-03-01","2023-04-01","2023-04-11")])
def test_invalid_boundaries(daily,v,t,e):
    with pytest.raises(ValueError):
        chronological_split(daily.index,v,t,e)
