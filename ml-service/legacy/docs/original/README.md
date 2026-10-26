# ESS Sentinel
## Explainable Predictive Environmental Stress Screening Platform

A working local Python/Streamlit engineering prototype for the supplied ESS/Burn-In problem. It detects population-relative anomalies and temporal drift, predicts 168h measurements from early observations, and generates review recommendations. **It is not an ISRO-validated product or a release/qualification system.** All included measurements and demonstrated performance are synthetic.

## Start on Windows

1. Install **Python 3.12**, including the Python launcher. Extract the entire ZIP.
2. Double-click `setup_windows.bat` (internet required once for dependencies).
3. Double-click `run_windows.bat`.
4. Open **http://localhost:8501**. The app includes a synthetic batch and trained demonstration models.
5. Select **Screen current batch**, or choose **Demo Mode → Latent Defect → Run scenario**.

Windows launch scripts are provided; execution was tested on Linux, not on a Windows machine. Do not move individual source files out of the extracted folder.

## Start on Linux/macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Alternatively, run `./run.sh` with Python 3.12 available. Close the terminal with Ctrl+C to stop. The default bind address is loopback; no public deployment or user authentication is enabled.

## Included modules

```text
ess_platform/
  app.py                     14-page engineering workbench
  ess/
    data/                    CSV/XLSX validation and synthetic generator
    features/                as-of features and temporal measurements
    anomaly/                 robust peer distributions
    prediction/              model selection, inference and metrics
    risk/                    transparent score and review overrides
    explainability/          human-readable reasons
    reports/                 PDF and spreadsheet-safe CSV
    ui/                      Plotly trajectory charts
    config.py                validated configurable policy
    audit.py                 SQLite event log
    cli.py                   reproducible demo and benchmarks
  config/                    default engineering policy
  data/example_synthetic.csv 2,000 components, 6,000 parameter records
  models/demo/               trained models, manifest, metrics, predictions
  tests/                     unit, integration, widget E2E and HTTP launch tests
  evidence/                  actual test logs, metrics, benchmarks, sample reports
  docs/                      architecture graphic and demonstration workflow
```

## Dataset contract

One row is one component/parameter/session/condition measurement series. Component IDs must be globally unique across lots for training. Multiple parameters or sessions per component are supported. The lot split keeps all those records together.

| Field | Requirement |
|---|---|
| component_id, lot_id, parameter, unit | Required identifiers; units consistent within a parameter |
| value_0h, value_24h | Required columns; missing values accepted for review but prediction withheld |
| value_96h | Optional for 24h model; required for a 96h prediction |
| value_168h | Required to train/evaluate regression; excluded from all prediction features |
| spec_min, spec_max | Required finite numeric specification limits; max > min |
| part_family, session_id | Optional, explicit defaults shown as warnings |
| temperature, voltage | Optional, defaults 25 °C and 3.3 V shown as warnings |
| defect_label | Optional binary ground truth, never an input feature |
| defect_type, true_future_value, synthetic | Optional generator provenance, excluded from features |

Column mapping is available on Data Import. Convert units before import; the app deliberately does not guess conversions. Signed quantities are supported when spec_min is negative. Measurement columns must be named `value_<nonnegative integer>h`. The screening UI uses 0/24/96/168h; generator exports may additionally contain 48/72/120h for inspection, not model inputs.

## Methodology

* Comparable peers share lot, family, parameter, unit, temperature, voltage and session. Median/MAD, robust Z, quartiles, percentiles, relative drift, slopes and acceleration are calculated at the selected stage. Small cohorts are sent to review.
* Isolation Forest is trained without labels on early features, separately by parameter. Its empirical training-reference percentile is an anomaly score, not a defect probability.
* Linear, two Ridge, Random Forest and two Gradient Boosting configurations compete on validation MAE. The winner is selected separately per parameter, preserving units.
* Independent lots form train/validation/calibration/test sets. The feature whitelist excludes future readings and truth labels. Exact cross-lot measurement duplicates block training pending review.
* A separate calibration partition supplies residual intervals. Because components within lots are dependent, these are approximate intervals without a lot-level coverage guarantee. Unseen input ranges suppress intervals and trigger review.
* Additive evidence points and explicit conservative overrides produce NORMAL/WATCH/HIGH RISK/CRITICAL recommendations. A NORMAL result is not proof of fitness. See MODEL_CARD.md for limitations and actual results.

## Reproduce training and benchmarks

```bash
python -m ess.cli demo
python -m ess.cli benchmark
python -m pytest -q --cov=ess --cov=app --cov-report=term-missing
```

The demo command regenerates the example dataset, trains every candidate, persists the selected models and exports reports/metrics. It overwrites those generated demonstration files. Training requires at least eight independent lots and sufficient complete records per split. GUI training saves to `models/current`; bundled demonstration models remain separate. The GUI automatically selects the best validation model; test metrics do not influence selection.

## GUI workflow

Generate/import → validate → train → screen → inspect → export. Changing the dataset, stage, model or policy invalidates the previous screening view. Dashboard counts use unique component IDs with the worst parameter/session status. Tables, classification metrics and predicted-crossing counts are record-level and labeled accordingly. Official data can replace synthetic data through the same import path.

## Reports and audit

PDF: per-component engineering detail and batch summary. CSV: full results, filtered results and audit events. SQLite records uploads, training/model versions, policies, screening hashes, component analysis and report generation. The audit is local and transactional, **not tamper-proof or compliance-certified**. Exported rows include dataset and policy hashes, model version, stage and timestamp.

## Deployment

For an isolated container: `docker build -t ess-sentinel .` then `docker run --rm -p 127.0.0.1:8501:8501 ess-sentinel`. This Docker recipe is supplied but was not built in this environment. Production deployment needs authentication, authorization, durable per-user storage, backups, audit protection and workload limits. Current application is single-user and local. No credentials are embedded. Uploaded files are parsed only; uploaded serialized models are not supported. Load joblib models only from trusted local sources.

## Documentation

* ARCHITECTURE.md — data flow and assumptions
* MODEL_CARD.md — evidence, evaluation and model limitations
* TEST_REPORT.md — executed checks, coverage, measured performance and unresolved checks
* USER_GUIDE.md — step-by-step operation
* docs/DEMO_5_MINUTES.md — judge-facing demonstration
* docs/architecture.svg — standalone architecture figure

## Future work

Validate on real burn-in data; calibrate device-specific thresholds; assess leave-one-family-out transfer; add lot-aware uncertainty; quantify sensitivity by defect mechanism; qualify units/conditions; add drift monitoring and protected human disposition workflows. Sudden failures with no early signal cannot reliably be inferred from 0/24h values.
