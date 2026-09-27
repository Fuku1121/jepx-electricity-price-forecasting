"""One row per delivery day; every price feature stops at d-1."""
import pandas as pd
from .data import validate_daily


def make_features(daily: pd.DataFrame) -> pd.DataFrame:
    # Missing targets are allowed for live inference; incomplete histories yield NaN
    # and are explicitly excluded by the forecasting routine, never backfilled.
    validate_daily(daily, allow_missing=True)
    parts = []
    for lag in (1, 2, 7):
        parts.append(daily.shift(lag).add_prefix(f"lag{lag}_slot"))
    history = daily.shift(1)  # shift BEFORE rolling: never includes delivery d
    parts += [history.rolling(7, min_periods=7).mean().add_prefix("mean7_slot"),
              history.rolling(7, min_periods=7).std(ddof=0).add_prefix("std7_slot")]
    calendar = pd.DataFrame({f"weekday_{k}": (daily.index.dayofweek == k).astype(float)
                             for k in range(7)}, index=daily.index)
    return pd.concat([*parts, calendar], axis=1).astype(float)
