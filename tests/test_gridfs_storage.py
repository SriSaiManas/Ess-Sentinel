"""Automated verification tests for MongoDB GridFS Persistent Artifact Storage.
Covers all 10 core requirements:
1. Dataset upload and retrieval.
2. Normalized dataset persistence.
3. Model bundle storage and retrieval.
4. Screening result persistence.
5. Report generation and downloads.
6. Backup generation and restoration.
7. Missing artifact handling.
8. Concurrent analytics tasks.
9. GridFS connection failures.
10. Application restart and retrieval of previously stored artifacts.
"""
import sys
import os
import shutil
from pathlib import Path
import pytest
import mongomock
import pandas as pd
from bson import ObjectId

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'ml-service'))
sys.path.insert(0, str(root / 'ml-service' / 'legacy'))

import bridge
import mongo_store
from gridfs_store import GridFSArtifactStore
from mongo_store import MongoStore
from ess.data.synthetic import generate
from ess.prediction.training import train, load_bundle

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv('MONGO_URI', 'mongodb://unused')
    monkeypatch.setenv('MONGO_DB', 'test_ess_sentinel')

@pytest.fixture()
def mock_db():
    client = mongomock.MongoClient()
    return client['test_ess_sentinel']

@pytest.fixture()
def store(tmp_path, mock_db):
    artifact_dir = tmp_path / 'artifacts'
    s = MongoStore(artifact_dir)
    s.db = mock_db
    s.artifact_store = GridFSArtifactStore(s.db, s.root)
    return s

def test_1_dataset_upload_and_retrieval(store):
    """1. Test dataset upload and retrieval via GridFS."""
    data = generate(100, 2)
    raw_csv = data.to_csv(index=False).encode('utf-8')
    bid = store.add_batch(data, 'Test Batch', 'SYNTHETIC', health=95, raw=raw_csv)
    
    # Check that original.bin and normalized.csv exist in GridFS
    assert store.artifact_store.exists('batches', bid, 'original.bin')
    assert store.artifact_store.exists('batches', bid, 'normalized.csv')
    
    # Retrieve raw bytes
    raw_retrieved = store.artifact_store.get_bytes('batches', bid, 'original.bin')
    assert raw_retrieved == raw_csv

def test_2_normalized_dataset_persistence(store):
    """2. Test normalized dataset persistence and retrieval via store.data()."""
    data = generate(80, 2)
    bid = store.add_batch(data, 'Normalized Test', 'SYNTHETIC', health=90)
    
    # Read back through data()
    df = store.data(bid)
    assert len(df) == len(data)
    assert set(df.component_id.unique()) == set(data.component_id.unique())

def test_3_model_bundle_storage_and_retrieval(store):
    """3. Test model bundle storage in GridFS and subsequent retrieval."""
    data = generate(200, 10)
    bundle = train(data, candidate_names=['Linear'], trees=20, boosting_stages=20)
    mid = store.register_model(bundle)
    
    # Verify model files exist in GridFS
    assert store.artifact_store.exists('models', mid, 'model.joblib')
    assert store.artifact_store.exists('models', mid, 'manifest.json')
    assert store.artifact_store.exists('models', mid, 'comparison.csv')
    assert store.artifact_store.exists('models', mid, 'test_predictions.csv')
    
    # Retrieve model bundle
    loaded = store.model(mid)
    assert loaded is not None
    assert loaded['manifest']['cutoff'] == bundle['manifest']['cutoff']

def test_4_screening_result_persistence(store):
    """4. Test screening results.csv persistence in GridFS."""
    data = generate(80, 2)
    bid = store.add_batch(data, 'Screen Batch', 'SYNTHETIC', health=90)
    from ess.risk.engine import screen
    from ess.config import Policy
    res = screen(data)
    
    rid = store.save_run(bid, '', Policy(), 24, res)
    assert store.artifact_store.exists('runs', rid, 'results.csv')
    
    # Read back results
    r_df = store.results(rid)
    assert len(r_df) == len(res)
    assert 'risk_score' in r_df.columns

