"""Synthetic mechanisms, not physical device models or ISRO measurements."""
import numpy as np
import pandas as pd

PARAMETERS = {'Leakage current': ('uA', 10., 50.), 'Standby current': ('mA', 2., 10.),
              'Propagation delay': ('ns', 8., 40.)}
SCENARIOS = ['Normal Lot', 'Obvious Failure', 'Latent Defect', 'Early Warning', 'Population Anomaly']

def generate(n: int = 1200, lots: int = 12, defect_fraction: float = .15,
             noise: float = .015, severity: float = 1., seed: int = 42,
             limit_multiplier: float = 1., times=(0,24,96,168), parameters=None) -> pd.DataFrame:
    if n < 1 or lots < 1 or lots > n or not 0 <= defect_fraction <= 1:
        raise ValueError('Require n >= lots >= 1 and defect fraction between zero and one.')
    if noise < 0 or severity <= 0 or limit_multiplier <= 0 or tuple(sorted(set(times))) != tuple(times) or 0 not in times or 24 not in times or 168 not in times:
        raise ValueError('Invalid noise/severity/limit or time points; require sorted unique 0,24,168h.')
    rng = np.random.default_rng(seed)
    pars = list(parameters or PARAMETERS)
    kinds = ['high_value','latent','gradual','accelerating','sudden','decreasing']
    lot_effect = rng.normal(0,.04,lots)
    records=[]
    for i in range(n):
        lot=i%lots
        defective=rng.random()<defect_fraction
        kind=str(rng.choice(kinds)) if defective else 'normal'
        for par in pars:
            unit, base, maximum=PARAMETERS[par]
            baseline=base*(1+lot_effect[lot]+rng.normal(0,.035))
            strength=severity*rng.uniform(.8,1.2)
            row=dict(component_id=f'C-{i:06d}',lot_id=f'LOT-{lot:03d}',parameter=par,
                     part_family='CMOS-A',session_id='RUN-01',temperature=125.,voltage=3.3,
                     unit=unit,spec_min=0.,spec_max=maximum*limit_multiplier,
                     defect_label=int(defective),defect_type=kind,synthetic=True)
            for t in times:
                x=t/168
                value=baseline+base*.06*x
                if kind=='high_value': value+=base*3.4*strength
                elif kind=='latent': value+=base*3.55*strength*x**1.35
                elif kind=='gradual': value+=base*2.8*strength*x
                elif kind=='accelerating': value+=base*5.0*strength*x**1.5
                elif kind=='sudden': value+=base*5*strength*(t>=96)
                elif kind=='decreasing': value-=base*.75*strength*x
                if t==168: row['true_future_value']=max(0,value)
                row[f'value_{t}h']=max(0,value+rng.normal(0,base*noise))
            records.append(row)
    return pd.DataFrame(records)

def scenario(name: str, seed: int = 42) -> pd.DataFrame:
    if name not in SCENARIOS: raise ValueError('Unknown scenario.')
    d=generate(120,1,0,seed=seed,parameters=['Leakage current'])
    if name=='Normal Lot': return d
    rng=np.random.default_rng(seed)
    trajectories={'Obvious Failure':[11,56,59,63], 'Latent Defect':[10.5,13.2,25.6,47.8],
                  'Early Warning':[10.5,16,37,59], 'Population Anomaly':[44,45,46,47]}
    for j,t in enumerate([0,24,96,168]):
        d.loc[0,f'value_{t}h']=trajectories[name][j]+rng.normal(0,.05)
    d.loc[0,['defect_label','defect_type','true_future_value']]=[1,name,d.loc[0,'value_168h']]
    return d
