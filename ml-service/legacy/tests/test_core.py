from dataclasses import replace
from io import BytesIO
import numpy as np
import pandas as pd
import pytest
from ess.data.synthetic import generate,scenario
from ess.data.validation import ingest,validate,require_valid
from ess.features.engineering import features,temporal
from ess.config import Policy
from ess.risk.engine import screen,component_summary
from ess.prediction.training import predict,train,save_bundle,load_bundle
from ess.prediction.evaluation import compare_screening,classification
from ess.reports.export import pdf_report,csv_bytes
from ess.audit import Audit

def test_generator_reproducible():
    a=generate(100,10); pd.testing.assert_frame_equal(a,generate(100,10))
    assert len(a)==300 and a.component_id.nunique()==100
    assert a.defect_label.isin([0,1]).all() and a.defect_label.sum()>0
    assert set(a.defect_type)-{'normal'}
@pytest.mark.parametrize('kwargs',[{'n':0},{'lots':2000},{'defect_fraction':2},{'noise':-1},{'times':(0,168,24)}])
def test_generator_rejects_bad_config(kwargs):
    with pytest.raises(ValueError): generate(**kwargs)
def test_csv_and_excel(dataset):
    assert len(ingest(dataset.to_csv(index=False).encode(),'x.csv'))==len(dataset)
    buf=BytesIO(); dataset.head(10).to_excel(buf,index=False)
    assert len(ingest(buf.getvalue(),'x.xlsx'))==10
@pytest.mark.parametrize('content,name',[(b'','x.csv'),(b'bad','x.exe'),(b'"unclosed','x.csv'),(b'bad','x.xlsx')])
def test_invalid_file(content,name):
    with pytest.raises(ValueError): ingest(content,name)
def test_map_and_missing_columns(dataset):
    raw=dataset.rename(columns={'component_id':'ID'})
    d=ingest(raw.to_csv(index=False).encode(),'x.csv',{'ID':'component_id'})
    assert not validate(d)[1]['errors']
    assert validate(dataset.drop(columns='value_24h'))[1]['errors']
def test_invalid_numeric_negative_infinite(dataset):
    for val in ['oops',-5,np.inf]:
        d=dataset.copy(); d['value_24h']=d.value_24h.astype(object); d.loc[0,'value_24h']=val
        assert validate(d)[1]['errors']
def test_missing_duplicates_units_time(dataset):
    d=dataset.copy(); d.loc[0,'value_24h']=np.nan
    assert any('value_24h contains 1 missing' in x for x in validate(d)[1]['warnings'])
    assert validate(pd.concat([d,d.iloc[:1]]))[1]['errors']
    d=dataset.copy(); d.loc[0,'unit']='A'; assert validate(d)[1]['errors']
    d=dataset.rename(columns={'value_96h':'value_-96h'}); assert validate(d)[1]['errors']
def test_feature_math_and_leakage(dataset):
    d=dataset.copy(); d.loc[0,['value_0h','value_24h']]=[10,13]
    f=features(d); assert f.loc[0,'early_drift']==3 and f.loc[0,'percentage_drift']==30
    assert f.loc[0,'slope_0_24']==.125
    d.value_168h=9999; d.value_96h=-999; d.defect_label=1; d.true_future_value=555
    pd.testing.assert_frame_equal(f,features(d))
    assert not set(['value_168h','value_96h','defect_label','true_future_value'])&set(f)
    assert temporal(d,24).loc[0,'absolute_drift']==3

def test_population_scenario():
    r=screen(scenario('Population Anomaly'))
    assert r.iloc[0].population_anomaly and not r.iloc[0].static_violation
    assert r.iloc[0].status=='HIGH RISK' and not r.iloc[1].population_anomaly

def test_latent_and_normal():
    assert screen(scenario('Latent Defect')).iloc[0].temporal_anomaly
    assert screen(scenario('Normal Lot')).population_anomaly.mean()<.05

def test_policy_rejects():
    for kwargs in [{'safety_fraction':2},{'watch_score':99},{'population_weight':99},{'robust_z':float('nan')}]:
        with pytest.raises(ValueError): replace(Policy(),**kwargs).validate()

def test_static_override():
    r=screen(scenario('Obvious Failure')); assert r.iloc[0].status=='CRITICAL'
    assert 'specification violation' in r.iloc[0].explanation

def test_training_prediction_and_split(dataset,bundle):
    p=predict(bundle,dataset); assert len(p)==len(dataset) and p.predicted_168h.notna().all()
    groups=list(bundle['manifest']['split'].values())
    for i,a in enumerate(groups):
        for b in groups[i+1:]: assert not set(a)&set(b)
    assert bundle['comparison'].MAE.ge(0).all()
    assert 'value_168h' not in bundle['manifest']['features']

