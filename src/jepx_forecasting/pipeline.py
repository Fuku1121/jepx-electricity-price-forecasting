"""Experiment orchestration and auditable artifacts; ingestion is separate."""
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import platform
import time
import importlib.metadata

import numpy as np
import pandas as pd

from .data import load_daily
from .features import make_features
from .splits import chronological_split
from .baseline import naive_predictions
from .lear import select_alpha, walk_forward
from .metrics import evaluate


@dataclass(frozen=True)
class Config:
    validation_start: str = "2024-01-01"
    test_start: str = "2024-04-01"
    test_end: str = "2025-03-31"
    alphas: tuple = (0.03, 0.1, 0.3, 1.0)
    min_train_days: int = 56
    window_days: int | None = None


def run_experiment(daily, config=Config(), progress=None):
    from .data import validate_daily
    validate_daily(daily)
    X = make_features(daily)
    usable = X.dropna().index
    split = chronological_split(usable, config.validation_start, config.test_start, config.test_end)
    if len(split.train) < config.min_train_days:
        raise ValueError("Initial training partition too short")
    kwargs = dict(min_train_days=config.min_train_days, window_days=config.window_days, progress=progress)
    # Hard boundary: neither test features nor test targets reach hyperparameter selection.
    prefix = daily.index < pd.Timestamp(config.test_start)
    alpha, tuning = select_alpha(X.loc[prefix], daily.loc[prefix], split.validation,
                                config.alphas, **kwargs)
    if progress:
        progress(f"Validation selected alpha={alpha}; now evaluating untouched test period")
    lear, audit = walk_forward(X, daily, split.test, alpha, **kwargs)
    predictions = naive_predictions(daily, split.test)
    predictions["lear_lasso"] = lear
    scores = evaluate(daily.loc[split.test], predictions)
    return dict(config=config, features=X, split=split, alpha=alpha, tuning=tuning,
                predictions=predictions, metrics=scores, audit=audit)


def save_results(daily, result, output, manifest, elapsed):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    days = result["split"].test
    actual = daily.loc[days]
    long = pd.DataFrame({"date": np.repeat(days.strftime("%Y-%m-%d"), 48),
                         "slot": np.tile(np.arange(1, 49), len(days)),
                         "actual": actual.to_numpy().ravel()})
    for name, pred in result["predictions"].items():
        long[name] = pred.to_numpy().ravel()
    long.to_csv(output / "predictions_full.csv", index=False)
    # A deterministic first week, not a hand-picked flattering interval.
    long.head(7 * 48).to_csv(output / "predictions_sample.csv", index=False)
    result["metrics"].to_csv(output / "metrics.csv", index=False)
    result["tuning"].to_csv(output / "validation_scores.csv", index=False)
    result["audit"].to_csv(output / "fit_audit.csv", index=False)
    daily_losses, slot_losses = [], []
    for name, pred in result["predictions"].items():
        abs_error = np.abs(pred.to_numpy() - actual.to_numpy())
        daily_losses.extend({"date": d.strftime("%Y-%m-%d"), "model": name, "mae": float(v)}
                            for d, v in zip(days, abs_error.mean(axis=1)))
        slot_losses.extend({"slot": s, "model": name, "mae": float(abs_error[:, s-1].mean()),
                            "q10": float(np.quantile(abs_error[:, s-1], .1)),
                            "median": float(np.median(abs_error[:, s-1])),
                            "q90": float(np.quantile(abs_error[:, s-1], .9))} for s in range(1, 49))
    pd.DataFrame(daily_losses).to_csv(output / "daily_mae.csv", index=False)
    slot_table = pd.DataFrame(slot_losses)
    slot_table.to_csv(output / "slot_errors.csv", index=False)
    source_root = Path(__file__).parent
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_root.glob("*.py"))}
    metadata = {"status": "executed_on_official_JEPX_CSV", "created_utc": datetime.now(timezone.utc).isoformat(),
                "target": "JEPX system price", "unit": "JPY/kWh", "timezone": "Asia/Tokyo",
                "config": asdict(result["config"]), "selected_alpha": result["alpha"],
                "data_start": str(daily.index[0].date()), "data_end": str(daily.index[-1].date()),
                "data_days": len(daily), "data_observations": int(daily.size),
                "initial_training_days": len(result["split"].train),
                "validation_days": len(result["split"].validation), "test_days": len(days),
                "feature_count": result["features"].shape[1], "elapsed_seconds": elapsed,
                "files": manifest, "source_sha256": source_hashes,
                "python": platform.python_version(),
                "versions": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scikit-learn", "matplotlib")},
                "assumptions": ["d-1 complete auction curve available before d auction",
                                "final historical CSV revisions not publication-time snapshots"],
                "inference": "descriptive comparison only; no statistical significance or profitability claim"}
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    plot_results(long, result["metrics"], slot_table, output / "figures")


def plot_results(long, scores, slot_table, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    colors = {"naive_previous_day": "#81909b", "naive_week": "#ad71a4",
              "naive_weekday": "#e0a130", "lear_lasso": "#007f86"}
    sample = long.head(7*48).copy()
    times = pd.to_datetime(sample.date) + pd.to_timedelta((sample.slot-1)*30, unit="min")
    fig, ax = plt.subplots(figsize=(12, 4.8), layout="constrained")
    ax.plot(times, sample.actual, label="Actual", color="#1b263b", linewidth=1.4)
    ax.plot(times, sample.lear_lasso, label="LEAR-style LASSO", color=colors["lear_lasso"], linewidth=1.1)
    ax.plot(times, sample.naive_weekday, label="Weekday naive", color=colors["naive_weekday"], alpha=.6, linewidth=.8)
    ax.set(title="JEPX system price | first test week (not selected by performance)", ylabel="JPY/kWh", xlabel="Delivery time (Asia/Tokyo)")
    ax.legend(ncol=3, frameon=False)
    fig.autofmt_xdate()
    fig.savefig(directory / "actual_vs_predicted.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    labels = [n.replace("naive_", "Naive: ").replace("_", " ") for n in scores.model]
    bars = ax.barh(labels, scores.mae, color=[colors[n] for n in scores.model])
    ax.bar_label(bars, fmt="%.3f", padding=4)
    ax.set_xlim(0, scores.mae.max()*1.18)
    ax.set(title="Same-period test MAE | lower is better", xlabel="MAE (JPY/kWh)")
    fig.savefig(directory / "model_mae.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    for name in colors:
        block = slot_table[slot_table.model == name]
        ax.plot(block.slot, block.mae, label=name, color=colors[name])
    block = slot_table[slot_table.model == "lear_lasso"]
    ax.fill_between(block.slot, block.q10, block.q90, color=colors["lear_lasso"], alpha=.13, label="LASSO 10–90% absolute error")
    ax.set(title="Error by delivery slot | shaded band is distribution, not confidence", xlabel="Half-hour slot (1 = 00:00–00:30 JST)", ylabel="Absolute error (JPY/kWh)")
    ax.legend(fontsize=8, ncol=2, frameon=False)
    fig.savefig(directory / "slot_errors.png", dpi=160)
    plt.close(fig)


def run_from_files(paths, config, output):
    started = time.perf_counter()
    daily, manifest = load_daily(paths)
    result = run_experiment(daily, config, progress=lambda s: print(s, flush=True))
    save_results(daily, result, output, manifest, time.perf_counter()-started)
    print(result["metrics"].to_string(index=False))
    return result
