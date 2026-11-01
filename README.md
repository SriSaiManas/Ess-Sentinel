# ESS Sentinel Web 3.0

**An intelligent industrial equipment health monitoring and predictive maintenance platform.**

ESS Sentinel combines a React dashboard, Express REST API, MongoDB-backed data catalog, and Python-based machine learning analytics to support equipment screening, anomaly detection, predictive maintenance, risk evaluation, and reporting.

## Project Overview

ESS Sentinel Web 3.0 provides an integrated workspace for:

- Industrial data ingestion and validation
- Equipment health screening and risk assessment
- Component-level analysis and monitoring
- Machine learning model training and evaluation
- Predictive maintenance and scenario simulation
- Policy configuration and decision support
- Historical reviews, audit events, and reporting
- PDF, Excel, and CSV exports

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Node.js, Express |
| Database | MongoDB Atlas, Mongoose |
| Artifact Storage | MongoDB GridFS |
| Analytics | Python, Pandas, NumPy, Scikit-learn |
| Machine Learning | Python-based analytics and prediction pipelines |
| Deployment | Vercel (frontend), Render (backend) |
| Version Control | Git, GitHub |

## Architecture

```text
                 USER / EVALUATOR
                        |
                        v
              React + Vite Frontend
                   (Vercel)
                        |
                  HTTPS REST API
                        |
                        v
                Express Backend
                   (Render)
                        |
             +----------+----------+
             |                     |
             v                     v
        MongoDB Atlas         Python Worker
             |                     |
       +-----+------+       ML / Analytics
       |            |       Screening / Training
       v            v       Prediction / Reports
   MongoDB       GridFS
   Catalog       Artifacts
```

**Important architectural decisions:**

- The browser communicates with Express through REST APIs.
- MongoDB stores application metadata, catalog records, and relationships.
- GridFS stores datasets, normalized CSV files, model artifacts, screening results, and other persistent files.
- Python runs as a controlled subprocess managed by the Express backend.
- The application does not require a separate Python HTTP server.
- GridFS avoids depending on Render's ephemeral local filesystem for persistent analytics artifacts.

## Application Features

### 1. Dashboard and Overview
- Centralized equipment health overview.
- Batch statistics and monitoring indicators.
- Risk summaries and analytical insights.
- Dashboard context and summary endpoints.

### 2. Data Ingestion
- Upload industrial CSV datasets.
- Preview and validate uploaded data.
- Review field mappings and measurement units.
- Commit validated datasets into the application catalog.

### 3. Equipment Screening
- Execute equipment screening workflows.
- Analyze observed measurements and drift.
- Generate risk classifications and forecasts.
- Persist screening results for later retrieval.

### 4. Component Explorer
- Inspect individual equipment components.
- View component-level measurements and trajectories.
- Record review notes and observations.

### 5. Model Laboratory
- Train machine learning models.
- Compare candidate models.
- Evaluate validation and test metrics.
- Activate selected models after reviewing their performance.

### 6. Scenario Simulator
- Run predictive maintenance scenarios.
- Evaluate early-warning and latent-defect scenarios.
- Compare baseline and simulated outcomes.

### 7. Policy Center
- Configure evaluation policies.
- Validate and preview policy decisions.
- Save policy versions while retaining historical references.

### 8. Reports and Exports
- Generate PDF reports.
- Export Excel workbooks.
- Download CSV results.
- Retrieve persistent analytics artifacts through the backend.

### 9. Batch Explorer and Reviews
- Browse, rename, and archive batches.
- Inspect historical records.
- Add review annotations.
- Preserve audit history and historical references.

## Public Demonstration Mode

The application supports a public evaluator demonstration mode.

Set:

```env
DEMO_MODE=true
```

In this mode:

- Evaluators can access the dashboard without entering an operator or viewer token.
- Normal demonstration workflows, including screening, training, and report generation, are available.
- Destructive batch deletion is blocked.
- Archiving is available as an alternative to deletion.
- Sensitive database configuration remains server-side.

**Security note:** Public demonstration mode is intended for controlled academic evaluation. It is not a substitute for a production multi-user authentication and authorization system. Do not use it to expose confidential industrial data or unrestricted administrative operations.

