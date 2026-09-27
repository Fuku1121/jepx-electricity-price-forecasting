import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def daily():
    # Synthetic fixture ONLY for software checks, not evidence of JEPX accuracy.
    rng = np.random.default_rng(81)
    days = pd.date_range("2023-01-01", periods=100, freq="D")
    values = 12 + 2*np.sin(np.arange(48)[None, :]/48*2*np.pi) + rng.normal(size=(100,48))
    return pd.DataFrame(values, index=days, columns=range(1,49))
