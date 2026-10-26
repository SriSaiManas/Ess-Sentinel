"""Adapter unit/integration tests use mongomock, NOT MongoDB persistence proof."""
import sys,os,json
from pathlib import Path
import pytest,mongomock
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'ml-service'))
import bridge,mongo_store
@pytest.fixture()
def env(tmp_path,monkeypatch):
 client=mongomock.MongoClient();monkeypatch.setattr(mongo_store,'MongoClient',lambda *a,**kw:client)
 monkeypatch.setenv('MONGO_URI','mongodb://unused');monkeypatch.setenv('MONGO_DB','unit_test');monkeypatch.setenv('ARTIFACT_DIR',str(tmp_path))
 bridge.main({'operation':'seed'});return tmp_path

def call(op,**args):return bridge.main({'operation':op,'args':args})
def test_seed_context_and_results(env):
 c=call('context');assert c['modelId'];r=call('results',runId=c['run']['id']);assert len(r)>100;assert all('risk_score' in x for x in r)
def test_quality_predict_model(env):
 c=call('context');q=call('quality',batchId=c['batchId']);assert not q['health']['errors'];r=call('predict',batchId=c['batchId'],modelId=c['modelId']);assert any(x['predicted_168h'] is not None for x in r);m=call('model',modelId=c['modelId']);assert isinstance(m['importance'],list)
def test_review_and_policy(env):
 c=call('context');rid=c['run']['id'];rows=call('results',runId=rid)
 call('review',runId=rid,componentId=rows[0]['component_id'],state='Reviewed',note='Evidence checked')
 with pytest.raises(ValueError):call('review',runId=rid,componentId='absent',state='Reviewed',note='')
 with pytest.raises(ValueError):call('policy',config={**c['policy'],'safety_fraction':2})
 comparison=call('policy',config={**c['policy'],'watch_score':15},batchId=c['batchId']);assert comparison
 call('policy',config=c['policy'],save=True)
def test_scenario_and_reports(env):
 c=call('context');pair=call('simulate',name='Latent Defect',seed=42);assert pair['baseline']!=pair['batchId']
 for kind in ['batch','component','quality','evaluation','audit','scenario']:
  args={'kind':kind,'runId':c['run']['id'],'batchId':c['batchId'],'modelId':c['modelId'],'componentId':call('results',runId=c['run']['id'])[0]['component_id']}
  r=call('report',**args)
  for ext in ['pdf','csv','xlsx']:assert (env/'reports'/r['reportId']/('report.'+ext)).stat().st_size>0
 backup=call('backup');assert (env/'reports'/backup['reportId']/'backup.zip').exists()
def test_real_training_adapter(env):
 c=call('context');m=call('train',batchId=c['batchId'],options={'candidate_names':['Linear'],'trees':20,'boosting_stages':20});assert m['modelId'];call('activate',modelId=m['modelId']);assert call('context')['modelId']==m['modelId']
def test_invalid_import(env):
 import base64
 with pytest.raises(ValueError):call('import',filename='sample.csv',content=base64.b64encode(b'bad\n1').decode(),name='Bad input',commit=True)
