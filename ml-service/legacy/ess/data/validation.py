"""Fail-closed schema validation with explicit warnings and no silent row deletion."""
from io import BytesIO
import re
import zipfile
import numpy as np
import pandas as pd

IDENTITY=['component_id','lot_id','parameter','part_family','session_id','temperature','voltage']
REQUIRED=['component_id','lot_id','parameter','unit','value_0h','value_24h','spec_min','spec_max']
DEFAULTS={'part_family':'unspecified','session_id':'session-1','temperature':25.,'voltage':3.3}

def ingest(content: bytes, filename: str, mapping: dict | None=None) -> pd.DataFrame:
    identifier_types={c:'string' for c in ['component_id','lot_id','parameter','unit','part_family','session_id']}
    if mapping: identifier_types.update({source:'string' for source,target in mapping.items() if target in identifier_types})
    if len(content)>25*1024*1024: raise ValueError('File exceeds 25 MB limit.')
    if not content: raise ValueError('File is empty.')
    try:
        if filename.lower().endswith('.csv'): d=pd.read_csv(BytesIO(content),on_bad_lines='error',dtype=identifier_types,float_precision='round_trip')
        elif filename.lower().endswith('.xlsx'):
            with zipfile.ZipFile(BytesIO(content)) as archive:
                if sum(x.file_size for x in archive.infolist())>128*1024*1024:
                    raise ValueError('Expanded spreadsheet exceeds 128 MB limit.')
            d=pd.read_excel(BytesIO(content),engine='openpyxl',dtype=identifier_types)
        else: raise ValueError('Only CSV and XLSX files are supported.')
    except Exception as e:
        raise ValueError('Unable to parse dataset. Check the file format and column structure.') from e
    if mapping:
        targets=list(mapping.values())
        if len(targets)!=len(set(targets)): raise ValueError('Column mapping contains duplicate destinations.')
        d=d.rename(columns=mapping)
    if d.columns.duplicated().any(): raise ValueError('Duplicate column names after mapping.')
    return d

def validate(data: pd.DataFrame, training: bool=False):
    d=data.copy(); errors=[]; warnings=[]
    missing=[c for c in REQUIRED if c not in d]
    if missing: errors.append('Missing required columns: '+', '.join(missing))
    if d.empty: errors.append('Dataset is empty.')
    if errors: return d,dict(score=0,errors=errors,warnings=warnings,rows=len(d))
    for c,v in DEFAULTS.items():
        if c not in d: d[c]=v; warnings.append(f'{c} missing; explicit default {v} applied.')
    times=[]
    for c in d:
        if c.startswith('value_'):
            m=re.fullmatch(r'value_(\d+)h',c)
            if not m: errors.append(f'Invalid measurement time column: {c}')
            else: times.append((int(m[1]),c))
    for c in IDENTITY+['unit']:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq('').any(): errors.append(f'{c} contains missing identifiers/conditions.')
    numeric=['spec_min','spec_max','temperature','voltage']+[c for _,c in times]
    for c in numeric:
        original=d[c]; d[c]=pd.to_numeric(original,errors='coerce')
        bad=original.notna()&d[c].isna()
        if bad.any(): errors.append(f'{c} contains {bad.sum()} invalid numerical values.')
        if np.isinf(d[c]).any(): errors.append(f'{c} contains infinite values.')
        missing_n=int(d[c].isna().sum())
        if missing_n:
            (errors if c in ['spec_min','spec_max','temperature','voltage'] else warnings).append(f'{c} contains {missing_n} missing values.')
        if c.startswith('value_') and ((d[c]<0)&(d.spec_min>=0)).any():
            errors.append(f'{c} has negative measurements for a nonnegative specification.')
    if (d.spec_max<=d.spec_min).any(): errors.append('spec_max must exceed spec_min.')
    duplicates=int(d.duplicated(IDENTITY).sum())
    if duplicates: errors.append(f'{duplicates} duplicate component/parameter/session/condition records.')
    if d.groupby('parameter').unit.nunique().gt(1).any(): errors.append('Inconsistent units within a parameter; convert units before import.')
    if len(d)<30: warnings.append('Insufficient sample size for reliable population/model assessment (<30 records).')
    values=[c for _,c in times]
    for c in values:
        group=d.groupby(['parameter','unit'])[c]
        med=group.transform('median'); scale=group.transform(lambda x:(x-x.median()).abs().median())
        out=((d[c]-med).abs()>10*scale.clip(lower=1e-9)).sum()
        if out: warnings.append(f'{c}: {out} extreme robust outliers retained for screening.')
    if 'defect_label' in d:
        if not d.defect_label.isin([0,1]).all(): errors.append('defect_label must contain only 0 or 1.')
        else:
            rate=d.defect_label.mean()
            if rate<.05 or rate>.95: warnings.append('Severe class imbalance; inspect recall and class counts.')
    forbidden=[c for c in d if c in ['defect_label','defect_type','true_future_value','value_168h']]
    warnings.append('Target/label columns excluded from prediction inputs: '+', '.join(forbidden))
    fingerprint_cols=['parameter','unit','temperature','voltage']+values
    if len(d) and values:
        signatures=pd.util.hash_pandas_object(d[fingerprint_cols],index=False)
        cross=pd.DataFrame({'signature':signatures,'lot':d.lot_id}).groupby('signature').lot.nunique().gt(1)
        if cross.any():
            (errors if training else warnings).append(f'{int(cross.sum())} identical measurement signatures occur across lots; resolve potential train/test duplicates before training.')
    if training:
        if 'value_168h' not in d: errors.append('Training requires value_168h targets.')
        if d.lot_id.nunique()<8: errors.append('Training requires at least 8 independent lots for train/validation/calibration/test separation.')
        if d.groupby('component_id').lot_id.nunique().gt(1).any(): errors.append('A component occurs in multiple lots; cannot guarantee split isolation.')
    score=max(0,100-20*len(errors)-min(30,3*len(warnings)))
    return d,dict(score=score,errors=errors,warnings=warnings,rows=len(d),time_points=sorted(t for t,_ in times))

def require_valid(d: pd.DataFrame, training=False):
    clean, report=validate(d,training)
    if report['errors']: raise ValueError('; '.join(report['errors']))
    return clean,report
