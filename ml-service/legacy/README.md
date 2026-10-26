# ESS Sentinel 2.0

**Engineering Screening & Surveillance Intelligence Platform**

A separate, fully local redesign of the original ESS Sentinel application. The original anomaly/risk semantics and 168h prediction task are retained. A new persistent workspace and 17 functional pages support batch management, validated imports, engineering review, model registration, policy simulation, and reports.

**Target:** your existing **Python 3.14.6 on Windows 11, 64-bit**. No second Python installation is required. Python 3.14.6 runtime tests were executed on Linux; Windows x64 dependency wheels were resolved/downloaded. A physical Windows 11 run is not claimed. See `docs/testing.md` for the exact verification boundary.

## Windows quick start

Extract the entire ZIP. Open Command Prompt in the extracted `ESS_Sentinel_2.0` directory:

```bat
setup_windows.bat
run_windows.bat
```

Open **http://localhost:8501**. Setup needs internet access once. After dependencies are installed, the app, charts, generation, training, predictions, reports and fonts work locally without internet. No dataset is sent to an external service.

If the Python launcher is unavailable, setup tries your active `python` only when it is Python 3.14. To specify your existing interpreter:

```bat
set "ESS_PYTHON=C:\Path\To\Your\Python314\python.exe"
setup_windows.bat
```

Replace the path with your actual Python executable. Setup checks an existing `.venv` rather than overwriting it. It never replaces your system Python installation.

Manual equivalent:

```bat
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m streamlit run app.py
```

Stop the server with Ctrl+C. Launch and test scripts preserve their exit status and keep the terminal visible.

## First use

On first launch, the app imports the bundled synthetic reference batch, registers the trusted demonstration model and performs a real initial screening. These are recorded operations, not invented dashboard history. Subsequent launches reload the local catalog.

1. **Overview:** inspect the current batch and priority findings.
2. **Screening:** choose the stage and run model-assisted or statistics-only screening.
3. **Component Explorer:** inspect a trajectory, distinguish observation from prediction, and save a review note.
4. **Reports & Exports:** preview the sections, generate files, and download PDF/Excel/CSV.
5. **Scenario Simulator:** compare a synthetic baseline with latent defects or missing measurements.

All included data and demonstration performance are synthetic. This is engineering decision support, not hardware qualification or a validated industrial release system.

## Navigation

| Group | Implemented pages |
|---|---|
| Command | Overview, Live Operations, Batch Explorer |
| Engineering | Data Ingestion, Data Quality, Screening, Anomaly Analysis, Component Explorer |
| Intelligence | Predictive Analytics, Model Laboratory, Scenario Simulator, Model Evaluation |
| Governance | Policy Center, Audit Trail, Reports & Exports |
| System | Settings, System Diagnostics |

Live Operations means local stored batch activity. No live telemetry, background queue, cloud connection or multi-user identity is fabricated.

## Project structure

```text
ESS_Sentinel_2.0/
  app.py                     application shell and shared batch context
  ess/                       preserved ML, statistics, risk and baseline reports
  services/                  workspace orchestration, catalog, diagnostics, reports
  ui/
    theme.py                 custom design tokens and chart styling
    common.py                bounded tables, caching and shared UI actions
    navigation.py            17 functional routes in five groups
    pages/                   command, engineering, intelligence, governance, system
  assets/                    wordmark and licensed bundled PDF fonts
  config/                    original illustrative engineering policy
  .streamlit/config.toml     centralized offline dark theme
  data/                      original reference and timestamped sample CSV
  models/demo/               trusted original demonstration models and metrics
  outputs/                   runtime workspace, created on first launch
  tests/                     preserved backend tests + expanded service/UI tests
  tools/                     reproducible report and optional browser verification
  evidence/                  executed test results, wheel audit, screenshots, exports
  docs/                      architecture, guide, model card, testing, preservation map
  requirements.txt           exact dependency pins checked for CPython 3.14
  setup_windows.bat
  run_windows.bat
  test_windows.bat
```

