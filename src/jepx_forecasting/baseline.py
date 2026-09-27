"""Auction curves already known at the forecast origin."""
import pandas as pd


def naive_predictions(daily: pd.DataFrame, days: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    previous, weekly = daily.shift(1).loc[days], daily.shift(7).loc[days]
    mixed = weekly.copy()
    use_previous = days.dayofweek.isin([1, 2, 3, 4])
    mixed.loc[use_previous] = previous.loc[use_previous]
    return {"naive_previous_day": previous, "naive_week": weekly, "naive_weekday": mixed}