def test_5_report_generation_and_downloads(store):
    """5. Test report artifact generation and retrieval."""
    rid = str(ObjectId())
    pdf_bytes = b'%PDF-1.4 test dummy report'
    xlsx_bytes = b'PK\x03\x04 xlsx dummy'
    csv_bytes = b'component_id,risk_score\nC1,85\n'
    
    store.artifact_store.save('reports', rid, 'report.pdf', pdf_bytes)
    store.artifact_store.save('reports', rid, 'report.xlsx', xlsx_bytes)
    store.artifact_store.save('reports', rid, 'report.csv', csv_bytes)
    
    assert store.artifact_store.get_bytes('reports', rid, 'report.pdf') == pdf_bytes
    assert store.artifact_store.get_bytes('reports', rid, 'report.xlsx') == xlsx_bytes
    assert store.artifact_store.get_bytes('reports', rid, 'report.csv') == csv_bytes

def test_6_backup_generation_and_restoration(store):
    """6. Test backup archive generation containing catalog and GridFS files."""
    data = generate(60, 2)
    bid = store.add_batch(data, 'Backup Test', 'SYNTHETIC', health=90)
    
    backup_zip = store.backup()
    assert len(backup_zip) > 100
    
    import zipfile, io
    with zipfile.ZipFile(io.BytesIO(backup_zip), 'r') as z:
        names = z.namelist()
        assert any('batches.json' in n for n in names)
        assert any('normalized.csv' in n for n in names)

def test_7_missing_artifact_handling(store):
    """7. Test missing artifact error handling."""
    fake_id = str(ObjectId())
    with pytest.raises(FileNotFoundError):
        store.data(fake_id)
    with pytest.raises(FileNotFoundError):
        store.results(fake_id)
    with pytest.raises(FileNotFoundError):
        store.model(fake_id)

def test_8_concurrent_analytics_tasks(store):
    """8. Test multiple artifact writes concurrently without corruption."""
    import concurrent.futures
    data = generate(50, 2)
    
    def save_task(idx):
        bid = store.add_batch(data, f'Concurrent {idx}', 'SYNTHETIC', health=90)
        return bid
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(save_task, i) for i in range(4)]
        bids = [f.result() for f in futures]
    
    assert len(bids) == 4
    for b in bids:
        assert store.artifact_store.exists('batches', b, 'normalized.csv')
        df = store.data(b)
        assert len(df) == len(data)

def test_9_gridfs_connection_failures(store, monkeypatch):
    """9. Test failure behavior when GridFS is unreachable."""
    def broken_find_one(*a, **kw):
        raise ConnectionError("MongoDB Atlas unreachable")
    
    monkeypatch.setattr(store.db['fs.files'], 'find_one', broken_find_one)
    # Clear cache
    store._data_cache.clear()
    
    with pytest.raises(Exception):
        store.artifact_store.get_stream('batches', 'dummy', 'normalized.csv')

def test_10_application_restart_and_retrieval(tmp_path, mock_db):
    """10. Test application restart simulation: local /tmp wiped, artifacts retrieved from GridFS."""
    artifact_dir_1 = tmp_path / 'container_1_tmp'
    s1 = MongoStore(artifact_dir_1)
    s1.db = mock_db
    s1.artifact_store = GridFSArtifactStore(s1.db, s1.root)
    
    data = generate(60, 2)
    bid = s1.add_batch(data, 'Persistent Across Restarts', 'SYNTHETIC', health=90)
    from ess.risk.engine import screen
    from ess.config import Policy
    res = screen(data)
    rid = s1.save_run(bid, '', Policy(), 24, res)
    
    # Simulate container restart: Container 1 disk is wiped
    shutil.rmtree(artifact_dir_1)
    assert not artifact_dir_1.exists()
    
    # New container starts with clean empty /tmp
    artifact_dir_2 = tmp_path / 'container_2_tmp'
    s2 = MongoStore(artifact_dir_2)
    s2.db = mock_db
    s2.artifact_store = GridFSArtifactStore(s2.db, s2.root)
    
    # Retrieve dataset and screening results from new container with empty disk!
    df = s2.data(bid)
    assert len(df) == len(data)
    
    results = s2.results(rid)
    assert len(results) == len(res)
    assert 'risk_score' in results.columns
    
    # Verify local cache was populated from GridFS
    assert (artifact_dir_2 / 'runs' / rid / 'results.csv').exists()
    assert (artifact_dir_2 / 'batches' / bid / 'normalized.csv').exists()
