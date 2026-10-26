# ESS Sentinel Web 3.0

React engineering workspace + Express REST API + MongoDB catalog + preserved Python analytics.

**Release status: implemented migration, awaiting real MongoDB end-to-end acceptance.** This environment blocked the MongoDB process (`open: Operation not permitted`). Do not treat mock-database adapter tests as MongoDB verification. See `docs/TEST_REPORT.md` for exact evidence and limitations. Not deployed online. Original input archive was not changed.

## Quick start on Windows (Command Prompt)

Install Node.js 24 and Python 3.12. Supply either a running MongoDB Community server or a MongoDB Atlas URI. Extract this ZIP, open the `ess-sentinel-web` folder, then:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r ml-service\requirements-tested.txt
npm ci
copy .env.example .env
```

Edit `.env`: set `MONGO_URI`, database name, and two **different** random operator/viewer tokens. Generate each token with:

```bat
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Use `PYTHON_BIN=python` with the virtual environment activated. For a service installation, use the absolute interpreter path. If setting `ARTIFACT_DIR`, use an absolute persistent path such as `E:/ess-data/artifacts` (forward slashes work on Windows).

Build a model compatible with your installed dependencies, then create the demo and build the frontend:

```bat
python scripts\rebuild_demo.py
npm run seed
npm run build
npm start
```

Open **http://localhost:3001** and paste your configured operator token into the sign-in form. All React requests go to Express. No browser connection to MongoDB or Python occurs. Tokens remain in memory, so refresh signs out. Do not paste tokens into chat or commit `.env`.

For development, keep `npm start` running in one activated terminal and run `npm run dev` in another. Open http://localhost:5173. Vite proxies `/api` to port 3001. The development frontend URL is configured in `CLIENT_ORIGIN`.

Python is a controlled internal subprocess service. Express starts a fresh worker for each analytics request; **there is no separate Python HTTP server to start**. CRUD requests stay in Node/Mongoose. At most two analytics workers run concurrently per API process. Heavy operations have a configurable timeout.

