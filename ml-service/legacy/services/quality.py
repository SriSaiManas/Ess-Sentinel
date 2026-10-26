"""Row-level diagnostics augment the preserved schema validation engine."""
import re
import numpy as np
import pandas as pd
from ess.data.validation import validate, IDENTITY, REQUIRED

COLUMNS=['severity','row','component_id','field','issue','remediation']

def inspect(data: pd.DataFrame, training=False):
    data=data.reset_index(drop=True)
    clean,report=validate(data,training); issues=[]; total=0
    def add(severity,field,issue,fix,mask=None):
        nonlocal total
        indices=[None] if mask is None else list(data.index[mask])
        total+=len(indices)
        for idx in indices[:max(0,5000-len(issues))]:
            issues.append(dict(severity=severity,row=None if idx is None else int(data.index.get_loc(idx))+2,
                component_id='' if idx is None or 'component_id' not in data else str(data.loc[idx,'component_id']),field=field,issue=issue,remediation=fix))
    for c in REQUIRED:
        if c not in data: add('ERROR',c,'Required column missing','Map the source column or provide the missing field.')
    for c in data:
        if c in IDENTITY+['unit']:
            add('ERROR',c,'Missing identifier/condition','Provide the identifier or condition.',data[c].isna()|data[c].astype(str).str.strip().eq(''))
        if c.startswith('value_') or c in ['temperature','voltage','spec_min','spec_max']:
            x=pd.to_numeric(data[c],errors='coerce')
            add('ERROR',c,'Invalid numeric value','Correct the source measurement; no imputation is applied.',data[c].notna()&(x.isna()|np.isinf(x)))
            add('WARNING' if c.startswith('value_') else 'ERROR',c,'Missing value','Acquire the missing measurement or route to review.',data[c].isna())
            if c.startswith('value_') and 'spec_min' in data:
                add('ERROR',c,'Negative nonnegative measurement','Verify sign and units.',(x<0)&(pd.to_numeric(data.spec_min,errors='coerce')>=0))
    if all(c in clean for c in IDENTITY):
        add('ERROR','identity','Duplicate measurement identity','Resolve duplicate acquisition records.',clean.duplicated(IDENTITY,keep=False))
    if all(c in clean for c in ['parameter','unit']):
        bad=clean.groupby('parameter').unit.transform('nunique')>1
        add('ERROR','unit','Inconsistent parameter units','Convert to a common unit before importing.',bad)
    tcols=sorted((int(m[1]),c) for c in data if (m:=re.fullmatch(r'timestamp_(\d+)h',c)))
    times={}
    for t,c in tcols:
        times[t]=pd.to_datetime(data[c],errors='coerce',utc=True)
        bad=times[t].isna()
        add('ERROR',c,'Invalid timestamp','Use an ISO 8601 timestamp including timezone.',bad)
        if bad.any(): report['errors'].append(f'{c}: {int(bad.sum())} invalid timestamps.')
    for (a,ca),(b,cb) in zip(tcols,tcols[1:]):
        bad=times[b]<=times[a]
        add('ERROR',cb,'Timestamp order violation',f'{cb} must be later than {ca}.',bad)
        if bad.any(): report['errors'].append(f'{cb}: timestamp order violation.')
        drift=((times[b]-times[a]).dt.total_seconds()/3600-(b-a)).abs()>.5
        add('WARNING',cb,'Nominal stage differs by >0.5h','Verify stage assignment; the model uses nominal hours.',drift&~bad)
    for msg in report['errors']: add('ERROR','dataset',msg,'Correct the dataset and validate again.')
    for msg in report['warnings']:
        informational=msg.startswith('Target/label columns excluded')
        add('INFO' if informational else 'WARNING','dataset',msg,'Review the evidence before proceeding.')
    values=[c for c in data if re.fullmatch(r'value_\d+h',c)]
    completeness=100*(1-data[values].isna().mean().mean()) if values and len(data) else 0
    report.update(issue_count=total,details_truncated=total>5000,completeness=float(completeness),timestamp_columns=len(tcols))
    if report['errors']: report['score']=min(report['score'],max(0,100-20*len(report['errors'])))
    return clean,report,pd.DataFrame(issues,columns=COLUMNS)

def timestamped(d):
    """Explicit synthetic acquisition times; no timing data is fabricated for imports."""
    result=d.copy()
    for c in list(result):
        if m:=re.fullmatch(r'value_(\d+)h',c):
            result[f'timestamp_{m[1]}h']=(pd.Timestamp('2026-01-01T00:00:00Z')+pd.Timedelta(hours=int(m[1]))).isoformat()
    return result
