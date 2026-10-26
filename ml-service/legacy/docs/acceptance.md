# Release acceptance

| Area | Status / evidence |
|---|---|
| Original backend preservation | Original tests passed on 3.12 and 3.14.6; exact source map provided |
| Separate 2.0 project | New folder and archive; original preserved |
| All 17 requested pages | Implemented, exercised through AppTest |
| Actual UI workflow | Chromium screening/review/upload/download/diagnostics pass |
| Persistence | SQLite catalog, immutable input/model/result files; reopen/backup tests |
| Reports | Six actual PDF/XLSX examples; PDF pagination visually reviewed |
| Python target | Exact 3.14.6 Linux installation and full suite pass |
| Windows dependencies | All 52 pinned compatible wheels downloaded |
| Physical Windows 11 | Not executed; supplied launch/setup/test scripts |
| Data and model validity | Synthetic demonstration only; no real-world accuracy claim |
| Production security / hardware control | Outside implemented local decision-support scope |

Full execution evidence and limitations: testing.md. Deployment compatibility: compatibility.md.
