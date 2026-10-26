# Final feature map

| ESS 2.0 capability | Web 3.0 implementation | Verification |
|---|---|---|
| 17 pages, five navigation groups | React Router, original labels and design tokens | React render tests |
| Six engineering overview KPIs, disposition, risk | Computed from immutable screening rows; worst severity per component | Build/component checks; browser acceptance pending |
| Dataset upload, mapping, units, preview, explicit commit | Multipart Express route → preserved ingest/quality services | Invalid uploads tested; bridge input validation tested |
| SQLite catalog and local artifacts | MongoDB ObjectIds, Mongoose/PyMongo, retained CSV/joblib files | Adapter tested with mock; real Mongo blocked |
| Batch selection, comparison, rename/archive/delete | Shared batch context, descriptive comparison table, validated CRUD/safe deletion | Validation tests; CRUD suite pending real Mongo |
| Screening/anomaly/drift/risk/explanations | Original ess/risk and anomaly modules unchanged | Original suite + bridge tests |
| Component trajectory/review/report | React charts, API review upsert, original report generator | Python report/review tests; browser pending |
| Predictions and model support/intervals | Original predict function, actual model selection | Actual Python tests |
| Training, candidate choice, explicit activation | Original train function, model catalog + activation | Actual Python tests |
| Evaluation/importances | Held-out comparison/test rows, regression scatter, importance table | Original suite + adapter tests |
| Scenarios | Original five recipes + configurable populations; retained pair/disposition comparison | Actual Python tests |
| Policy preview/versioning | Original Policy validation and before/after screen | Actual Python tests |
| Reports | Six original report purposes, PDF/XLSX/CSV, component report | Actual Python export tests |
| Audit and diagnostics | Append-only API, Mongo catalog, runtime and smoke views | API protections + Python tests |
| Settings/reset/backup | Persistent name, non-destructive demo creation, catalog/artifact ZIP | Bridge backup tested |
| SQLite import | Read-only source utility, ObjectId map and artifact copies | Implemented; real migration acceptance pending |

Functional alternatives: Streamlit multiselect column mapping becomes explicit JSON mapping and preview; batch comparison is a descriptive table; report generation uses the original report service; Python runs as a bounded internal process rather than a publicly exposed service. No generic CRUD replacement or hardcoded model scores are used.

Remaining gaps are recorded in TEST_REPORT.md. The final package deliberately does not claim quantified visual parity, verified Mongo persistence, complete production hardening or online deployment.
