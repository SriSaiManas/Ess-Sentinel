"""Migrate local filesystem artifacts into MongoDB GridFS for ESS Sentinel Web 3.0.
Idempotent and safe to run multiple times. Handles missing historical artifacts gracefully.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from pymongo import MongoClient

# Setup paths
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / 'ml-service'))

from gridfs_store import GridFSArtifactStore

def load_dotenv_if_exists():
    env_file = root_dir / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

def main():
    load_dotenv_if_exists()
    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        print("ERROR: MONGO_URI environment variable must be set.")
        sys.exit(1)

    db_name = os.environ.get('MONGO_DB', 'ess_sentinel')
    artifact_dir = Path(os.environ.get('ARTIFACT_DIR', root_dir / 'var/artifacts')).resolve()

    print(f"Connecting to MongoDB: {db_name}")
    print(f"Scanning artifact directory: {artifact_dir}")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    store = GridFSArtifactStore(db, artifact_dir)
    store._ensure_indexes()

    stats = {'migrated': 0, 'already_present': 0, 'missing': 0}

    # 1. Migrate Batches
    print("\n--- Verifying & Migrating Batches ---")
    batches = list(db.batches.find())
    for b in batches:
        bid = str(b['_id'])
        name = b.get('name', 'unnamed')
        for fname in ['normalized.csv', 'original.bin']:
            if store.db['fs.files'].count_documents({'metadata.category': 'batches', 'metadata.identifier': bid, 'metadata.filename': fname}) > 0:
                stats['already_present'] += 1
            else:
                local_file = artifact_dir / 'batches' / bid / fname
                if local_file.exists() and local_file.is_file():
                    store.save('batches', bid, fname, local_file.read_bytes(), extra_metadata={'batch_id': bid, 'migrated_at': datetime.now(timezone.utc).isoformat()})
                    print(f"  [+] Migrated batch {bid} ({name}) -> {fname}")
                    stats['migrated'] += 1
                else:
                    print(f"  [!] Note: Batch {bid} ({name}) artifact {fname} missing from local disk.")
                    stats['missing'] += 1

    # 2. Migrate Models
    print("\n--- Verifying & Migrating Models ---")
    models = list(db.models.find())
    for m in models:
        mid = str(m['_id'])
        for fname in ['model.joblib', 'manifest.json', 'comparison.csv', 'test_predictions.csv']:
            if store.db['fs.files'].count_documents({'metadata.category': 'models', 'metadata.identifier': mid, 'metadata.filename': fname}) > 0:
                stats['already_present'] += 1
            else:
                local_file = artifact_dir / 'models' / mid / fname
                if local_file.exists() and local_file.is_file():
                    store.save('models', mid, fname, local_file.read_bytes(), extra_metadata={'model_id': mid, 'migrated_at': datetime.now(timezone.utc).isoformat()})
                    print(f"  [+] Migrated model {mid} -> {fname}")
                    stats['migrated'] += 1
                else:
                    print(f"  [!] Note: Model {mid} artifact {fname} missing from local disk.")
                    stats['missing'] += 1

    # 3. Migrate Screening Runs
    print("\n--- Verifying & Migrating Screening Runs ---")
    runs = list(db.runs.find())
    for r in runs:
        rid = str(r['_id'])
        if store.db['fs.files'].count_documents({'metadata.category': 'runs', 'metadata.identifier': rid, 'metadata.filename': 'results.csv'}) > 0:
            stats['already_present'] += 1
        else:
            local_file = artifact_dir / 'runs' / rid / 'results.csv'
            if local_file.exists() and local_file.is_file():
                store.save('runs', rid, 'results.csv', local_file.read_bytes(), extra_metadata={'run_id': rid, 'batch_id': str(r.get('batch_id', '')), 'migrated_at': datetime.now(timezone.utc).isoformat()})
                print(f"  [+] Migrated run {rid} -> results.csv")
                stats['migrated'] += 1
            else:
                print(f"  [!] Note: Run {rid} results.csv missing from local disk.")
                stats['missing'] += 1

    # 4. Migrate Reports
    print("\n--- Verifying & Migrating Reports ---")
    reports = list(db.reports.find())
    for rep in reports:
        rid = str(rep['_id'])
        kind = rep.get('kind', 'batch')
        filenames = ['backup.zip'] if kind == 'backup' else ['report.pdf', 'report.xlsx', 'report.csv']
        for fname in filenames:
            if store.db['fs.files'].count_documents({'metadata.category': 'reports', 'metadata.identifier': rid, 'metadata.filename': fname}) > 0:
                stats['already_present'] += 1
            else:
                local_file = artifact_dir / 'reports' / rid / fname
                if local_file.exists() and local_file.is_file():
                    store.save('reports', rid, fname, local_file.read_bytes(), extra_metadata={'report_id': rid, 'kind': kind, 'migrated_at': datetime.now(timezone.utc).isoformat()})
                    print(f"  [+] Migrated report {rid} ({kind}) -> {fname}")
                    stats['migrated'] += 1
                else:
                    print(f"  [!] Note: Report {rid} ({kind}) artifact {fname} missing from local disk.")
                    stats['missing'] += 1

    print("\n=== Migration Summary ===")
    print(f"Artifacts newly migrated to GridFS: {stats['migrated']}")
    print(f"Artifacts already present in GridFS: {stats['already_present']}")
    print(f"Historical missing artifacts noted: {stats['missing']}")
    print("Migration completed successfully.")

if __name__ == '__main__':
    main()
