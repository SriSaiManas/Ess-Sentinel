"""Rebuild demonstrable exports from actual local computations."""
from pathlib import Path
import tempfile,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from services.workspace import Workspace
from services.reports import report_pdf,excel_bytes
from services.quality import inspect,timestamped
from ess.risk.engine import component_summary
from ess.data.synthetic import generate

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    w=Workspace(temp);w.bootstrap();s=w.store;bid=s.get('active_batch');run=s.latest_run(bid);r=s.results(run['id']);data=s.data(bid);b=s.model(s.get('active_model'))
    folder=ROOT/'evidence/reports';folder.mkdir(parents=True,exist_ok=True)
    tables={}
    tables['batch']={'Dispositions':component_summary(r).status.value_counts().rename_axis('Status').reset_index(name='Components'),'Lots':r.groupby('lot_id').agg(records=('component_id','size'),flagged=('dynamic_flag','sum')).reset_index()}
    cid=r.sort_values('risk_score',ascending=False).component_id.iloc[0];component=r[r.component_id==cid]
    tables['component']={'Measurements':component[['parameter','unit','value_0h','value_24h','predicted_168h','risk_score','status']]}
    tables['quality']={'Quality findings':inspect(data)[2]}
    tables['evaluation']={'Regression comparison':b['comparison']}
    baseline,simulation=w.simulate('Latent Defect');rows=[]
    for label,id in [('Baseline',baseline),('Latent defect',simulation)]:
        sr=s.results(s.latest_run(id)['id']);summary=component_summary(sr)
        rows.append(dict(population=label,components=len(summary),review=int(summary.dynamic_flag.sum()),static_violations=int(summary.static_violation.sum()),predicted_crossings=int(sr.predicted_crossing.sum())))
    tables['scenario']={'Scenario comparison':pd.DataFrame(rows)}
    tables['audit']={'Events':s.table('events')[['id','timestamp','action','outcome']]}
    meta={'Source':'Synthetic reference dataset','Batch':bid,'Model':b['manifest']['version'],'Screening stage':'24h'}
    for kind,frames in tables.items():
        (folder/(kind+'.pdf')).write_bytes(report_pdf(kind.title()+' report',meta,frames,screening=component if kind=='component' else r if kind=='batch' else None))
        (folder/(kind+'.xlsx')).write_bytes(excel_bytes(frames))
    sample=ROOT/'data/samples';sample.mkdir(exist_ok=True)
    timestamped(generate(400,12)).to_csv(sample/'multilot_timestamped.csv',index=False)
    (ROOT/'evidence/scenario_comparison.json').write_text(json.dumps(rows,indent=2))
print('Six PDF and Excel report pairs generated from actual computations.')
