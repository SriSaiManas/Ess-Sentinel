"""Contemporaneous peer statistics; never mix units, conditions, or sessions."""
import numpy as np
import pandas as pd
from ess.config import Policy
from ess.features.engineering import temporal

GROUP=['lot_id','part_family','parameter','unit','temperature','voltage','session_id']

def population(d: pd.DataFrame, stage: int, policy: Policy) -> pd.DataFrame:
    t=temporal(d,stage)
    work=d[GROUP].join(t[['current','absolute_drift']])
    out=t.copy()
    for col,prefix in [('current','population'),('absolute_drift','temporal')]:
        g=work.groupby(GROUP,dropna=False)[col]
        med=g.transform('median')
        mad=g.transform(lambda x:(x-x.median()).abs().median())
        q1=g.transform('quantile',q=.25); q3=g.transform('quantile',q=.75)
        scale=(1.4826*mad).clip(lower=(d.spec_max-d.spec_min)*policy.scale_floor_fraction)
        out[prefix+'_median']=med; out[prefix+'_mad']=mad
        out[prefix+'_q1']=q1; out[prefix+'_q3']=q3
        out[prefix+'_p01']=g.transform('quantile',q=.01)
        out[prefix+'_p99']=g.transform('quantile',q=.99)
        out[prefix+'_z']=(work[col]-med)/scale
        out[prefix+'_percentile']=g.rank(pct=True)*100
        out[prefix+'_iqr_outlier']=(work[col]<q1-1.5*(q3-q1))|(work[col]>q3+1.5*(q3-q1))
        out['peer_count']=g.transform('count')
    out['peer_sufficient']=out.peer_count>=policy.minimum_peers
    out.loc[~out.peer_sufficient,['population_z','temporal_z']]=np.nan
    out['trajectory_residual']=out.absolute_drift-out.temporal_median
    return out
