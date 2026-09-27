"""Metrics on exactly aligned observations; no silent dropping of missing rows."""
import numpy as np
import pandas as pd


def evaluate(actual: pd.DataFrame, predictions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if actual.empty or not np.isfinite(actual.to_numpy()).all():
        raise ValueError("Actuals must be nonempty and finite")
    rows = []
    for name, pred in predictions.items():
        if not actual.index.equals(pred.index) or not actual.columns.equals(pred.columns):
            raise ValueError("Actuals and predictions must have identical dates and slots")
        if not np.isfinite(pred.to_numpy()).all():
            raise ValueError("Predictions must be finite")
        err = pred.to_numpy() - actual.to_numpy()
        rows.append({"model": name, "mae": float(np.abs(err).mean()),
                     "rmse": float(np.sqrt(np.square(err).mean())), "n_observations": err.size})
    table = pd.DataFrame(rows)
    denom = float(table.set_index("model").loc["naive_week", "mae"])
    table["rmae_week"] = table["mae"] / denom if denom > 0 else np.nan
    return table
