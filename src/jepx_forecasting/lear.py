"""Independent slot regressions with training-only scaling and daily refits."""
import warnings
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model(alpha: float):
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and positive")
    # Multi-output Lasso minimizes elementwise L1: each slot is independent.
    # This is not MultiTaskLasso (which couples feature selection across outputs).
    return make_pipeline(StandardScaler(), Lasso(alpha=alpha, max_iter=30000,
                                                tol=1e-4, selection="cyclic"))


def walk_forward(X, y, days, alpha, min_train_days=56, window_days=None, progress=None):
    if not X.index.equals(y.index) or not X.index.is_monotonic_increasing or X.index.has_duplicates:
        raise ValueError("Aligned, sorted and unique X/y indices required")
    if min_train_days < 2 or (window_days is not None and window_days < min_train_days):
        raise ValueError("Window must be at least min_train_days >= 2")
    days = pd.DatetimeIndex(days)
    if days.empty or days.has_duplicates or not days.is_monotonic_increasing:
        raise ValueError("Forecast days must be nonempty, unique and sorted")
    complete = X.notna().all(axis=1) & y.notna().all(axis=1)
    predictions, audit = [], []
    for i, day in enumerate(days):
        train = X.index[(X.index < day) & complete]
        if window_days is not None:
            train = train[train >= day - pd.Timedelta(days=window_days)]
        if len(train) < min_train_days:
            raise ValueError(f"Insufficient history before {day.date()}")
        model = make_model(alpha)
        # Treat non-convergence as failure, not a silently accepted experiment.
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(X.loc[train], y.loc[train])
        prediction = model.predict(X.loc[[day]])[0]
        if not np.isfinite(prediction).all():
            raise ValueError("Nonfinite prediction")
        predictions.append(prediction)
        reg = model.named_steps["lasso"]
        audit.append({"date": day, "train_start": train[0], "train_end": train[-1],
                      "n_train_days": len(train), "alpha": alpha,
                      "nonzero_coefficients": int(np.count_nonzero(reg.coef_)),
                      "max_iterations": int(np.max(reg.n_iter_))})
        if progress and (i % 30 == 0 or i + 1 == len(days)):
            progress(f"{i+1}/{len(days)} forecast days; latest {day.date()}")
    return pd.DataFrame(predictions, index=days, columns=y.columns), pd.DataFrame(audit)


def select_alpha(X, y, validation_days, alphas, **kwargs):
    # Called only on a pre-test prefix by the experiment pipeline.
    scores = []
    for alpha in sorted(set(alphas)):
        pred, _ = walk_forward(X, y, validation_days, alpha, **kwargs)
        mae = float(np.abs(y.loc[validation_days].to_numpy() - pred.to_numpy()).mean())
        scores.append({"alpha": alpha, "validation_mae": mae})
    if not scores:
        raise ValueError("Empty alpha grid")
    table = pd.DataFrame(scores).sort_values(["validation_mae", "alpha"])
    return float(table.iloc[0]["alpha"]), table
