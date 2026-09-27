"""Strict official-CSV ingestion; never fill missing prices from the future."""
from pathlib import Path
import hashlib
import io
import unicodedata

import numpy as np
import pandas as pd

SOURCE = "https://www.jepx.jp/electricpower/market-data/spot/"


def read_official_csv(path: str | Path) -> pd.DataFrame:
    blob = Path(path).read_bytes()
    frame = None
    for encoding in ("utf-8-sig", "cp932"):
        try:
            frame = pd.read_csv(io.StringIO(blob.decode(encoding)))
            break
        except UnicodeDecodeError:
            continue
    if frame is None:
        raise ValueError(f"Unsupported CSV encoding: {Path(path).name}")
    frame.columns = [unicodedata.normalize("NFKC", str(c)).strip() for c in frame.columns]
    columns = {"受渡日": "date", "時刻コード": "slot", "システムプライス(円/kWh)": "price"}
    if not set(columns).issubset(frame.columns):
        raise ValueError("Expected official JEPX delivery-date, slot and system-price columns")
    out = frame[list(columns)].rename(columns=columns)
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    if out["date"].isna().any() or not out["date"].eq(out["date"].dt.normalize()).all():
        raise ValueError("Delivery dates must be nonmissing calendar dates")
    out["slot"] = pd.to_numeric(out["slot"], errors="raise")
    if not out["slot"].isin(range(1, 49)).all():
        raise ValueError("Slots must be integers 1..48")
    out["slot"] = out["slot"].astype(int)
    out["price"] = pd.to_numeric(out["price"], errors="raise")
    if not np.isfinite(out["price"]).all():
        raise ValueError("Missing or nonfinite prices")
    return out


def validate_daily(daily: pd.DataFrame, allow_missing: bool = False) -> None:
    if daily.empty or not isinstance(daily.index, pd.DatetimeIndex):
        raise ValueError("Expected a nonempty daily DatetimeIndex")
    if daily.index.tz is not None or not daily.index.equals(daily.index.normalize()):
        raise ValueError("Use timezone-naive delivery dates interpreted as Asia/Tokyo")
    expected = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    if not daily.index.equals(expected) or daily.index.has_duplicates:
        raise ValueError("Delivery dates must be sorted, unique and contiguous")
    if list(daily.columns) != list(range(1, 49)):
        raise ValueError("Each day must have ordered slots 1..48")
    values = daily.to_numpy(dtype=float)
    if np.isinf(values).any() or (not allow_missing and np.isnan(values).any()):
        raise ValueError("Missing or nonfinite prices")


def load_daily(paths: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    if not paths:
        raise ValueError("No CSVs found. See data/README.md for official download instructions.")
    frames, manifest = [], []
    for path in sorted(paths):
        frame = read_official_csv(path)
        frames.append(frame)
        manifest.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "bytes": path.stat().st_size, "rows": len(frame), "source": SOURCE})
    rows = pd.concat(frames, ignore_index=True)
    if rows.duplicated(["date", "slot"]).any():
        raise ValueError("Duplicate delivery date/slot, including overlapping files")
    daily = rows.pivot(index="date", columns="slot", values="price").sort_index()
    validate_daily(daily)
    return daily, manifest
