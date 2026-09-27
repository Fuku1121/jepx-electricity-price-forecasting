# Stage 1 publication review

Reviewed locally on 2026-09-27; documentation refined for public review.
Repository: [Fuku1121/jepx-electricity-price-forecasting](https://github.com/Fuku1121/jepx-electricity-price-forecasting).
Hosted test status is available in [Actions](https://github.com/Fuku1121/jepx-electricity-price-forecasting/actions).

- Literature: published paper sections on features, LEAR, calibration and evaluation
  checked; explicit Paper / This implementation distinctions documented.
- Implementation provenance: No third-party forecasting repository source code was intentionally used as an implementation reference or copied during this project.
  This describes intentional project activity, not a proof about AI training provenance.
- Tests: 25 pytest cases passed, using synthetic fixtures only; module imports passed.
- Leakage: feature and prediction mutation tests include the forecast day's actuals;
  unknown-target inference works; tuning receives only the pre-test prefix.
- Data integrity: three official fiscal-year CSVs, complete 48-slot contiguous days,
  no duplicates, gaps or nonfinite values. No interpolation or spike deletion.
- Real results: one executed main experiment. Full local predictions independently
  reproduce MAE/RMSE/rMAE, daily MAE aggregates and committed first-week sample.
- Dates: all 365 fitting-audit rows end before their forecast day; selected alpha is fixed.
- Provenance: recorded raw-file and source-code SHA-256 hashes match local files.
- Figures: all three generated figures visually inspected for readable labels and data.
- Rights: official JEPX attribution/use page checked; raw/processed data and full
  predictions excluded from Git; source attribution and separate data rights documented.
- Claims: no significance, profitability, full-reproduction or unaided-authorship claim.
- Links: local Markdown destinations checked. External scholarly/JEPX/documentation
  destinations were read during the task; website availability may subsequently change.
- Public scope: only the independent repository; existing fx-ml-trading untouched.

## Separate privacy checks

The earlier review did not establish the identity fields in the published Git
objects. Its statement that the initial public commit used a noreply identity was
incorrect and has been withdrawn.

- **Current files:** checked separately for credential/key patterns, personal
  contact information and local absolute paths. No matching private-data payload
  was detected in the tracked file contents.
- **Historical file contents:** the two published commits' tracked file contents
  and patches were reviewed separately from their author/committer headers.
- **Commit metadata:** both initially published commits contained a personal
  Gmail address in both Author and Committer email fields. The address is not
  reproduced in this document. After explicit owner approval, those two commits
  were reconstructed with the verified noreply email in both identity fields.
  Their trees, messages, names, timestamps and parent ordering were preserved.
  This documentation commit follows the corrected history.

GitHub Settings > Emails was inspected to verify the exact noreply identity:
`325605192+Fuku1121@users.noreply.github.com`. Repository-local Git configuration
uses that verified identity. GitHub's "Keep my email addresses private" setting
was also enabled with owner approval. Configuration alone does not alter earlier commits.

The original history was saved in a verified local-only Git bundle before
reconstruction; that backup must never be pushed. The corrected original commits
are `00839274a02905a43dfd14c3343cdb9a07d4e605` and
`6e9103ce9975bdd039eb6dec8314e680006a5089`. Their trees match their originals.
Publication requires a guarded update of main, followed by a fresh audit of
current files, historical file contents and all reachable published identity fields. Old commit URLs, caches
and other clones may still retain the original objects; a branch rewrite alone
cannot establish complete removal from GitHub storage or third parties.

These are pattern/manual checks, not a guarantee that no possible secret exists.
Raw data, virtual environments, notebooks and full-series predictions remain
excluded from the repository. Research code, experiment configuration, metrics,
figures and test expectations are unchanged by this documentation review.

Run commands and exact numerical evidence are documented in the README and results
metadata. Review the public Actions run after publishing; local checks cannot
substitute for a claim that hosted CI actually ran.


## Stage 2 extension review

The historical review above describes the Stage 1 publication and metadata correction.
Stage 2 adds a forecast-driven battery MILP and backtest without changing any original
forecasting module, test expectation or Stage 1 result artifact. Its method and executed
results are in [Battery optimization](BATTERY_OPTIMIZATION.md) and
[Battery results](BATTERY_RESULTS.md). All six predeclared battery scenarios are reported;
there is no test-return-based parameter selection or new forecasting model.

The local suite now contains 52 passing cases, including the original 25. Battery tests
cover physical constraints, binary exclusivity, unit conversion, solver failures,
forecast/actual separation and an actual-price mutation test. Full base schedules were
independently audited and daily cashflows recomputed. CI evidence must be checked on
the published branch/merge commit in Actions; this text does not substitute for it.

Public battery data consist of derived summaries and the first chronological week of
schedules. Full-series schedules and full predictions stay Git-ignored. The same JEPX
attribution and data-rights exclusions apply. This extension uses ordinary commits on
battery-optimization, with no history rewrite or force push.
