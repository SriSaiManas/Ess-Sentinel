# Source audit and preservation checklist
Original archive is unchanged. source-inventory.json records all 119 source archive members, hashes, and Python symbols. Original source, tests, UI and historical evidence are retained under ml-service/legacy; historical test evidence is NOT a Web 3.0 test result.

Architecture: Streamlit pages → Workspace → SQLite Store + immutable CSV/joblib artifacts. Existing catalog entities: batches, models, policies, runs, events, reviews, settings. No redundant anomaly collection: parameter-level results belong to immutable run CSVs. MongoDB replaces catalog operations, retaining artifact storage outside the database. ObjectId strings are used as artifact directory names; references are ObjectIds in MongoDB.

Visual reference: original ui/theme.py and evidence/screenshots. Navy #0d1422/#111c2e, teal #36d6c5, gray #96a6bc, borders #23324a; severity green/yellow/orange/red. Retain five navigation groups and 17 page labels, metric grid, charts, batch context and dense tables.

Preservation targets (verify against final TEST_REPORT):
- COMMAND: Overview, Live Operations, Batch Explorer — retained catalog and measured result views.
- ENGINEERING: Data Ingestion (CSV/XLSX, mapping, explicit units, preview/commit), Data Quality (row findings), Screening (stage/model/policy), Anomaly Analysis (observed versus predicted), Component Explorer (trajectory/review).
- INTELLIGENCE: Predictive Analytics, Model Laboratory (lot-disjoint splits/candidates/activation), Scenario Simulator (five fixed + configurable recipes), Model Evaluation.
- GOVERNANCE: Policy Center (validate/preview/version), Audit Trail (append-only API), Reports & Exports (six types, PDF/XLSX/CSV).
- SYSTEM: Settings (persistent preferences/non-destructive demo reset), System Diagnostics, backups.

Algorithms retained: robust median/MAD population and temporal statistics; Isolation Forest; regression candidate selection, calibration and held-out evaluation; engineering risk rules and explanations. Target and future values excluded at cutoff. Synthetic data is labeled. Predictions are not failure probabilities.

Risks: serialized models require matching dependency versions; retrain under supported local environment if loading fails. Windows execution and Atlas deployment need separate verification. Multi-process operations need bounded concurrency; artifacts and MongoDB must be backed up together. No live industrial telemetry exists in 2.0 and none is fabricated here.