## Local Setup

### Prerequisites

- Node.js and npm
- Python 3.12
- MongoDB Community Server or MongoDB Atlas
- Git

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ess-sentinel-web
```

### 2. Create a Python virtual environment

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r ml-service/requirements-tested.txt
npm ci
```

### 4. Configure environment variables

Copy the example configuration:

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**Linux/macOS:**

```bash
cp .env.example .env
```

Configure the values in `.env`:

```env
MONGO_URI=<YOUR_MONGODB_CONNECTION_STRING>
MONGO_DB=ess_sentinel

DEMO_MODE=true
NODE_ENV=development

PYTHON_BIN=python
ML_TIMEOUT_MS=300000
```

Use the actual environment variable names and defaults defined in `.env.example` and the application configuration.

Never commit `.env` or expose database credentials in frontend environment variables.

### 5. Initialize demonstration data

If the demonstration model needs to be rebuilt:

```bash
python scripts/rebuild_demo.py
```

Seed the database:

```bash
npm run seed
```

### 6. Build and start the application

```bash
npm run build
npm start
```

Open:

**http://localhost:3001**

The Express server serves the built React application and handles API requests.

### Development Mode

Keep the backend running:

```bash
npm start
```

In another terminal, run:

```bash
npm run dev
```

Open:

**http://localhost:5173**

The Vite development server proxies API requests to the Express backend.

## Environment Configuration

| Variable | Purpose |
|---|---|
| `MONGO_URI` | MongoDB connection URI |
| `MONGO_DB` | Database name |
| `DEMO_MODE` | Enables public evaluator demonstration mode |
| `NODE_ENV` | Application environment |
| `PYTHON_BIN` | Python executable used by the backend |
| `ML_TIMEOUT_MS` | Maximum analytics operation duration |
| `CLIENT_ORIGIN` | Allowed frontend origin for CORS |
| `VITE_API_URL` | Backend API URL used by the Vite frontend |

`VITE_API_URL` is a frontend build-time variable. It must contain only the public backend URL, never credentials or secrets.

Render provides its own `PORT` environment variable.

## MongoDB Atlas and GridFS

ESS Sentinel uses MongoDB Atlas for database persistence and GridFS for file storage.

### Atlas Configuration

1. Create a MongoDB Atlas project and cluster.
2. Create a database user with appropriate permissions.
3. Configure Network Access to permit connections from the backend hosting environment.
4. Obtain the Node.js connection URI.
5. Configure `MONGO_URI` in the backend environment.

### GridFS Storage

GridFS is used to persist larger application artifacts, including:

- Original uploaded datasets
- Normalized CSV files
- Trained model bundles
- Screening results
- Generated analytics artifacts
- Backup-related files

This architecture is designed to prevent the loss of analytics files when a Render instance restarts or is redeployed.

**Important:** GridFS persistence must be validated against the actual MongoDB Atlas deployment. Passing mocked storage tests alone does not establish successful live database persistence.

## Online Deployment

The application uses separate frontend and backend deployments.

### Frontend — Vercel

1. Push the project to GitHub.
2. Import the repository into Vercel.
3. Set the frontend root directory to:

   ```text
   client
   ```

4. Configure the Vite build settings as required by the repository.
5. Add the environment variable:

   ```env
   VITE_API_URL=https://YOUR-RENDER-BACKEND.onrender.com
   ```

6. Deploy the frontend.
7. Note the stable production domain assigned by Vercel.

### Backend — Render

1. Create a new Web Service on Render.
2. Connect the GitHub repository.
3. Configure the correct build and start commands for the backend.
4. Add the required backend environment variables:

   ```env
   MONGO_URI=<YOUR_ATLAS_CONNECTION_STRING>
   MONGO_DB=ess_sentinel
   DEMO_MODE=true
   NODE_ENV=production
   PYTHON_BIN=python
   ML_TIMEOUT_MS=300000
   CLIENT_ORIGIN=https://YOUR-VERCEL-PRODUCTION-DOMAIN
   ```

5. Deploy the service.
6. Verify that the backend connects successfully to MongoDB Atlas.

### Deployment Notes

