"""Run after `python -m pip install -e .[dev]` from the repository root."""
import argparse
from pathlib import Path
from jepx_forecasting.pipeline import Config, run_from_files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--output", type=Path, default=Path("results"))
    p.add_argument("--validation-start", default="2024-01-01")
    p.add_argument("--test-start", default="2024-04-01")
    p.add_argument("--test-end", default="2025-03-31")
    p.add_argument("--alphas", nargs="+", type=float, default=[.03, .1, .3, 1.])
    p.add_argument("--min-train-days", type=int, default=56)
    p.add_argument("--window-days", type=int)
    args = p.parse_args()
    config = Config(args.validation_start, args.test_start, args.test_end,
                    tuple(args.alphas), args.min_train_days, args.window_days)
    run_from_files(list(args.raw_dir.glob("*.csv")), config, args.output)


if __name__ == "__main__":
    main()
