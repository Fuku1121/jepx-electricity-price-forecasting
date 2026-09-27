# Repository and maintenance

Public repository: [Fuku1121/jepx-electricity-price-forecasting](https://github.com/Fuku1121/jepx-electricity-price-forecasting).

This is an independent repository. The existing fx-ml-trading repository is outside
its scope. The original local research commit is retained in local Git history.

## Updating the project

```bash
git clone https://github.com/Fuku1121/jepx-electricity-price-forecasting.git
cd jepx-electricity-price-forecasting
python -m pip install -r requirements.txt
python -m pytest -q
```

Make changes on a branch, review the diff and open a pull request. Check the hosted
[Actions results](https://github.com/Fuku1121/jepx-electricity-price-forecasting/actions)
before merging. Use normal GitHub authentication; do not put tokens in remote URLs,
source files or committed configuration.

Before publishing new experiments, check data attribution, excluded raw/full-series
files, date alignment, information availability and reported metrics. Keep the
original test results traceable; do not silently overwrite evidence after tuning
on the same test period. See [release review](RELEASE_REVIEW.md).

The downloadable archive contains tracked files only and excludes Git history,
raw/processed data and full local predictions. Clone the public repository for
future development.
