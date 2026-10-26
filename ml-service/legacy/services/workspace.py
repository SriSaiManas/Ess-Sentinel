"""Application orchestration. UI pages never duplicate engineering decisions."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,traceback,platform,importlib.metadata,os
import pandas as pd
from ess.data.synthetic import generate,scenario,SCENARIOS
from ess.data.validation import ingest
from ess.prediction.training import train,load_bundle,dataset_hash
from ess.risk.engine import screen,component_summary
from services.quality import inspect,timestamped
from services.store import Store,policy_id

ROOT=Path(__file__).resolve().parents[1]
APP_VERSION='2.0.0'

class Workspace:
    def __init__(self,root=None):
        self.store=Store(root or os.environ.get('ESS_DATA_DIR',str(ROOT/'outputs'/'workspace')))
    def bootstrap(self):
        s=self.store
        if not s.table('batches').empty: return
        d=timestamped(ingest((ROOT/'data/example_synthetic.csv').read_bytes(),'sample.csv'))
        bid=self.commit(d,'Reference demonstration','SYNTHETIC',metadata={'generator_seed':42,'components':2000,'lots':20,'bootstrap':True})
        if s.table('models').empty:
            try:
                mid=s.register_model(load_bundle(ROOT/'models/demo')); s.activate(mid,True)
            except ValueError as e: s.event('demo_model_load_failed',{'message':str(e)},outcome='error')
        self.screen(bid,24); s.set('active_batch',bid)
    def commit(self,data,name,source,raw=None,metadata=None):
        if not name.strip() or len(name)>120: raise ValueError('Batch name must contain 1–120 characters.')
        if len(data)>300000: raise ValueError('Maximum 300,000 measurement records per batch.')
        clean,health,issues=inspect(data)
        if health['errors']: raise ValueError('; '.join(health['errors']))
        bid=self.store.add_batch(clean,name,source,health['score'],raw,metadata)
        self.store.event('validation_completed',dict(score=health['score'],warnings=health['warnings']),bid)
        self.store.set('active_batch',bid)
        return bid
    def screen(self,bid,stage=24,mid=None,progress=None):
        s=self.store; d=s.data(bid); policy=s.policy()
        if progress: progress(.1,'Data and policy loaded')
        selected=s.get('active_model') if mid is None else mid
        bundle=s.model(selected) if selected else None
        if progress: progress(.25,'Computing population, drift and model evidence')
        result=screen(d,bundle,policy,stage)
        if progress: progress(.9,'Persisting completed assessment')
        rid=s.save_run(bid,selected,policy,stage,result)
        if progress: progress(1.0,'Screening complete')
        return rid
    def train(self,bid,**options):
        start=time.perf_counter(); data=self.store.data(bid)
        _,health,_=inspect(data,training=True)
        if health['errors']: raise ValueError('; '.join(health['errors']))
        bundle=train(data,policy=self.store.policy(),**options)
        bundle['manifest'].update(duration_seconds=time.perf_counter()-start,batch_id=bid,application_version=APP_VERSION)
        mid=self.store.register_model(bundle)
        self.store.event('model_training_completed',dict(model_id=mid,duration=bundle['manifest']['duration_seconds']),bid)
        return mid
    def simulate(self,name,seed=42,n=600,lots=12,noise=.015,severity=1.,defect_fraction=.15):
        if name in SCENARIOS:
            base=timestamped(scenario('Normal Lot',seed)); sim=timestamped(scenario(name,seed))
            settings={'scenario':name,'seed':seed,'components':120,'lots':1,'parameter':'Leakage current','fixed_recipe':True}
        else:
            base=timestamped(generate(n,lots,0,noise=.015,seed=seed))
            sim=timestamped(generate(n,lots,defect_fraction,noise=noise,severity=severity,seed=seed))
            if name=='Missing measurements': sim.loc[sim.index[::13],'value_24h']=float('nan')
            elif name not in ['Mixed-quality population','Elevated measurement variation']: raise ValueError('Unknown scenario.')
            settings=dict(scenario=name,seed=seed,components=n,lots=lots,noise=noise,severity=severity,defect_fraction=defect_fraction)
        baseline=self.commit(base,name+' · baseline','SYNTHETIC',metadata=settings|{'role':'baseline'})
        bid=self.commit(sim,name,'SYNTHETIC',metadata=settings|{'baseline_batch':baseline})
        self.store.event('scenario_executed',settings|{'baseline_batch':baseline},bid)
        # Preserve active model; a 96h active model requires stage 96.
        model=self.store.model(self.store.get('active_model')); stage=model['manifest']['cutoff'] if model else 24
        self.screen(baseline,stage); self.screen(bid,stage)
        self.store.set('active_batch',bid)
        return baseline,bid
    def reset_demo(self,confirmed=False):
        if not confirmed: raise ValueError('Confirm creation of a fresh demo workspace.')
        # Non-destructive reset: add a fresh demo batch; keep all imports, runs and audit.
        d=timestamped(generate(1200,12)); bid=self.commit(d,'Fresh demo population','SYNTHETIC',metadata={'generator_seed':42,'reset':True})
        self.store.event('demo_reset',{'preserved_existing_batches':True},bid)
        return bid
    def error(self,operation,exc,bid=''):
        token=__import__('uuid').uuid4().hex[:8]
        # No environment dump or uploaded payload in logs.
        self.store.event('operation_failed',dict(reference=token,operation=operation,error_type=type(exc).__name__,message=str(exc)[:1000]),bid,outcome='error')
        return token
    def diagnostics(self):
        packages=['streamlit','numpy','pandas','scikit-learn','scipy','plotly','reportlab','openpyxl','pyarrow','pytest']
        rows=[]
        for p in packages:
            try: version=importlib.metadata.version(p)
            except importlib.metadata.PackageNotFoundError: version='NOT INSTALLED'
            rows.append({'dependency':p,'version':version})
        probe=self.store.root/'write-check.tmp'
        try: probe.write_text('ESS diagnostics',encoding='utf-8'); writable=True
        except OSError: writable=False
        finally: probe.unlink(missing_ok=True)
        self.store.policy().validate()
        return dict(python=platform.python_version(),os=platform.system(),app=APP_VERSION,writable=writable,dependencies=rows,schema_version=1)
    def smoke(self):
        d=scenario('Latent Defect'); r=screen(d)
        if not r.iloc[0].temporal_anomaly: raise RuntimeError('Latent-defect smoke check failed.')
        self.store.event('backend_smoke_passed',{'records':len(r)})
        return {'records':len(r),'population_anomaly':bool(r.iloc[0].population_anomaly),'temporal_anomaly':bool(r.iloc[0].temporal_anomaly),'status':r.iloc[0].status}