## Data contract

A row represents a component / parameter / session / operating-condition series. Multiple parameters and sessions are supported. Component IDs must be globally unique across lots for training and component-level summaries.

Required: `component_id`, `lot_id`, `parameter`, `unit`, `value_0h`, `value_24h`, `spec_min`, `spec_max`.

Optional metadata: `part_family`, `session_id`, `temperature`, `voltage`. Explicit inherited defaults are warned in the preview. Optional measurements: `value_96h`, `value_168h`; 168h targets are needed for training, not for inference. Optional binary ground truth: `defect_label`. Optional acquisition timestamps: `timestamp_0h`, `timestamp_24h`, `timestamp_96h`, `timestamp_168h` in ISO 8601 format.

The import flow previews column mappings and optional unit assignments. Unit assignment **labels** values; it never performs a numeric unit conversion. Convert engineering units before importing. Raw upload bytes, normalized data, hashes and transformation metadata are retained separately. Missing values are not silently replaced with plausible observations. Missing early inputs withhold predictions and require review.

## Training and engineering behavior

The 24h feature whitelist uses only 0h/24h data and supported metadata. The optional 96h model adds 96h features. No target or defect label is an input. Lots are separated into training, validation, calibration and test sets. Model Laboratory exposes the supported candidate set, random seed, forest tree count and boosting-stage count. The linear baseline remains included. Validation MAE selects a winner per parameter. A successful new model is registered; **activation requires explicit confirmation**.

All original policy point weights and category overrides are retained. Absolute breaches, population/temporal anomalies and predicted safety crossings remain separate evidence. Policy Center validates a draft, shows changed settings, computes before/after decisions on the same batch, and requires confirmation before saving. Historical runs retain their original policy/model identifiers.

## Persistence, backup and limits

Default data directory: `outputs/workspace`. Override before launch with `set ESS_DATA_DIR=D:\ESS_Workspace`. `.env.example` documents optional variables; it is not automatically loaded.

SQLite schema version 1 stores batches, model registrations, policies, runs, reviews, settings and audit. Dataset/run writes are atomic. Model artifacts become visible only after successful persistence. Historical results remain immutable through the UI. Review states are annotations, not disposition overrides. Backups are generated through Settings. Demo reset creates a new synthetic batch without deleting prior imports or audit.

Limits: 25 MB uploaded file, 128 MB expanded XLSX, 300,000 measurement records per batch, 5,000 row-level issue details, 50 displayed table rows per page. Missingness chart shows first 200 records; other charts use aggregates or one selected series. Quality PDF limits are displayed before generation. Large training is synchronous and can take time; progress reflects completed fits/stages, not estimated percentages from timers.

## Tests

```bat
test_windows.bat
```

Or:

```bat
.venv\Scripts\python.exe -m pytest -q --cov=ess --cov=services --cov=ui --cov=app
```

Optional browser test (not required to operate the application):

```bat
.venv\Scripts\python.exe -m pip install playwright==1.63.0
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tools\browser_verify.py
```

Run tests from the project directory. UI and browser tests use isolated temporary catalogs, not the normal saved workspace. `python tools/generate_evidence.py` regenerates demonstration report files from actual computations.

## Documentation and remaining boundaries

Read `docs/user_guide.md`, `docs/architecture.md`, `docs/model_card.md`, `docs/testing.md`, `docs/feature_preservation.md` and `docs/demo_workflow.md`. Genuine screenshots are in `evidence/screenshots` and sample generated PDFs/XLSX in `evidence/reports`.

Not provided: industrial qualification, real ISRO measurements, physical telemetry ingestion, authentication/roles, tamper-proof audit, automatic hardware release, installer executable, signed deployment or guarantees of prediction coverage. The application binds to localhost by default. Do not expose it as a public multi-user service without a separate security design.
