"""Reproducible demo and measured performance runs."""
import argparse,json,time,platform
from pathlib import Path
from io import BytesIO
import psutil
import pandas as pd
from ess.data.synthetic import generate,scenario,SCENARIOS
from ess.data.validation import require_valid
from ess.features.engineering import features
from ess.prediction.training import train,save_bundle,load_bundle
from ess.prediction.evaluation import compare_screening
from ess.risk.engine import screen
from ess.config import Policy
from ess.reports.export import csv_bytes,pdf_report

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['demo','benchmark']); args=parser.parse_args()
    Path('evidence').mkdir(exist_ok=True); Path('data').mkdir(exist_ok=True)
    if args.command=='demo':
        d=generate(2000,20); d.to_csv('data/example_synthetic.csv',index=False)
        b=train(d); save_bundle(b,'models/demo'); Policy().save('config/default_policy.json')
        test=d[d.lot_id.isin(b['manifest']['split']['test'])]
        r=screen(test,b); compare_screening(r).to_csv('evidence/screening_metrics.csv',index=False)
        Path('evidence/sample_batch_report.pdf').write_bytes(pdf_report(r))
        Path('evidence/sample_component_report.pdf').write_bytes(pdf_report(r[r.component_id==r.sort_values('risk_score',ascending=False).iloc[0].component_id]))
        Path('evidence/test_screening.csv').write_bytes(csv_bytes(r))
        outcomes=[]
        for name in SCENARIOS:
            row=screen(scenario(name),b).iloc[0]
            outcomes.append(dict(scenario=name,static_violation=bool(row.static_violation),dynamic_flag=bool(row.dynamic_flag),status=row.status,predicted_168h=row.predicted_168h,reason=row.explanation))
        Path('evidence/demo_outcomes.json').write_text(json.dumps(outcomes,indent=2))
        print(b['comparison'].to_string(index=False)); print(compare_screening(r).to_string(index=False)); print(json.dumps(outcomes,indent=2))
    else:
        b=load_bundle('models/demo'); measurements=[]
        for n in [1000,10000,100000]:
            start=time.perf_counter(); d=generate(n,20,parameters=['Leakage current']); gen=time.perf_counter()-start
            payload=d.to_csv(index=False).encode(); start=time.perf_counter()
            d=pd.read_csv(BytesIO(payload)); loading=time.perf_counter()-start
            start=time.perf_counter(); clean,_=require_valid(d); features(clean); preprocessing=time.perf_counter()-start
            start=time.perf_counter(); result=screen(clean,b); inference=time.perf_counter()-start
            measurements.append(dict(components=n,records=len(d),generation_seconds=gen,loading_seconds=loading,preprocessing_seconds=preprocessing,screening_seconds=inference,rss_mb=None,dataframe_memory_mb=float((d.memory_usage(deep=True).sum()+result.memory_usage(deep=True).sum())/1024**2),review_count=int(result.dynamic_flag.sum())))
            print(measurements[-1],flush=True)
        Path('evidence/benchmark.json').write_text(json.dumps(dict(platform=platform.platform(),python=platform.python_version(),measurements=measurements),indent=2))
if __name__=='__main__': main()
