# Executed test report

## Result

* Total: **35**
* Passed: **35**
* Failed: **0**
* Errors: **0**
* Skipped: **0**
* Measured statement coverage: **90.29%** (735/814 lines)

Executed with pytest and pytest-cov in a freshly created Python 3.12 virtual environment. Dependencies were actually installed. Tests were rerun after discovered defects were repaired. The raw final console log is `evidence/test_run.txt`, JUnit results are `evidence/tests.xml`, and coverage is `evidence/coverage.json`. Separate demo/benchmark commands were executed but are not included in the pytest coverage percentage.

## Executed scope

| Area | Evidence |
|---|---|
| Ingestion | CSV and XLSX parsing; malformed/unsupported/empty input; column mapping |
| Validation | Missing columns/measurements, numerical errors, infinities, negative values, units, time-column syntax, duplicate identities, cross-lot duplicate signatures |
| Features | Drift/percentage/slope mathematics; future/label perturbation invariance |
| Anomalies | Obvious outlier, population anomaly below specification, latent drift, normal comparison |
| Regression | Training and inference; lot-disjoint splits; 24h and 96h models; missing inputs; unseen parameters/ranges; independent per-parameter model state |
| Risk | Policy validation, actual/static overrides, configurable thresholds, explanations, incomplete assessment handling |
| Integration | Ingest → validate → saved model → screen → evaluate → explanation → CSV/PDF → audit |
| GUI end-to-end | Streamlit AppTest launches app, generates synthetic data, trains, screens, visits all major pages, opens component report, generates batch report and runs Early Warning |
| Live server | Subprocess launch; HTTP readiness endpoint returns 200 and root HTML is served; process shut down cleanly |
| Reports | PDF header assertions plus visual inspection of all three component-report pages and batch-report page |
| Performance | Actual 1k, 10k and 100k screening runs |

## Bugs discovered and repaired

1. A shared scikit-learn estimator instance caused parameter models to overwrite each other's fitted state. Candidate estimators are now cloned per parameter. A regression test asserts persisted test predictions equal fresh inference and that estimator object identities differ.
2. The UI test initially resolved app.py relative to the tests folder. It now uses the resolved project entrypoint.
3. Process RSS reporting was not reliable in the execution host and sometimes raised NoSuchProcess. Benchmarks now explicitly leave RSS unavailable and measure dataframe storage instead. No claim of total process memory is made.

## Measured performance

One parameter (Leakage current), 20 lots, seed 42; component count equals record count. Timing is one run, not a service SLA. Screening time includes schema checking, robust cohort statistics, model inference, risk computation and explanations. It excludes GUI rendering and report downloads. CSV generation is outside loading time. The 100k benchmark is direct CLI parsing; the GUI retains its 25 MB upload cap.

| Components | CSV load (s) | Preprocess (s) | Screen (s) | Dataframe storage (MiB) |
|---|---:|---:|---:|---:|
| 1,000 | 0.004 | 0.026 | 0.139 | 1.02 |
| 10,000 | 0.027 | 0.034 | 0.652 | 10.21 |
| 100,000 | 0.158 | 0.110 | 4.761 | 102.07 |

Dataframe memory uses pandas deep memory accounting for input plus output. It is not peak RSS, excludes model/native/temporary allocations, and may count shared values more than once. Raw timings and environment details are in evidence/benchmark.json.

## Unresolved verification limits

* A full browser automation pass could not run: Playwright installed, but Chromium download repeatedly returned an invalid/truncated archive. AppTest exercises actual Streamlit scripts/widgets, not browser pixels, file-picker behavior or download clicks. Import parsing/mapping and exported bytes are verified through integration tests, not a browser upload/download round trip. Browser visual polish and click-through acceptance remain to be checked on the user's machine.
* Linux/Python 3.12 was tested. Windows helper scripts and Docker recipe were not executed on those platforms.
* Total process/peak memory could not be measured reliably in this host. Dataframe storage is reported transparently.
* No real-data accuracy, calibration, device qualification or security certification was performed.

Therefore this is a tested functional local prototype, **not a claim that every production/competition acceptance gate is closed**. No known failure remains in the executed suite. No skipped test is being used to hide the browser limitation; that verification was outside the completed suite and is disclosed here.

## Clean start and reproducibility

A fresh virtual environment was created with `python -m venv .venv`; requirements were installed and pinned. A real application server launch passed the HTTP check. The full source archive excludes the virtual environment: install dependencies using setup_windows.bat or the README commands. It is not an offline standalone executable.

## Assumptions

Component IDs are globally unique across lots; each row is a parameter/session/condition series. Unknown conditions use warned defaults. Synthetic ground truth is injected mechanism truth. Default thresholds are illustrative; no failure rate or industrial limit is assumed. Final disposition requires human engineering review.
