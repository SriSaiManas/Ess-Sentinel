# User guide

## First demonstration

Run `setup_windows.bat` once, then `run_windows.bat`. On Linux/macOS use README commands. Open http://localhost:8501. A synthetic dataset and trained demonstration model are ready. Click **Screen current batch**. The Overview displays unique component counts and the worst status across each component's parameter records.

## Import your dataset

1. Open **Data Import**, choose a CSV/XLSX under 25 MB.
2. Preview the data and map source columns to the expected schema. Do not map one column twice.
3. Include units and spec_min/spec_max. Enter operating conditions if known; omitted defaults produce warnings.
4. Click **Validate and import**. Errors block import; correct the source file and retry.
5. Read **Dataset Validation**. Its health score is a schema heuristic, not model confidence.
6. Go to **Drift Prediction** and train using your data. A demo model is not qualified for real parts.

Ground truth labels are optional for screening. Without them the app does not report classification precision/recall. Targets at 168h are necessary for training, not for inference. Missing 24h inputs produce review warnings rather than invented predictions. Missing 96h values do not prevent the 24h model from working.

## Train and evaluate

Choose 24h or 96h cutoff, then **Train and evaluate models**. At least eight lots are needed. Each parameter also needs at least 30 training records and five validation/test records with required inputs. The candidate table shows validation MAE/RMSE/R²/median error. Lowest validation MAE is selected automatically. A new model invalidates the old screening view. Re-screen to apply it.

**Model Evaluation** compares static screening, robust statistics, Isolation Forest and the hybrid review policy. During a matching training run, the classification evaluation uses held-out test lots. A changed dataset shows an explicit warning: those classification results are descriptive. Altering policy while looking at test outcomes is exploratory and invalidates claims of an untouched threshold evaluation; confirm the chosen policy on new external data.

## Screen a batch

Select the screening stage in the sidebar, then **Screen current batch**. A 96h model cannot be used at a 24h screening stage. The default 24h model can remain an early prediction during later retrospective screening. Watch the differences between observed static violations, dynamic anomalies, predicted safety crossings and predicted absolute-specification crossings.

**Anomaly Detection** supports lot, parameter, status and score filters. Sort table columns. Select a table row to show its trajectory and explanation. Export the filtered result.

## Inspect a component

Open **Component Detail** or **Burn-In Trajectory**. Choose lot, component and parameter/session/condition. See observed values, peer range, peer median, specification/safety lines and the predicted 168h diamond. Future actual values are gray retrospective points, not model inputs. Every flagged record has an explanation. Generate and download the component PDF. The component report includes all of that component's parameter records.

**Model Explainability** shows validation permutation importance and an individual additive risk contribution chart. Importance is not causal attribution. Strong rules can override the score category; both the reasons and numerical points are available.

## Change thresholds

Open **Engineering Policy**. All weights and risk/robust/Isolation Forest/peer thresholds are configurable. They are illustrative defaults, not industrial limits. Nonnegative weights must sum to 100 and status cutoffs must increase. Absolute specifications come from dataset rows. Apply changes and re-screen; previous results are invalidated. All changes are audited.

## Generate data

Open **Synthetic Generator**. Set components, lots, defect fraction, noise, drift severity, limit multiplier, measurement intervals and seed. Required generator intervals are 0h, 24h and 168h; include 96h for that optional model. One component receives three parameter records. Download the generated CSV, train and screen. Every synthetic dataset is labeled.

## Export and audit

**Reports & Audit** exports all/flagged records, batch PDF, active policy and the audit CSV. Model versions, dataset/policy hashes and screening stage are included in results. Reports are recommendations for qualified engineering review. Download actions, generated reports and assessments are logged locally.

## Troubleshooting

* Missing Python: install Python 3.12 with launcher, then rerun setup.
* Dependency install failure: inspect terminal error and verify network access; setup does not contain offline wheels.
* Model incompatible/corrupted: retrain in Drift Prediction. Never import joblib files from untrusted sources.
* Too few lots: collect independent lots; the app intentionally refuses to claim held-out performance from a tiny dataset.
* Different units: convert before import. No automatic engineering-unit guessing.
* Duplicate signature across lots: inspect duplicated acquisition records before training. Quantized legitimate duplicates may need domain review; do not casually delete evidence.
* WATCH due to missing data: complete the required observations or route to human review.
* Normal Lot contains some WATCH results: statistical false positives can occur. The app never forces all normal-lot outputs to be normal.
* Public access: not configured. Use locally; do not expose the development app without access controls.
