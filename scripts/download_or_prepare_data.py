"""Validate local CSVs or fetch requested fiscal years through the public form."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
from jepx_forecasting.data import load_daily, read_official_csv, SOURCE


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--download-years", nargs="+", type=int,
                   help="Optional: explicit years only, one request per file; no retries")
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--processed", type=Path, default=Path("data/processed/daily.csv"))
    args = p.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    acquisition = []
    for year in args.download_years or []:
        if year < 2005 or year > datetime.now().year:
            raise ValueError("Invalid fiscal year")
        target = args.raw_dir / f"spot_summary_{year}.csv"
        if target.exists():
            print(f"Keeping existing {target.name}")
            continue
        payload = {"dir": "spot_summary", "file": target.name}
        request = urllib.request.Request("https://www.jepx.jp/_download.php",
                   data=urllib.parse.urlencode(payload).encode(),
                   headers={"Referer": SOURCE, "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=60) as response:
            blob = response.read()
        if not blob or b"<html" in blob[:500].lower():
            raise RuntimeError("No CSV returned. Use manual download described in data/README.md.")
        temporary = target.with_suffix(".csv.part")
        temporary.write_bytes(blob)
        read_official_csv(temporary)  # validate before promoting to a raw input
        temporary.rename(target)
        acquisition.append({"file": target.name, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                            "endpoint": request.full_url, "method": "POST", "form": payload})
        time.sleep(1)
    daily, manifest = load_daily(list(args.raw_dir.glob("*.csv")))
    args.processed.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(args.processed)
    (args.processed.parent / "manifest.json").write_text(json.dumps({"files": manifest, "acquisition": acquisition}, indent=2), encoding="utf-8")
    print(f"Validated {len(daily)} days / {daily.size} observations; {daily.index[0].date()} to {daily.index[-1].date()}")


if __name__ == "__main__":
    main()
