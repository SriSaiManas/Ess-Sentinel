# Original-to-2.0 preservation map

The original 35-test suite was rerun unchanged in an isolated copy on Python 3.12 and then Python 3.14.6; both passed. In 2.0 only the old UI test was replaced, because its single-radio navigation no longer exists. The 33 core tests and real-server launch test remain. The new UI test covers all 17 routes and the equivalent workflows plus new operations. The original UI test source is retained for inspection under docs/original and is excluded from collection by pytest.ini.

| Original implementation | 2.0 implementation | Verification |
|---|---|---|
| ess/data/synthetic.py | Retained unchanged; Workspace adds paired scenarios and explicit synthetic timestamps | generator/latent/population tests; test_scenario_pair |
| ess/data/validation.py | Retained with string-ID preservation and safer numeric-bound ordering | original ingestion tests; test_string_ids_preserved; test_quality_invalid_numbers_and_bounds |
| ess/features/engineering.py | Retained unchanged | test_feature_math_and_leakage; test_asof_guard |
| ess/anomaly/statistics.py | Retained unchanged | test_population_scenario; test_latent_and_normal |
| ess/prediction/training.py | Retained algorithms; added optional experiment controls/progress; fixed Linear-winner reporting edge | original prediction/split tests; test_training_progress_seed_and_linear_winner |
| ess/prediction/evaluation.py | Retained unchanged | test_metric_edge_cases; label-free tests |
| ess/risk/engine.py and ess/config.py | Retained unchanged; new service stores policy/run versions | policy/static/threshold tests; test_policy_version_and_immutable_run |
| ess/explainability/reasons.py | Retained unchanged | original integration explanations; component UI test |
| ess/audit.py | Retained API; explicit SQLite connection cleanup; new catalog event store adds batch/outcome metadata | original audit test; new persistence/error tests |
| ess/reports/export.py | Retained baseline PDF/CSV; new branded PDF and XLSX service | original integration test; test_excel_formula_protection; test_branded_pdf |
| app.py monolith | Shell + reusable services + five grouped UI modules | test_end_to_end_widgets; browser verification |
| Trusted demo artifacts | Preserved original estimator bundles and metrics | Python 3.14 loading/inference tests and actual bootstrap |

## Documented changes that do not silently alter engineering semantics

* IDs retain leading zeroes during CSV/XLSX ingestion.
* Specification bounds are parsed before checking measurement sign, avoiding a TypeError when bounds are textual.
* Timestamp validation is additional and applies only when timestamp fields exist.
* Linear winners now retain their test metric row rather than an empty comparison entry.
* Model registration no longer activates automatically; explicit confirmation is required.
* Policy/model changes do not overwrite historical screening results.
* Review state is separate from engineering risk/disposition.
* Dataset health inherits the original heuristic; new row-level diagnostics are supplemental, not a fabricated reliability score.

SQLite connection cleanup was added to the original Audit API and backup writer to prevent resource leaks and Windows temporary-file lock conflicts.
