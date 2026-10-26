"""Lot-disjoint model selection, untouched test evaluation and local persistence."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error
from sklearn.inspection import permutation_importance
from ess.features.engineering import features, CATEGORIES
from ess.data.validation import require_valid
from ess.config import Policy

SEED=42

def dataset_hash(d):
    return hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()

def metrics(y,p):
    return dict(MAE=float(mean_absolute_error(y,p)),RMSE=float(np.sqrt(mean_squared_error(y,p))),
                R2=float(r2_score(y,p)) if len(y)>1 else None,
                MedianAE=float(median_absolute_error(y,p)))

def processor(X):
    numeric=[c for c in X if c not in CATEGORIES]
    return ColumnTransformer([('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),
        ('scale',StandardScaler())]),numeric),('category',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CATEGORIES)])

def lot_split(d, seed=SEED):
    lots=np.array(sorted(d.lot_id.unique())); np.random.default_rng(seed).shuffle(lots)
    n=len(lots); v=max(1,int(n*.15)); c=max(1,int(n*.15)); t=max(1,int(n*.2))
    groups={'train':lots[:n-v-c-t], 'validation':lots[n-v-c-t:n-c-t],
            'calibration':lots[n-c-t:n-t], 'test':lots[n-t:]}
    if min(map(len,groups.values()))<1: raise ValueError('Insufficient independent lots.')
    return {k:list(map(str,x)) for k,x in groups.items()}

def train(data: pd.DataFrame, cutoff=24, policy: Policy | None=None, *, seed=SEED, candidate_names=None, trees=80, boosting_stages=100, progress=None):
    d,health=require_valid(data,True); policy=(policy or Policy()).validate()
    if not isinstance(seed,int) or not 0 <= seed <= 2**32-1: raise ValueError('Seed must be an unsigned 32-bit integer.')
    if not 20 <= trees <= 300 or not 20 <= boosting_stages <= 300: raise ValueError('Tree/stage counts must be between 20 and 300.')
    split=lot_split(d,seed); units={}; comparisons=[]; test_records=[]; importances=[]
    candidates={'Linear':LinearRegression(), 'Ridge-1':Ridge(alpha=1.),'Ridge-10':Ridge(alpha=10.),
        'RandomForest':RandomForestRegressor(n_estimators=trees,min_samples_leaf=3,n_jobs=1,random_state=seed),
        'GradientBoosting-2':GradientBoostingRegressor(n_estimators=boosting_stages,max_depth=2,loss='huber',random_state=seed),
        'GradientBoosting-3':GradientBoostingRegressor(n_estimators=boosting_stages,max_depth=3,loss='huber',random_state=seed)}
    if candidate_names is not None:
        if not candidate_names or set(candidate_names)-set(candidates): raise ValueError('Select supported candidate models.')
        candidates={k:v for k,v in candidates.items() if k in set(candidate_names)|{'Linear'}}
    completed=0; total=d.parameter.nunique()*len(candidates)
    for par, all_rows in d.groupby('parameter',sort=True):
        valid=all_rows.value_0h.notna()&all_rows.value_24h.notna()&all_rows.value_168h.notna()
        if cutoff==96: valid &= all_rows.get('value_96h',pd.Series(np.nan,index=all_rows.index)).notna()
        rows=all_rows.loc[valid]
        parts={k:rows[rows.lot_id.isin(v)] for k,v in split.items()}
        if len(parts['train'])<30 or min(len(parts[k]) for k in ['validation','test'])<5:
            raise ValueError(f'{par}: too few complete records per independent split (train>=30, validation/test>=5).')
        X=features(parts['train'],cutoff); y=parts['train'].value_168h
        xv=features(parts['validation'],cutoff); yv=parts['validation'].value_168h
        fitted={}; ranking=[]
        for name,model in candidates.items():
            pipe=Pipeline([('prepare',processor(X)),('model',clone(model))])
            pipe.fit(X,y); m=metrics(yv,pipe.predict(xv)); ranking.append((m['MAE'],name))
            fitted[name]=pipe; comparisons.append(dict(parameter=par,model=name,split='validation',**m))
            completed+=1
            if progress: progress(.9*completed/total,f'{par}: {name} fitted and validated')
        winner=sorted(ranking)[0][1]; selected=fitted[winner]
        cal=parts['calibration']; radius=None
        if len(cal)>=20:
            residual=np.abs(cal.value_168h.to_numpy()-selected.predict(features(cal,cutoff)))
            q=min(1,np.ceil((len(cal)+1)*.9)/len(cal)); radius=float(np.quantile(residual,q,method='higher'))
        xt=features(parts['test'],cutoff); yt=parts['test'].value_168h
        pred=selected.predict(xt)
        for name in dict.fromkeys(['Linear',winner]):
            comparisons.append(dict(parameter=par,model=name,split='test',**metrics(yt,fitted[name].predict(xt))))
        # Same preprocessing fit only on training data; Isolation Forest does not use defect labels.
        prep=processor(X); z=prep.fit_transform(X)
        forest=IsolationForest(n_estimators=100,contamination='auto',random_state=seed,n_jobs=1).fit(z)
        reference=np.sort(-forest.score_samples(z))
        importance=permutation_importance(selected,xv,yv,scoring='neg_mean_absolute_error',n_repeats=3,random_state=seed)
        importances += [dict(parameter=par,feature=f,importance=float(v)) for f,v in zip(X.columns,importance.importances_mean)]
        numeric=[c for c in X if c not in CATEGORIES]
        bounds={c:[float(X[c].min()),float(X[c].max())] for c in numeric}
        units[par]=dict(model=selected,winner=winner,prep=prep,forest=forest,reference=reference,
                        unit=str(rows.unit.iloc[0]),radius=radius,bounds=bounds,
                        families=sorted(rows.part_family.unique().tolist()),test_metrics=metrics(yt,pred),
                        excluded_training_records=int((~valid).sum()))
        records=parts['test'][['component_id','lot_id','parameter','unit']].copy()
        records['actual']=yt; records['predicted']=pred; records['residual']=yt-pred
        records['lower']=pred-radius if radius is not None else np.nan
        records['upper']=pred+radius if radius is not None else np.nan
        test_records.append(records)
    stamp=datetime.now(timezone.utc).isoformat()
    manifest=dict(version='ESS-'+stamp[:19].replace(':','')+'-'+dataset_hash(d)[:8],timestamp=stamp,
        dataset_hash=dataset_hash(d),cutoff=cutoff,features=list(features(d,cutoff).columns),
        split=split,policy=policy.__dict__,seed=seed,synthetic=bool(d.get('synthetic',pd.Series(False)).all()),
        winners={p:m['winner'] for p,m in units.items()},
        hyperparameters={p:m['model'].named_steps['model'].get_params() for p,m in units.items()},
        test_metrics={p:m['test_metrics'] for p,m in units.items()})
    if progress: progress(1.0,'Calibration and held-out test evaluation complete')
    return dict(manifest=manifest,units=units,comparison=pd.DataFrame(comparisons),
                test_predictions=pd.concat(test_records,ignore_index=True),importance=pd.DataFrame(importances),health=health)

def predict(bundle, d):
    out=pd.DataFrame(index=d.index,columns=['predicted_168h','interval_lower','interval_upper','if_score','if_percentile'],dtype=float)
    out['prediction_note']=''; out['out_of_domain']=False
    cutoff=bundle['manifest']['cutoff']
    for par,rows in d.groupby('parameter'):
        if par not in bundle['units']:
            out.loc[rows.index,'prediction_note']='Unsupported parameter; prediction unavailable.'; continue
        m=bundle['units'][par]; X=features(rows,cutoff)
        required=['value_0h','value_24h']+(['value_96h'] if cutoff==96 else [])
        usable=X[required].notna().all(axis=1)&(rows.unit==m['unit'])
        out.loc[rows.index[~usable],'prediction_note']='Missing required early measurements or incompatible unit; prediction unavailable.'
        good=rows.index[usable]
        if not len(good): continue
        x=X.loc[good]; pred=m['model'].predict(x); out.loc[good,'predicted_168h']=pred
        score=-m['forest'].score_samples(m['prep'].transform(x))
        out.loc[good,'if_score']=score
        out.loc[good,'if_percentile']=100*np.searchsorted(m['reference'],score,side='right')/len(m['reference'])
        ood=pd.Series(False,index=good)
        for c,(lo,hi) in m['bounds'].items():
            spread=max(hi-lo,1e-9); ood|=(x[c]<lo-.2*spread)|(x[c]>hi+.2*spread)
        ood|=~rows.loc[good,'part_family'].isin(m['families'])
        out.loc[good,'out_of_domain']=ood
        out.loc[good[ood],'prediction_note']='Outside training support; extrapolation requires review, interval withheld.'
        if m['radius'] is not None:
            reliable=good[~ood]
            out.loc[reliable,'interval_lower']=out.loc[reliable,'predicted_168h']-m['radius']
            out.loc[reliable,'interval_upper']=out.loc[reliable,'predicted_168h']+m['radius']
    return out

def save_bundle(bundle, directory):
    p=Path(directory); p.mkdir(parents=True,exist_ok=True)
    joblib.dump(bundle,p/'model.joblib')
    (p/'manifest.json').write_text(json.dumps(bundle['manifest'],indent=2))
    bundle['comparison'].to_csv(p/'comparison.csv',index=False)
    bundle['test_predictions'].to_csv(p/'test_predictions.csv',index=False)

def load_bundle(directory):
    # Trusted local artifacts only: never expose joblib upload in the GUI.
    try: return joblib.load(Path(directory)/'model.joblib')
    except Exception as e: raise ValueError('Saved model unavailable or incompatible; train a new model.') from e