## Linux/macOS

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r ml-service/requirements-tested.txt
npm ci
cp .env.example .env
# Configure MongoDB, tokens and persistent artifact storage in .env.
python scripts/rebuild_demo.py
npm run seed
npm run build
npm start
```

## Demonstration workflow

1. Open Overview and confirm the batch source is **SYNTHETIC**.
2. Data Ingestion: choose `ml-service/legacy/data/example_synthetic.csv`, name it, preview, review mappings/units and commit. Because it was uploaded, its source is IMPORTED; its `synthetic` column still identifies generated measurements. Never call it real industrial evidence.
3. Screening: choose 24 hours and execute. Inspect explanation, risk category, observed drift and forecast separately.
4. Component Explorer: select a component, view trajectory and save a review note.
5. Model Laboratory: select candidates and train. Training does not activate the result; explicitly activate it after reviewing validation/test metrics.
6. Scenario Simulator: run Early Warning or Latent Defect. Compare baseline and simulated batches using Batch Explorer and Overview.
7. Policy Center: validate and preview decisions before saving a version. Historical runs keep the policy used when created.
8. Reports & Exports: generate PDF/XLSX/CSV. Component PDF is in Component Explorer; backups are in Settings.
9. Batch Explorer: rename or archive a batch. Delete is allowed only with no run/scenario references. Audit events remain.

## MongoDB Atlas configuration

Create an Atlas project/cluster in your own account. Create a database user restricted to this application's database, add the actual API host IP to the network access list, and obtain the Node.js connection URI. Put the URI in server-side `MONGO_URI`, replacing the password with its URL-encoded value. Keep the URI out of React variables. Atlas UI and tier offerings can change; use the current Atlas connection instructions. This project does not create or verify an Atlas account for you.

Startup initializes Mongoose schemas and indexes. `npm run seed` adds a synthetic batch and registers the rebuilt demonstration model. There are no seeded passwords or embedded database credentials.

## Tests

```bat
npm run test:unit
npm run test:integration
python -m pip install -r ml-service\requirements-test.txt
python -m pytest tests\test_bridge.py -q
cd ml-service\legacy
python -m pytest tests -q
```

`test:integration` starts an isolated real MongoDB process using mongodb-memory-server; it downloads an official MongoDB binary. If local execution is unavailable, set `TEST_MONGO_URI` to a **dedicated test server/Atlas connection** before running it. It creates a unique `ess_test_*` database. Never supply production credentials. Its test DB is dropped during cleanup. `test:unit` uses mocked API responses for React component tests and injected worker failures for API tests. `test_bridge.py` uses mongomock for catalog calls while executing the actual Python algorithms/reports. No mock is used by the shipped application.

## Migration from SQLite 2.0

Keep the source workspace and original archive. Use an empty MongoDB database and empty artifact directory, set the corresponding environment variables in the activated shell, then run:

```bat
python scripts\migrate_sqlite.py E:\path\to\ESS_Sentinel_2.0\outputs\workspace
```

The utility reads SQLite in read-only mode, assigns ObjectIds, remaps primary relationships and active selections, copies trusted CSV/model/run artifacts, and preserves events/reviews/settings. Nested legacy IDs inside historical event details remain original evidence; `migration-map.json` resolves them. Generated 2.0 report files were not cataloged; retain the original backup for those exports and regenerate reports in Web 3.0. An interrupted migration is not transactional: preserve the source, explicitly clear the incomplete **target only**, and retry. The migration utility requires real-MongoDB acceptance testing before use on valuable data.

## Online deployment

Recommended initial deployment: one private container/VM for Express plus Python and persistent artifact disk; MongoDB Atlas separately. `npm run build` emits client/dist and Express serves it. Terminate HTTPS at a reverse proxy, set a long enough proxy request timeout for analytics, and configure the exact client origin. Do not expose MongoDB publicly without authentication. Do not use ephemeral storage for artifacts.

For a separate static frontend host, set `VITE_API_URL=https://your-api-host.example` **before building** and set Express `CLIENT_ORIGIN` to the exact frontend origin. Configure the static host to rewrite React routes to index.html. Never put tokens, database URIs or passwords in VITE variables. Python remains alongside the API under the controlled subprocess interface.

Dockerfile and compose.yaml provide an alternative local stack; container startup and online deployment were not verified here. Configure `.env`, then `docker compose up --build`; run `docker compose exec app npm run seed`. Container builds rebuild the synthetic model for the container runtime.

For a larger production service, add per-user identity, a durable job queue, transactional catalog/artifact operations, monitored backups and operational load testing. Current shared-role tokens and per-process concurrency limits suit a controlled academic demonstration; they do not constitute an audited multi-user production deployment.

## Troubleshooting

- `Database unavailable` / startup failure: confirm MongoDB is running, URI/password and Atlas network access are correct. The app has no in-memory fallback.
- `Python runtime unavailable`: activate `.venv` or set an absolute `PYTHON_BIN`.
- Model unavailable: run `python scripts/rebuild_demo.py` before seeding, or train and activate a new model. Never upload untrusted joblib files.
- No predictions: inspect required early measurements, units, model cutoff and support flags.
- Training fails: at least eight independent lots and enough complete records per split are required.
- 429: wait for a running analytics task; two workers are allowed per API process.
- 504: inspect audit/history before retrying a mutation; a timed-out process can leave completed artifacts or an incomplete operation.
- 409 on delete: the batch has retained history; archive it instead.
- Reports may be large: full tables paginate; PDF shows at most seven fields and Excel contains all fields.
- Access denied: use the operator token for writes; viewer tokens can inspect and compute read-only analytics.

See `docs/API.md`, `docs/MIGRATION.md`, and `docs/TEST_REPORT.md`.
