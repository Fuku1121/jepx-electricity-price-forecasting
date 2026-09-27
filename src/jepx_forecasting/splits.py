"""Chronological boundaries on whole days, with no shuffled split."""
from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class DateSplit:
    train: pd.DatetimeIndex
    validation: pd.DatetimeIndex
    test: pd.DatetimeIndex


def chronological_split(index, validation_start, test_start, test_end) -> DateSplit:
    index = pd.DatetimeIndex(index)
    if index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("Index must be unique and sorted")
    v, t, e = map(pd.Timestamp, (validation_start, test_start, test_end))
    if not v < t <= e or any(d != d.normalize() for d in (v, t, e)):
        raise ValueError("Require midnight validation_start < test_start <= test_end")
    if any(d not in index for d in (v, t, e)):
        raise ValueError("Requested boundaries are outside usable data")
    result = DateSplit(index[index < v], index[(index >= v) & (index < t)],
                       index[(index >= t) & (index <= e)])
    if any(len(part) == 0 for part in (result.train, result.validation, result.test)):
        raise ValueError("All partitions must be nonempty")
    return result
