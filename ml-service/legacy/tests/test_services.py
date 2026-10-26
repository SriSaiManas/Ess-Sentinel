from io import BytesIO
from dataclasses import replace
import zipfile,json
import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from services.workspace import Workspace
from services.store import Store,atomic,policy_id
from services.quality import inspect,timestamped
from services.reports import excel_bytes,report_pdf
from ess.data.synthetic import generate,scenario
from ess.data.validation import ingest
from ess.prediction.training import train
from ess.config import Policy
from ess.risk.engine import screen

@pytest.fixture
def workspace(tmp_path): return Workspace(tmp_path/'workspace')

def test_store_roundtrip_original_integrity(workspace,dataset):
    raw=b'original bytes preserved'
    bid=workspace.commit(dataset,'New batch','UPLOADED',raw=raw)
    pd.testing.assert_frame_equal(workspace.store.data(bid),ingest(dataset.to_csv(index=False).encode(),'x.csv'))
    assert workspace.store.path('batches',bid,'original.bin').read_bytes()==raw
    again=Workspace(workspace.store.root);assert len(again.store.table('batches'))==1
    assert again.store.get('active_batch')==bid

@pytest.mark.parametrize('identifier',['../x','a/b','a\\b','../../models/x','',':bad'])
def test_path_traversal_rejected(workspace,identifier):
    with pytest.raises(ValueError):workspace.store.path('batches',identifier,'normalized.csv')

def test_timestamp_quality(dataset):
    d=timestamped(dataset);_,h,issues=inspect(d);assert not h['errors']
    d.loc[0,'timestamp_24h']='invalid';assert inspect(d)[1]['errors']
    d=timestamped(dataset);d.loc[0,'timestamp_24h']=d.loc[0,'timestamp_0h'];assert inspect(d)[1]['errors']

def test_quality_invalid_numbers_and_bounds(dataset):
    d=dataset.copy();d.spec_min=d.spec_min.astype(str);d.loc[0,'spec_min']='broken'
    clean,h,issues=inspect(d);assert h['errors'] and (issues.issue=='Invalid numeric value').any()

def test_string_ids_preserved():
    d=generate(50,5,parameters=['Leakage current']);d.component_id=[f'{i:04d}' for i in range(50)]
    result=ingest(d.to_csv(index=False).encode(),'input.csv');assert result.component_id.iloc[0]=='0000'

def test_model_explicit_activation(workspace,bundle):
    mid=workspace.store.register_model(bundle);assert workspace.store.get('active_model') is None
    with pytest.raises(ValueError):workspace.store.activate(mid)
    workspace.store.activate(mid,True);assert workspace.store.get('active_model')==mid

def test_run_provenance_and_review(workspace,dataset,bundle):
    bid=workspace.commit(dataset,'Batch','SYNTHETIC');mid=workspace.store.register_model(bundle);workspace.store.activate(mid,True)
    rid=workspace.screen(bid);run=workspace.store.latest_run(bid)
    assert run['id']==rid and run['model_id']==mid and run['policy_id']==policy_id(Policy())
    r=workspace.store.results(rid);workspace.store.review(rid,r.component_id.iloc[0],'In review','Check chamber record')
    assert len(workspace.store.table('reviews'))==1
    with pytest.raises(ValueError):workspace.store.review(rid,'not present','Reviewed','wrong')
    with pytest.raises(ValueError):workspace.store.review(rid,r.component_id.iloc[0],'Released','not allowed')

def test_policy_version_and_immutable_run(workspace,dataset,bundle):
    bid=workspace.commit(dataset,'Batch','SYNTHETIC');mid=workspace.store.register_model(bundle);workspace.store.activate(mid,True)
    rid=workspace.screen(bid);before=workspace.store.results(rid)
    draft=replace(Policy(),safety_fraction=.95)
    with pytest.raises(ValueError):workspace.store.save_policy(draft)
    pid=workspace.store.save_policy(draft,True);assert pid!=policy_id(Policy())
    pd.testing.assert_frame_equal(before,workspace.store.results(rid))

def test_backup_is_complete(workspace,dataset):
    bid=workspace.commit(dataset,'Batch','SYNTHETIC');content=workspace.store.backup()
    with zipfile.ZipFile(BytesIO(content)) as z:
        assert 'catalog.sqlite' in z.namelist()
        assert f'batches/{bid}/original.bin' in z.namelist()
        assert z.testzip() is None

def test_safe_reset_does_not_delete(workspace,dataset):
    workspace.commit(dataset,'Keep me','UPLOADED')
    with pytest.raises(ValueError):workspace.reset_demo()
    workspace.reset_demo(True);assert len(workspace.store.table('batches'))==2
    assert workspace.store.table('batches').name.eq('Keep me').any()

def test_excel_formula_protection():
    raw=pd.DataFrame({'user':['=HYPERLINK("x")',' @SUM(1)','ordinary'],'value':[1,2,3]})
    wb=load_workbook(BytesIO(excel_bytes({'Sheet':raw})))
    assert wb.active['A2'].data_type!='f' and wb.active['A3'].value.startswith("'")
    assert wb.active['B2'].value==1

def test_branded_pdf(workspace,dataset,bundle):
    r=screen(dataset,bundle).iloc[:3]
    content=report_pdf('Component inspection',{'Batch':'Synthetic'}, {'Measurements':r[['component_id','parameter','risk_score','status']]},r)
    assert content.startswith(b'%PDF') and len(content)>10000

def test_training_progress_seed_and_linear_winner(dataset):
    events=[];b=train(dataset,candidate_names=['Linear'],seed=19,progress=lambda value,text:events.append((value,text)))
    assert b['manifest']['seed']==19 and events[-1][0]==1
    assert len(b['comparison'].query("split=='test'"))==3
    assert all(a[0]<=b[0] for a,b in zip(events,events[1:]))

@pytest.mark.parametrize('name',['Normal Lot','Latent Defect','Missing measurements','Elevated measurement variation','Mixed-quality population'])
def test_scenario_pair(workspace,name):
    baseline,sim=workspace.simulate(name,n=120,lots=12)
    assert baseline!=sim and workspace.store.latest_run(sim)
    assert workspace.store.table('batches').source.eq('SYNTHETIC').all()

def test_error_and_diagnostics(workspace):
    ref=workspace.error('test',ValueError('Bad data'));assert ref
    assert workspace.store.table('events').iloc[0].outcome=='error'
    assert workspace.diagnostics()['writable']
    assert workspace.smoke()['temporal_anomaly']

def test_failed_import_is_not_committed(workspace,dataset):
    invalid=dataset.drop(columns='spec_max')
    with pytest.raises(ValueError):workspace.commit(invalid,'Invalid','UPLOADED')
    assert workspace.store.table('batches').empty

def test_invalid_train_config(dataset):
    with pytest.raises(ValueError):train(dataset,seed=-1)
    with pytest.raises(ValueError):train(dataset,candidate_names=[])
    with pytest.raises(ValueError):train(dataset,trees=0)
