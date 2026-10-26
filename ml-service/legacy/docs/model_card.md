# Model card: ESS Sentinel demonstration models

## Intended use and provenance

Local decision support for inspecting electronic-component burn-in trajectories. Not suitable for autonomous release, rejection, hardware control, flight qualification or reliability certification. No real ISRO dataset was supplied. Included models are trained on 2,000 reproducible synthetic components, with three parameters each (6,000 records), seed 42. Synthetic mechanisms include stable behavior, high values, latent/gradual/accelerating drift, abrupt failures, decreasing trajectories, lot variation and measurement noise.

The generator is illustrative, not a semiconductor physics model. Defect labels refer to injected mechanisms, even when an absolute threshold is not crossed. Real prevalence, calibration and transfer performance are unknown.

## Models and selection

Six candidates per parameter: ordinary linear regression, Ridge alpha 1 and 10, an 80-tree random forest with minimum leaf size 3, and 100-stage Huber gradient boosting at depths 2 and 3. Lowest validation MAE wins per parameter. No deep learning or XGBoost dependency. Numeric imputation/scaling and categorical encoding fit only on training data. Separate estimator objects prevent cross-parameter model contamination.

Isolation Forest (100 trees) provides an unsupervised feature-space anomaly score. Robust statistical evidence and engineering rules are retained because Isolation Forest alone does not demonstrate adequate recall in this synthetic run. Default policy thresholds are illustrative predeclared values, not empirically qualified industrial thresholds.

## Split and leakage controls

20 independent lots split 10 training / 3 validation / 3 calibration / 4 test. Test set: 400 components / 1,200 parameter records. Components and repeated sessions cannot cross lot partitions. Feature whitelists use only values available by 24h (or by 96h for the optional model), condition metadata and derived early drift. Truth labels, defect names and future values are excluded. Tests perturb future values and labels to verify invariant early predictions/risk. Duplicate measurement signatures across lots block training for review.

Model selection is based on validation MAE, not test performance. These are single-split results, not cross-validation estimates or confidence bounds. The shipped seed does not establish robustness across data-generating distributions.

## Actual regression results

MAE/RMSE/median error carry each parameter's unit: leakage uA, standby mA, delay ns. R2 is unitless. Do not average errors across different units.

| parameter | model | split | MAE | RMSE | R2 | MedianAE |
| --- | --- | --- | --- | --- | --- | --- |
| Leakage current | Linear | test | 3.7531 | 8.3993 | 0.5633 | 1.9476 |
| Leakage current | GradientBoosting-3 | test | 1.6839 | 7.8140 | 0.6220 | 0.1581 |
| Propagation delay | Linear | test | 3.0419 | 6.9021 | 0.5517 | 1.5276 |
| Propagation delay | GradientBoosting-2 | test | 1.3361 | 6.1109 | 0.6486 | 0.1289 |
| Standby current | Linear | test | 0.7356 | 1.7622 | 0.5456 | 0.3243 |
| Standby current | GradientBoosting-3 | test | 0.3385 | 1.5925 | 0.6289 | 0.0290 |

Large RMSE relative to MAE reflects hard cases, especially sudden failures without early warning. Prediction quality must be assessed across defect mechanisms, not only aggregate error.

## Actual early screening evaluation

The following are record-level metrics on held-out synthetic lots at 24h. Positive = defect mechanism for truth; positive = engineering review for the hybrid policy. WATCH is counted as review, including incomplete/unsupported assessments. Thus review recall is not equivalent to confirmed-failure detection. PR_AUC uses average precision. Undefined metrics are left unavailable, not replaced with fabricated values.

| method | TN | FP | FN | TP | Recall | Precision | F1 | Specificity | FNR | FPR | ROC_AUC | PR_AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Static only | 1044 | 0 | 154 | 2 | 0.0128 | 1.0000 | 0.0253 | 1.0000 | 0.9872 | 0.0000 | 0.5064 | 0.1412 |
| Robust statistics | 1044 | 0 | 31 | 125 | 0.8013 | 1.0000 | 0.8897 | 1.0000 | 0.1987 | 0.0000 | 0.9100 | 0.8687 |
| Isolation Forest | 1044 | 0 | 116 | 40 | 0.2564 | 1.0000 | 0.4082 | 1.0000 | 0.7436 | 0.0000 | 0.9109 | 0.8725 |
| Hybrid review policy | 907 | 137 | 23 | 133 | 0.8526 | 0.4926 | 0.6244 | 0.8688 | 0.1474 | 0.1312 | 0.9130 | 0.8701 |

The hybrid policy improves recall over static-only screening at the cost of false positives. Remaining false negatives are explicitly present. Strong early outliers/drift are easier than sudden failures with no early signature. Default score thresholds were not optimized on the test results. If a user tunes policy while viewing test metrics, those outcomes are exploratory and must be checked on a new untouched dataset.

## Uncertainty and explainability

A 90% absolute residual quantile from the separate calibration partition is added/subtracted from point predictions if there are at least 20 calibration records. This follows split-residual calibration, but within-lot dependence and unseen-lot distribution changes mean no finite-sample 90% guarantee is asserted. Out-of-range inputs and unseen families withhold intervals and require review. Anomaly percentile, interval, review risk score and model probability are different; the application does not invent a calibrated failure probability.

Validation permutation importance measures MAE sensitivity to shuffled features. Individual explanations describe the rules and risk contributions, not causal model behavior. Correlated features can share importance. SHAP is not used; permutation importance and transparent rule contributions provide the implemented explainability.

## Limitations and required qualification

* No real component validation, datasheet-derived policy or official problem-statement verification.
* Synthetic labels/mechanisms are easier to separate than many actual latent defects.
* Sudden failures without early signals cannot generally be predicted from early values.
* Peer statistics include the evaluated component; small or heavily contaminated cohorts can mask anomalies.
* No pooled fallback across incompatible sessions/conditions. Sparse groups trigger review.
* Only 24h/96h prediction cutoffs and a 168h target are modeled. Extra generator times are exported, not automatically modeled.
* Missing early input suppresses predictions rather than silently imputing an engineering disposition.
* Entirely new parameters require retraining. Unit conversion is explicit. Family/range shift is flagged but not solved.
* Audit storage is local, mutable and unauthenticated. This is a single-user prototype.
* Clinical, flight-safety or industrial certification is outside scope. Final engineering disposition remains human.

## Reproducibility

See models/demo/manifest.json for exact version, timestamp, seed, feature list, lot partitions, dataset hash, hyperparameters and policy. requirements.txt pins the clean-environment dependencies. Run `python -m ess.cli demo` to regenerate results. Model files require compatible scikit-learn versions and must be trusted.

## Version 2.0 implementation note

The bundled demo models and historical metrics above are preserved original artifacts, not newly claimed real-data results. Version 2.0 successfully loaded and used them on Python 3.14.6 with the same pinned libraries. Model Laboratory now exposes seed, candidate subset, tree and boosting-stage controls; each new registration records its own manifest and metrics. Registration does not activate a model. The Linear-winner test-metric reporting edge case was fixed without changing predictions. New experiments must be assessed using their own held-out results.
