# User guide

## Workspace and navigation

The sidebar groups 17 pages into Command, Engineering, Intelligence, Governance and System. The header's Active batch selector applies consistently across pages. Select “No active batch” to clear it. The batch panel shows actual import and screening timestamps; LOCAL / DEMO marks synthetic data. A model's presence does not mean it is qualified for the active device family.

## Import a real dataset

Open Data Ingestion. Choose CSV/XLSX under 25 MB. Preview source rows/types; map each source column once. Missing required mappings appear as blocking findings. Optionally assign unit labels, after independently verifying that the numerical values already use those units. Inspect normalized preview and row-level findings. Enter a batch name, confirm mappings/units, and click Commit dataset. The raw original file is retained alongside normalized data; no invalid row is silently deleted.

Timestamp fields, when provided, should be ISO 8601 and increase within a record. The model uses nominal burn-in hours; deviations of more than 0.5h are flagged. No timestamps are fabricated for uploaded records. Reference synthetic timestamps are explicitly generated.

## Check quality

Data Quality shows completeness, schema health, blocking issues, timestamp availability and detailed findings. Severity filters and field/row information identify remediation. A missingness plot is explicitly limited to the first 200 rows. Exports contain the displayed issue dataset; row details cap at 5,000 with an explicit truncation notice. The health score is an inherited heuristic, not reliability or confidence.

## Run screening

Open Screening. Confirm the active batch, select 24/96/168h and choose Active model + statistics or Statistics only. A 96h prediction model cannot be applied to a 24h screening stage. Execute screening. Progress follows actual processing milestones. The table supports text search, lot/status filters, column visibility and pagination. Counts summarize unique components at their worst record status. Incomplete counts may overlap flagged counts.

Use Open component / Inspect selected component to investigate. Filters are remembered for the batch when navigating back. Historical runs remain unchanged if you edit policy or activate another model; re-screen explicitly to create a new run.

## Investigate and annotate

Anomaly Analysis separates measurements, peer comparisons and model/policy reasons. Filter by lot, measurement, status and score. Component Explorer offers tabs for trajectory, evidence/prediction, review/history and report. Future observations are retrospective; predictions use the selected model's earlier cutoff. Intervals are approximate and unavailable for unsupported inputs.

Save an Engineering review note with Unreviewed, In review or Reviewed state. This records human review progress only. It does not change the measured evidence or auto-release a component. Notes are scoped to the run and component. Generate a component PDF under the Report tab.

## Train, register and activate

In Model Laboratory, use a sufficiently large batch with at least eight independent lots and completed targets. Choose 24h or 96h input cutoff, candidate models, seed and supported estimator sizes. The target remains 168h and the feature whitelist cannot include future data. Lot partitions are fixed in method and displayed in the manifest.

Train candidate models. The lowest validation MAE wins separately for each parameter. Registration follows successful fitting/calibration/test evaluation. Inspect the actual metrics and metadata, then check Confirm and Activate selected model. Training alone does not change the active screening model.

Predictive Analytics can use any registered model without activating it. Click Predict active batch; inspect units, unsupported-range flags, interval availability and input warnings. Permutation importance describes validation sensitivity, not causality or a local SHAP attribution.

## Evaluate honestly

Model Evaluation displays saved validation/test regression results and errors by lot/range. Click Evaluate screening policy to compute actual classification comparisons. If active data differs from the model's training dataset, classification results are labeled descriptive. Without ground truth, precision/recall are unavailable. Inspect false negatives and false positives, not only headline scores. Changing thresholds after looking at test results requires new independent validation.

## Simulate

Scenario Simulator retains the five original recipes and adds elevated variation, missing measurements and mixed-quality populations. Fixed recipes use 120 components, one lot and leakage current; only the supported seed changes. The additional recipes expose size, lots, noise, drift and defect fraction. Baseline and simulation are stored and actually screened; the UI shows the recorded configuration and computed differences. This is synthetic evidence, not a production incident.

## Policies, reports and audit

Policy Center: edit → validate/preview → simulate against current decisions → confirm/save. Preview does not mutate the active policy. Decision rules and per-record specifications are distinct; datasheet limits come from imported rows.

Reports & Exports supports batch, component, quality, model evaluation, scenario and audit outputs when corresponding evidence exists. Preview sections before generating. PDF includes branded tables/charts and limitations; Excel includes all listed sheets; summary CSV contains the first section, as labeled. Download buttons appear only after successful generation. For full raw screening records use the Screening CSV/Excel exports.

Audit Trail displays actual operations and bounded error metadata with search/action/outcome filters. No edit/delete control is offered. The log is not cryptographically tamper-proof.

## Settings, backup and recovery

Settings stores a workspace name, generates a backup ZIP, and offers a confirmed non-destructive demo reset. Reset adds a new demonstration batch and keeps all prior data. To restore a backup: stop the app, move the current workspace directory aside, extract the backup into an empty directory, set ESS_DATA_DIR to that directory, and relaunch. Keep the moved directory until recovery is verified. Never restore over a live catalog.

System Diagnostics shows Python/package versions, OS, workspace writability, catalog schema, model availability, policy, latest successful operation and recent errors. Its smoke test computes a real latent-defect case. If a trusted saved model becomes incompatible, train/register another and activate it; no remote model upload is offered.
