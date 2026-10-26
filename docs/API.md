# REST API

All endpoints except GET /api/health require `Authorization: Bearer <token>`. Operator token is required for mutations. Response errors use `{error:{message,requestId}}`. 400 invalid schema/ID, 401 missing credentials, 403 role denied, 404 absent resource, 409 retained history, 413 upload/response too large, 422 invalid engineering data, 429 concurrency/rate limit, 503 worker failure, 504 timeout.

GET /api/openapi.json provides an endpoint index in OpenAPI format. This table provides payload details.

## Catalog

GET `/api/{resource}` returns `{items,total,page,limit}`. Resources: batches, screening-runs, reviews, models, policies, scenarios, reports, audit-events. Pagination: page>=1, limit=1..100; sort=oldest or newest (default). Batches support search and source=IMPORTED|SYNTHETIC. Screening runs support batchId; reviews support runId and componentId. GET `/api/{resource}/{id}` retrieves one document. All identifiers are MongoDB ObjectId hex strings.

- POST /api/batches: multipart file (CSV/XLSX <=25 MiB), name, mapping JSON, units JSON, commit=false|true. Preview returns health/issues/preview; commit returns batchId (201).
- PATCH /api/batches/:id: `{name?,archived?}`. Immutable measurement artifacts are not edited in place; import a corrected batch.
- DELETE /api/batches/:id: only when no run/scenario references. Audit and underlying immutable artifacts are retained. Prefer archive for normal use.
- GET /api/components?batchId=...&search=...&page=1: component measurement records, 100 per page. Components are rows in immutable batch artifacts, not a redundant MongoDB collection.
- GET /api/context?batchId=...: active batch/run/model/policy/settings.
- GET /api/reports/:id/download/pdf|xlsx|csv: persisted report. Use zip for backup reports.

Runs, policies, models, scenarios and reports are immutable historical entities. No ordinary delete or overwrite endpoints are provided. Reviews support create/update through the review action. Audit is append-only. Complete editable-record CRUD is demonstrated on batches; enforcing history immutability is intentional.

## Analytics/action POST endpoints

Path prefix `/api/actions/`. Bodies are JSON, unknown fields are rejected.

| Operation | Request body | Result |
|---|---|---|
| seed | {} | batchId; creates initial synthetic workspace |
| quality | {batchId} | health, issues |
| measurements | {batchId} | normalized measurement rows |
| results | {runId} | parameter-level screening rows |
| screen | {batchId,stage:24/96/168,statisticsOnly:false} | runId |
| train | {batchId,options:{cutoff:24/96,seed,trees:20..300,boosting_stages:20..300,candidate_names?:[...]}} | modelId |
| model | {modelId} | manifest, comparison, test_predictions, importance |
| activate | {modelId} | activation acknowledgement |
| predict | {batchId,modelId} | actual model inference rows |
| evaluate | {runId} | descriptive classification metrics if labels exist |
| simulate | {name,seed?,n?,lots?,noise?,severity?,defect_fraction?} | id, baseline, batchId |
| policy | {config,save:false,batchId?} | validation or before/after decisions; save=true persists policy |
| review | {runId,componentId,state,note} | upsert review, append audit event |
| report | {kind,runId?,batchId?,modelId?,componentId?} | reportId |
| backup | {} | reportId for ZIP |
| settings | {name} | saved workspace label |
| reset | {} | new synthetic batch; previous work retained |
| diagnostics | {} | runtime readiness/dependencies |
| smoke | {} | actual latent-defect smoke result |

Candidate names: Linear, Ridge-1, Ridge-10, RandomForest, GradientBoosting-2, GradientBoosting-3. Linear remains baseline. Review states: Unreviewed, In review, Reviewed. Report kinds: batch, component, quality, evaluation, audit, scenario. Original five fixed scenarios and three configurable scenarios are exposed in the UI.

API process spawns Python without a shell; requests cannot supply executable paths or commands. Trusted model/artifact paths are derived internally. MongoDB collections: batches, runs, models, policies, reviews, events, reports, scenarios, settings. Binary artifacts remain on persistent disk.
