"""Transparent evidence weights and explicit overrides; never automatic disposition."""
from datetime import datetime, timezone
import hashlib,json
import numpy as np
import pandas as pd
from ess.anomaly.statistics import population
from ess.prediction.training import predict, dataset_hash
from ess.data.validation import require_valid
from ess.config import Policy
from ess.explainability.reasons import explain_row

LEVELS=['NORMAL','WATCH','HIGH RISK','CRITICAL']

def screen(data, bundle=None, policy=None, stage=24):
    policy=(policy or Policy()).validate(); d,_=require_valid(data)
    if stage not in [0,24,96,168]: raise ValueError('Screening stage must be 0,24,96,168h.')
    if bundle is not None and stage<bundle['manifest']['cutoff']:
        raise ValueError('Prediction model cutoff is later than screening stage; choose an earlier model or later stage.')
    d=d.reset_index(drop=True)
    out=d.join(population(d,stage,policy))
    if bundle is not None: out=out.join(predict(bundle,d))
    else:
        for c in ['predicted_168h','interval_lower','interval_upper','if_score','if_percentile']: out[c]=np.nan
        out['prediction_note']='No trained model; statistical screening only.'; out['out_of_domain']=False
    out['safety_threshold']=out.spec_min+policy.safety_fraction*(out.spec_max-out.spec_min)
    out['lower_safety_threshold']=out.spec_min+(1-policy.safety_fraction)*(out.spec_max-out.spec_min)
    # Lower safety applies only when there is a positive lower specification or negative range.
    lower_active=out.spec_min!=0
    observed=[f'value_{t}h' for t in [0,24,96,168] if t<=stage and f'value_{t}h' in out]
    out['static_violation']=out[observed].gt(out.spec_max,axis=0).any(axis=1)|out[observed].lt(out.spec_min,axis=0).any(axis=1)
    out['population_anomaly']=out.population_z.abs()>=policy.robust_z
    out['temporal_anomaly']=out.temporal_z.abs()>=policy.temporal_z
    out['ml_anomaly']=out.if_percentile>=policy.if_percentile
    out['predicted_crossing']=(out.predicted_168h>out.safety_threshold)|(lower_active&(out.predicted_168h<out.lower_safety_threshold))
    out['predicted_spec_crossing']=(out.predicted_168h>out.spec_max)|(out.predicted_168h<out.spec_min)
    out['predicted_margin']=np.minimum(out.safety_threshold-out.predicted_168h,
        np.where(lower_active,out.predicted_168h-out.lower_safety_threshold,np.inf))
    out['predicted_future_drift']=out.predicted_168h-out.value_0h
    out['lot_normalized_drift']=out.temporal_z
    out['population_points']=policy.population_weight*(out.population_z.abs()/policy.robust_z).clip(0,1).fillna(0)
    out['drift_points']=policy.drift_weight*(out.temporal_z.abs()/policy.temporal_z).clip(0,1).fillna(0)
    out['prediction_points']=policy.prediction_weight*out.predicted_crossing.astype(int)
    proximity=((out.current-out.spec_min)/(out.spec_max-out.spec_min)).clip(0,1)
    proximity=np.maximum(proximity,np.where(lower_active,1-proximity,0))
    out['proximity_points']=policy.proximity_weight*proximity.fillna(0)
    out['isolation_points']=policy.isolation_weight*((out.if_percentile-policy.if_percentile)/(100-policy.if_percentile)).clip(0,1).fillna(0)
    out['risk_score']=out[['population_points','drift_points','prediction_points','proximity_points','isolation_points']].sum(axis=1).round(2)
    out['status']=np.select([out.risk_score>=policy.critical_score,out.risk_score>=policy.high_score,out.risk_score>=policy.watch_score],
                            ['CRITICAL','HIGH RISK','WATCH'],default='NORMAL')
    # Explicit conservative overrides are shown independently of the additive score.
    high=out.predicted_crossing|out.population_anomaly|out.temporal_anomaly
    out.loc[high&out.status.isin(['NORMAL','WATCH']),'status']='HIGH RISK'
    out.loc[out.static_violation,'status']='CRITICAL'
    out['incomplete_assessment']=out.current.isna()|out.value_0h.isna()|out.value_24h.isna()|~out.peer_sufficient|out.out_of_domain|out.predicted_168h.isna()
    out.loc[(out.incomplete_assessment|out.ml_anomaly)&(out.status=='NORMAL'),'status']='WATCH'
    out['dynamic_flag']=out.status!='NORMAL'
    out['stage']=stage
    out['model_version']=bundle['manifest']['version'] if bundle else 'statistics-only'
    out['policy_hash']=hashlib.sha256(json.dumps(policy.__dict__,sort_keys=True).encode()).hexdigest()
    out['dataset_hash']=dataset_hash(d)
    out['timestamp']=datetime.now(timezone.utc).isoformat()
    out['explanation']=out.apply(explain_row,axis=1)
    return out

def component_summary(results):
    r=results.copy(); r['severity']=r.status.map({v:i for i,v in enumerate(LEVELS)})
    return r.sort_values(['severity','risk_score'],ascending=False).drop_duplicates('component_id')