- Use the exact Vercel production domain in `CLIENT_ORIGIN`.
- Do not use temporary Vercel preview URLs as the permanent CORS origin.
- Do not store MongoDB credentials in Vercel frontend variables.
- Render's local filesystem is ephemeral on the free tier. Persistent analytics artifacts must be stored in GridFS.
- Render free-tier services may experience cold starts.
- Analytics operations can take longer than ordinary API requests; configure appropriate timeouts.
- Verify the live application after every production deployment.

## Migration from ESS Sentinel 2.0

The project includes migration utilities for transferring data from the earlier SQLite-based version.

The migration process is intended to:

- Read the legacy SQLite database.
- Reconstruct MongoDB catalog records.
- Remap legacy identifiers.
- Transfer supported CSV and model artifacts.
- Preserve historical events, reviews, and settings.

Migration utility:

```bash
python scripts/migrate_sqlite.py <PATH_TO_ESS_SENTINEL_2.0_WORKSPACE>
```

Use a separate, empty target database and preserve the original source workspace and backups.

Migration should be tested against a disposable database before being used with valuable data.

## Testing

Run the JavaScript test suite:

```bash
npm test
```

Run Python bridge tests:

```bash
python -m pytest tests/test_bridge.py -v
```

Run GridFS storage tests:

```bash
python -m pytest tests/test_gridfs_storage.py -v
```

Additional legacy analytics tests can be executed from:

```bash
cd ml-service/legacy
python -m pytest tests -v
```

### Test Coverage

The test suites cover areas including:

- API functionality and validation.
- Public demonstration access.
- Batch operations and historical references.
- Destructive-operation restrictions.
- Data ingestion and screening workflows.
- Model training and prediction.
- PDF and Excel report generation.
- GridFS artifact storage.
- React dashboard rendering and interactions.
- Backend failure and timeout handling.

**Test evidence and limitations:** Local automated tests do not automatically prove that the deployed application works against a live Atlas database. Production acceptance requires actual deployment testing, including artifact persistence across backend restarts.

## Troubleshooting

| Problem | Suggested check |
|---|---|
| Dashboard does not load | Check the Vercel deployment and browser console. |
| `Unable to resolve host` | Verify the backend URL, DNS, and service availability. |
| CORS error | Confirm `CLIENT_ORIGIN` matches the exact Vercel production domain. |
| Database unavailable | Verify `MONGO_URI`, database credentials, and Atlas Network Access. |
| Python runtime unavailable | Verify the Python version and `PYTHON_BIN`. |
| Missing screening results | Inspect the screening run, GridFS storage, and backend logs. |
| Analytics task already running | Wait for the current task to finish before retrying. |
| Report download fails | Check the report record, GridFS artifact, and backend logs. |
| Render cold start | Allow the backend time to start and retry the request. |
| Old login screen appears | Check that the latest frontend build is deployed and clear the browser cache. |
| Batch deletion returns 403 | Expected behavior in public demonstration mode. Archive the batch instead. |

## Project Structure

```text
ess-sentinel-web/
│
├── client/
│   ├── src/
│   ├── public/
│   └── dist/
│
├── server/
│   ├── app.js
│   ├── index.js
│   └── python.js
│
├── ml-service/
│   ├── bridge.py
│   ├── mongo_store.py
│   ├── gridfs_store.py
│   ├── requirements-tested.txt
│   └── legacy/
│
├── scripts/
│   ├── rebuild_demo.py
│   ├── migrate_sqlite.py
│   └── migrate_to_gridfs.py
│
├── tests/
│
├── docs/
│   ├── API.md
│   ├── MIGRATION.md
│   └── TEST_REPORT.md
│
├── .env.example
├── .gitignore
├── package.json
└── README.md
```

## Future Improvements

Potential future enhancements include:

- Full user identity and role-based access control.
- Durable background job queues.
- Multi-instance analytics coordination.
- Transactional consistency between catalog records and stored artifacts.
- Automated backup and recovery verification.
- Expanded integration and load testing.
- Monitoring, logging, and operational alerting.
- Improved model explainability and predictive maintenance capabilities.

## License

Add the applicable project license and attribution information before public distribution.

---

**ESS Sentinel Web 3.0 — From industrial data to actionable equipment intelligence.**
