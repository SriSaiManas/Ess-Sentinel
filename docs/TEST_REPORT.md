# Verification and release acceptance

## Status

Implementation and available checks are complete; **the full definition of done is not yet verified**. Real MongoDB persistence, integrated authenticated browser workflows, Windows execution, Docker startup and deployment remain acceptance gates. This is a reviewable migration package, not a claim of production certification or deployment.

## Executed evidence

| Check | Result | Scope |
|---|---|---|
| Preserved Python suite | 61 passed, one timestamp parsing warning | Existing algorithms, services, Streamlit regression suite |
| Express validation/security suite | 9 passed | Authentication/roles, invalid IDs, schema validation, malformed uploads, immutable audit routes, worker failures, API index |
| React component suite | 5 passed | Sign-in, all 17 routes, API error state, table filter/paging, import confirmation, responsive CSS rules |
| Python bridge/adapter suite | 6 passed | Actual screening, model loading/prediction/training, policy preview, reviews, scenarios, six report formats/types and backup; **mongomock catalog** |
| Vite production build | Passed | React build; bundle size warning remains |
| Browser | Sign-in page rendered and visually inspected | Authenticated workflows not verified |
| Real MongoDB integration suite | Blocked at database startup | MongoDB 7.0.14 binary downloaded; process exited 100, `open: Operation not permitted` |

The 81 passing tests span different layers and do not compensate for the blocked persistence checks. React tests use mocked API responses. Adapter tests use an in-memory mock exclusively in test code. Production code requires MongoDB and has no mock/localStorage persistence fallback.

Current test logs are under docs/evidence. Historical ESS 2.0 evidence remains under ml-service/legacy/evidence and is explicitly not Web 3.0 verification.

## Compatibility correction

The supplied model was serialized with scikit-learn 1.9.1. This environment uses 1.8.0, so the initial inherited UI test could not reach prediction. The copied demonstration model was regenerated from the original synthetic dataset with the preserved training algorithm; all 61 inherited tests then passed. The original ZIP and original extraction were unchanged. `requirements-tested.txt` records the tested direct dependencies, and `scripts/rebuild_demo.py` provides reproducible regeneration for another runtime.

Tested here: Linux, Node.js 24.22.1, Python 3.12, scikit-learn 1.8.0. Windows 11/Python 3.14 are not verified by this migration run. Use Python 3.12 as documented.

## Remaining acceptance checklist

- [ ] Run `npm run test:integration` on a host that supports MongoDB or against a dedicated TEST_MONGO_URI. The suite covers Mongo create/read/update/delete, reconnection persistence, protected references, actual Python/Express integration, training and report downloads.
- [ ] Start the API against valid MongoDB configuration and test the built frontend through Express.
- [ ] Use a browser to import/commit, screen, review, train/activate, compare policies, run scenarios, and download exports.
- [ ] Check authenticated pages at desktop, tablet and phone widths. Responsive CSS is implemented; CSS assertions are not visual browser verification.
- [ ] Migrate a copied SQLite workspace into an empty test target and reconcile catalog counts, relationships and hashes.
- [ ] Test Windows scripts/commands and container startup if those deployment paths will be used.
- [ ] Review the design against the supplied screenshots. Original colours, logo, group hierarchy, page names, KPI structure and major workflow controls are retained; an 85–90% visual preservation figure has not been measured.

## Operational limits

- Shared operator/viewer bearer tokens provide role checks, not per-person identity or revocable sessions. Audit records identify operations, not an authenticated individual.
- Up to two Python processes run per API instance. There is no durable distributed job queue or automatic retry; a crash/timeout may leave orphan artifacts. Inspect history before retrying writes.
- MongoDB writes and disk artifacts are not a single transaction. No multi-instance write-safety or production load qualification is claimed.
- Batch deletion retains audit and artifact evidence and refuses known run/scenario references. Archive is the normal history-preserving workflow.
- Catalog selectors initially display the latest 100 batches/models; API pagination is available. Tables and charts fetch full selected-batch data, so very large datasets need further server-side result pagination/aggregation.
- Policy/classification metrics shown on a selected batch are descriptive; saved regression test metrics retain lot-disjoint provenance. Synthetic datasets are not real industrial qualification.
