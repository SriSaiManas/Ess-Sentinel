# Executed verification report

Python **3.14.6**, Linux x86_64. Clean virtual-environment installation of all pinned requirements succeeded; `pip check` reported no broken requirements. All 52 Windows CPython 3.14-compatible wheels were downloaded successfully (see compatibility.md).

**61 tests passed, 0 failed, 0 skipped.** Measured statement coverage: **92.15%**, 1432/1554 statements. Final test log, JUnit and JSON coverage are in evidence/. One warning remains: pandas reports timestamp format inference for intentionally malformed test data. Parsing coerces invalid values into a visible validation issue. No SQLite resource warnings remain after connection cleanup.

The unchanged original 35-test suite passed separately on both Python 3.12 and Python 3.14.6. The 2.0 suite retains 33 original backend tests and the server test, replaces obsolete UI navigation assertions and adds service tests. See feature_preservation.md and evidence/backend_preservation.json for exact source comparison.

## Scope actually executed

* Original synthetic generation, validation, drift/features, leakage guards, anomalies, lot-disjoint training, risk, explanations, evaluation and reports.
* New persisted raw bytes, string identifiers, invalid numbers/timestamps, safe paths, model activation, policy versions, immutable historical results, separate review state, backup, non-destructive reset, scenario pairs and error references.
* Streamlit AppTest covers all 17 routes, screening, component review/report, prediction, model training/activation, scenario, policy preview/simulation/save, report generation, settings/backup/reset, diagnostics and empty-state behavior.
* A real HTTP server launch passed. Real Chromium exercised screening, review save, generated PDF download and byte signature, CSV file upload/mapping/explicit commit, active batch selection and diagnostics. JavaScript page errors: none. A 900px viewport overflow assertion passed.
* Six desktop screenshots and one narrower screenshot are genuine browser renders. They were visually reviewed. All six generated report types were rendered and reviewed for pagination/layout. A final table pagination adjustment received a focused report test after the full suite.

Browser interactions were **automated**, followed by visual inspection of captured output. No human-operated Windows browser session was performed. The included script can reproduce those interactions; Playwright and its browser are optional test-only dependencies.

## Defects repaired during verification

String IDs lost leading zeros; textual bounds could raise a TypeError; Linear winners could omit a test metric; changing an instantiated Streamlit batch selector raised an exception; archived UI tests needed exclusion from collection; SQLite transactions did not automatically close connections; a large report table unnecessarily moved past the cover content. These are fixed in 2.0, with relevant regression coverage or rendered-output checks.

## Measured performance

One synthetic parameter, 20 lots, seed 42. One run per size, not an SLA. GUI rendering/report generation are excluded. Memory is deep dataframe accounting for input plus output, not peak process RSS; RSS was unavailable. Raw environment/timing data: evidence/benchmark.json.

| Components | CSV load (s) | Preprocess (s) | Screen (s) | Dataframe MiB |
|---|---:|---:|---:|---:|
| 1,000 | 0.010 | 0.060 | 0.281 | 1.02 |
| 10,000 | 0.078 | 0.063 | 1.115 | 10.21 |
| 100,000 | 0.401 | 0.368 | 9.845 | 102.07 |

## Extracted release check

The ZIP passed its CRC check, was extracted to a separate directory, and launched through AppTest on Python 3.14.6 with a fresh temporary catalog: zero errors or exceptions. See evidence/release_check.json.

## Remaining boundaries

Physical Windows 11 execution and .bat interaction are unverified; dependency wheels and exact Python runtime were verified separately. No real component dataset, industrial qualification, real hardware integration, multi-user access control, authenticated/tamper-proof audit, installer signing or security certification is claimed. The default dataset, trained demo and reported metrics are explicitly synthetic. Local model files must be trusted. Backup should be run while the single-user workspace is idle. First dependency installation requires internet. Reports export at most seven PDF fields with an explicit notice; CSV/XLSX carry all supplied fields. No failing or skipped test is concealed as a pass.
