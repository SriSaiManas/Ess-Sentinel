"""Strict as-of feature whitelist. Neither labels nor future values enter X."""
import numpy as np
import pandas as pd

CATEGORIES=['parameter','part_family']

def features(d: pd.DataFrame, cutoff: int=24) -> pd.DataFrame:
    if cutoff not in [24,96]: raise ValueError('Prediction cutoff must be 24 or 96 hours.')
    out=pd.DataFrame(index=d.index)
    for c in ['value_0h','value_24h','temperature','voltage']:
        out[c]=pd.to_numeric(d[c],errors='coerce')
    out['early_drift']=out.value_24h-out.value_0h
    denom=out.value_0h.abs().where(out.value_0h.abs()>1e-9)
    out['percentage_drift']=100*out.early_drift/denom
    out['slope_0_24']=out.early_drift/24
    out['normalized_drift']=out.early_drift/(out.value_0h.abs()+1)
    if cutoff==96:
        out['value_96h']=d.get('value_96h',np.nan)
        out['slope_24_96']=(out.value_96h-out.value_24h)/72
        out['acceleration']=(out.slope_24_96-out.slope_0_24)/60
    for c in CATEGORIES: out[c]=d[c].astype(str)
    return out.replace([np.inf,-np.inf],np.nan)

def temporal(d: pd.DataFrame, stage: int) -> pd.DataFrame:
    out=pd.DataFrame(index=d.index)
    out['current']=d.get(f'value_{stage}h',pd.Series(np.nan,index=d.index))
    out['absolute_drift']=out.current-d.value_0h
    out['percentage_drift']=100*out.absolute_drift/d.value_0h.abs().replace(0,np.nan)
    out['overall_slope']=out.absolute_drift/max(stage,1)
    for a,b in [(0,24),(24,96),(96,168)]:
        if b<=stage and f'value_{b}h' in d and f'value_{a}h' in d:
            out[f'slope_{a}_{b}']=(d[f'value_{b}h']-d[f'value_{a}h'])/(b-a)
    if 'slope_24_96' in out: out['acceleration']=(out.slope_24_96-out.slope_0_24)/60
    out['normalized_drift']=out.absolute_drift/(d.spec_max-d.spec_min)
    return out
