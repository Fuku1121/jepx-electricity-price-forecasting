# JEPX data: acquisition, attribution and non-redistribution

Source: **Japan Electric Power Exchange (JEPX)**,
[Spot market / 約定価格・入札・約定量](https://www.jepx.jp/electricpower/market-data/spot/).
Target: **システムプライス(円/kWh)**. Other price/volume columns are ignored.
Data are delivery-day auction prices, not actual real-time prices.

## Manual route (no automated download required)

1. Open the official page above; choose 約定価格・入札・約定量.
2. Click データダウンロード and select the fiscal year (年度).
3. Download **2022年度**, **2023年度**, **2024年度**.
4. Save under `data/raw/` as `spot_summary_2022.csv`,
   `spot_summary_2023.csv`, `spot_summary_2024.csv`. If a browser renames a download,
   rename it to match. Do not put index, bid-curve or price-sensitivity CSVs here.
5. Fiscal 2022 means 2022-04-01–2023-03-31, not calendar 2022.
6. Run `python scripts/download_or_prepare_data.py` to validate and prepare.

The official file schema contains 受渡日, 時刻コード (1..48), and
システムプライス(円/kWh). UTF-8 BOM and CP932 are supported. No JEPX credentials,
API subscription, or trading account are needed for these public CSVs.

## Optional automated route

```bash
python scripts/download_or_prepare_data.py --download-years 2022 2023 2024
```

The script submits the same public download form observed on 2026-09-27:
`POST https://www.jepx.jp/_download.php`, form `dir=spot_summary` and
`file=spot_summary_YYYY.csv`, with the official spot page as Referer.
This is a convenience wrapper around three explicit annual downloads, not a crawler.
It skips existing files, pauses between requests, and does not bypass login,
CAPTCHA, or access restrictions. A blank/error response is not accepted as data;
use the manual route if the site changes. Existing files are validated rather than
silently overwritten. A `.part` file after failure may be inspected/removed locally.

## Use conditions reviewed 2026-09-27

[JEPX disclaimer/copyright](https://www.jepx.jp/disclaimer/) identifies JEPX as
copyright owner and asks users to identify the source; it notes content/conditions
can change. This project does not interpret that as an unrestricted open-data license.
Raw CSVs and the complete processed series are excluded from Git. The MIT license
applies to original code/documentation, not JEPX data. Derived figures/metrics and a
short first-week sample are attributed to JEPX in the README and results notes.
Check the current terms before other uses or bulk redistribution.

## Provenance

`results/acquisition.json` records the executed download requests and UTC retrieval
times. `results/run_metadata.json` records each raw filename, SHA-256 hash, size,
row count and source page. `data/processed/manifest.json` is a local validation
manifest. Re-downloads can differ if JEPX revises its historical archive.
The source files do not include a historical publication-time/version snapshot;
this limits strict as-of replication.

`raw/`, `processed/` and full predictions are Git-ignored. Synthetic unit-test
fixtures are generated in tests and never presented as market observations.