def test_prediction_missing_and_unknown(dataset,bundle):
    d=dataset.copy(); d.loc[0,'value_24h']=np.nan; d.loc[1,'parameter']='Unknown'
    p=predict(bundle,d); assert np.isnan(p.loc[0,'predicted_168h']) and np.isnan(p.loc[1,'predicted_168h'])
    assert p.loc[0,'prediction_note'] and p.loc[1,'prediction_note']

def test_96_optional_at_24(dataset,bundle):
    assert predict(bundle,dataset.drop(columns='value_96h')).predicted_168h.notna().all()

def test_unsupported_range_and_small_peers(dataset,bundle):
    d=dataset.copy(); d.loc[0,'value_24h']=1e8
    p=predict(bundle,d); assert p.loc[0,'out_of_domain'] and np.isnan(p.loc[0,'interval_lower'])
    r=screen(dataset.iloc[:3],bundle); assert r.incomplete_assessment.all() and r.dynamic_flag.all()

def test_insufficient_training_and_empty(dataset):
    with pytest.raises(ValueError): train(dataset.iloc[:15])
    with pytest.raises(ValueError): screen(dataset.iloc[:0])

def test_asof_guard(dataset,bundle):
    with pytest.raises(ValueError): screen(dataset,bundle,stage=0)
    d=dataset.copy(); a=screen(d,bundle,stage=24); d.value_168h=1e9; d.value_96h=1e9
    b=screen(d,bundle,stage=24); np.testing.assert_allclose(a.risk_score,b.risk_score)
    assert (a.status==b.status).all()

def test_metric_edge_cases():
    m=classification([0,0],[0,1],[.1,.2]); assert m['Recall'] is None and m['ROC_AUC'] is None
    m=classification([0,0,1,1],[0,1,0,1]); assert m['FNR']==.5 and m['FPR']==.5

def test_integration_flow(dataset,bundle,tmp_path):
    clean,_=require_valid(ingest(dataset.to_csv(index=False).encode(),'sample.csv'))
    save_bundle(bundle,tmp_path/'model'); b=load_bundle(tmp_path/'model')
    r=screen(clean,b); assert r.explanation.str.len().gt(0).all()
    assert len(component_summary(r))==800 and not compare_screening(r).empty
    assert pdf_report(r[r.component_id==r.iloc[0].component_id]).startswith(b'%PDF')
    assert len(csv_bytes(r))>1000
    log=Audit(tmp_path/'audit.sqlite'); log.record('screening',{'n':len(r)}); assert len(log.read())==1
    with pytest.raises(ValueError): load_bundle(tmp_path/'missing')

def test_formula_injection():
    assert b"'=HYPERLINK" in csv_bytes(pd.DataFrame({'id':['=HYPERLINK(1)']}))

def test_label_free_screening(dataset,bundle):
    a=screen(dataset,bundle); b=screen(dataset.drop(columns=['defect_label','defect_type','true_future_value']),bundle)
    np.testing.assert_allclose(a.risk_score,b.risk_score); assert compare_screening(b).empty

def test_parameter_models_do_not_share_state(dataset,bundle):
    test=dataset[dataset.lot_id.isin(bundle['manifest']['split']['test'])]
    pred=predict(bundle,test)
    actual=test[['component_id','parameter']].copy(); actual['prediction']=pred.predicted_168h
    joined=bundle['test_predictions'].merge(actual,on=['component_id','parameter'])
    np.testing.assert_allclose(joined.predicted,joined.prediction,rtol=1e-12)
    objects=[id(m['model'].named_steps['model']) for m in bundle['units'].values()]
    assert len(set(objects))==len(objects)

def test_96h_training_and_missing_inputs(dataset):
    b=train(dataset,cutoff=96)
    assert 'value_96h' in b['manifest']['features'] and 'value_168h' not in b['manifest']['features']
    with pytest.raises(ValueError): screen(dataset,b,stage=24)
    d=dataset.copy(); d.loc[0,'value_96h']=np.nan
    assert np.isnan(predict(b,d).loc[0,'predicted_168h'])
    assert screen(d,b,stage=96).iloc[0].dynamic_flag

def test_policy_changes_real_decisions(bundle):
    d=scenario('Latent Defect')
    a=screen(d,bundle,Policy()); b=screen(d,bundle,replace(Policy(),safety_fraction=1.0))
    assert a.iloc[0].safety_threshold!=b.iloc[0].safety_threshold
    assert a.iloc[0].policy_hash!=b.iloc[0].policy_hash

def test_cross_lot_duplicate_training_guard(dataset):
    copy=dataset.iloc[:3].copy(); copy.component_id='copied'; copy.lot_id='another-lot'
    d=pd.concat([dataset,copy],ignore_index=True)
    assert any('identical measurement signatures' in x for x in validate(d,training=True)[1]['errors'])
