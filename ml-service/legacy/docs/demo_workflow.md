# Five-minute demonstration

1. Run `setup_windows.bat`, then `run_windows.bat`. Open http://localhost:8501. First launch creates a clearly marked synthetic reference batch and registers the bundled trusted model.
2. Overview: inspect real counts, risk distribution, highest-priority findings and activity. Operations shows the local workspace state; this is not connected to physical test hardware.
3. Screening: select cutoff, execute screening, filter the saved result and export it. Anomaly Analysis shows computed peer/drift evidence. Component Explorer shows trajectory, contributing reasons, metadata and review history. Save an engineering review note; it does not overwrite risk.
4. Data Ingestion: upload `data/samples/multilot_timestamped.csv`, inspect mappings, units and quality findings, explicitly confirm and commit. Batch Explorer selects persisted batches; Data Quality explains missing values and timestamp issues. Return to Screening to compute results for the new batch.
5. Model Laboratory: choose candidate controls and train. Inspect validation/test metrics. Registered models require explicit activation. Predictions can use another registered model without changing the active model.
6. Scenario Simulation: run a paired baseline/scenario comparison. Evaluation distinguishes model metrics from labeled screening metrics and does not invent ground truth for unlabeled data.
7. Thresholds & Policies: preview a policy change, simulate, then explicitly confirm its new version. Existing runs remain historical snapshots.
8. Reports & Exports: generate a report, download PDF/XLSX/CSV, then inspect Audit & Logs. Settings provides backup and confirmed non-destructive demo reset. System Diagnostics shows dependencies and a runnable backend smoke test.

Suggested short live presentation: steps 1–3, then report generation and persistence after restart. Training time depends on selected candidates and machine; it is not required to use the bundled model. All default data and metrics are synthetic and final component disposition remains an engineering decision.
