"""Internal one-request process interface. Never accepts executable code or paths."""
import sys, os, json, base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'legacy'))

import pandas as pd
from bson import ObjectId
from mongo_store import MongoStore
from services.workspace import Workspace
from services.quality import inspect
from services.store import atomic, now
from services.reports import report_pdf, excel_bytes
from ess.reports.export import csv_bytes
from ess.data.validation import ingest
from ess.config import Policy
from ess.prediction.training import predict
from ess.prediction.evaluation import compare_screening
from ess.risk.engine import screen, component_summary

def records(d):
    return json.loads(d.to_json(orient='records', date_format='iso'))

def main(p):
    w = Workspace.__new__(Workspace)
    w.store = MongoStore(os.environ['ARTIFACT_DIR'])
    s = w.store
    op = p['operation']
    a = p.get('args', {})

    if op == 'seed':
        w.bootstrap()
        s.ensure_indexes()
        return {'batchId': s.get('active_batch')}

    if op == 'context':
        bid = a.get('batchId') or s.get('active_batch')
        r = s.latest_run(bid) if bid else None
        if r and not s.artifact_store.exists('runs', r['id'], 'results.csv'):
            r = None
        return dict(
            batchId=bid,
            run=r,
            policy=s.policy().__dict__,
            modelId=s.get('active_model'),
            workspace=s.get('workspace_name', 'Engineering workspace')
        )

    if op == 'overview':
        # Fast overview aggregation
        bid = a.get('batchId') or s.get('active_batch')
        r = s.latest_run(bid) if bid else None
        summaries = []
        counts = {'NORMAL': 0, 'WATCH': 0, 'HIGH RISK': 0, 'CRITICAL': 0}
        priority = []
        if r:
            try:
                res = s.results(r['id'])
                # Vectorized highest status per component
                levels = {'NORMAL': 0, 'WATCH': 1, 'HIGH RISK': 2, 'CRITICAL': 3}
                res['status_level'] = res['status'].map(lambda x: levels.get(x, 0))
                # Sort and drop duplicate component_ids, keeping highest status and risk_score
                res_sorted = res.sort_values(['status_level', 'risk_score'], ascending=[False, False])
                comp_max = res_sorted.drop_duplicates(subset=['component_id'])
                for st in counts.keys():
                    counts[st] = int((comp_max['status'] == st).sum())
                top_priority = comp_max.head(20)[['component_id', 'lot_id', 'status', 'risk_score', 'explanation']]
                priority = records(top_priority)
            except Exception:
                pass
        return {
            'batchId': bid,
            'run': r,
            'counts': counts,
            'priority': priority
        }

    if op == 'import':
        d = ingest(base64.b64decode(a['content']), a['filename'], a.get('mapping'))
        for par, unit in a.get('units', {}).items():
            if unit:
                d.loc[d.parameter == par, 'unit'] = unit
        clean, health, issues = inspect(d)
        if len(d) > 300000:
            raise ValueError('Maximum 300000 rows')
        if not a.get('commit'):
            return dict(preview=records(clean.head(50)), health=health, issues=records(issues), columns=list(d.columns))
        return {'batchId': w.commit(clean, a['name'], 'IMPORTED', base64.b64decode(a['content']))}

    if op == 'quality':
        clean, health, issues = inspect(s.data(a['batchId']))
        return dict(health=health, issues=records(issues))

    if op == 'measurements':
        return records(s.data(a['batchId']))

    if op == 'results':
        return records(s.results(a['runId']))

    if op == 'screen':
        return {'runId': w.screen(a['batchId'], a.get('stage', 24), mid='' if a.get('statisticsOnly') else None)}

    if op == 'train':
        return {'modelId': w.train(a['batchId'], **a.get('options', {}))}

    if op == 'activate':
        s.activate(a['modelId'], True)
        return {'message': 'Model activated'}

    if op == 'model':
        b = s.model(a['modelId'])
        return dict(
            manifest=b['manifest'],
            comparison=records(b['comparison']),
            test_predictions=records(b['test_predictions']),
            importance=records(b['importance'])
        )

    if op == 'predict':
        d = s.data(a['batchId'])
        return records(d[['component_id', 'lot_id', 'parameter', 'unit']].join(predict(s.model(a['modelId']), d)))

    if op == 'simulate':
        baseline, bid = w.simulate(**a)
        oid = s.db.scenarios.insert_one(dict(
            created=now(),
            settings=a,
            baseline_batch=ObjectId(baseline),
            batch_id=ObjectId(bid)
        )).inserted_id
        return dict(
            id=str(oid),
            baseline=baseline,
            batchId=bid,
            comparison=[{'population': label, **s.latest_run(key)['summary']} for label, key in [('Baseline', baseline), ('Simulation', bid)]]
        )

    if op == 'policy':
        policy = Policy(**a['config']).validate()
        if a.get('save'):
            return {'policyId': s.save_policy(policy, True)}
        if not a.get('batchId'):
            return {'valid': True}
        d = s.data(a['batchId'])
        model = s.model(s.get('active_model'))
        stage = model['manifest']['cutoff'] if model else 24
        before = screen(d, model, s.policy(), stage)
        after = screen(d, model, policy, stage)
        return records(pd.DataFrame(dict(
            component_id=before.component_id,
            parameter=before.parameter,
            before=before.status,
            after=after.status,
            score_before=before.risk_score,
            score_after=after.risk_score
        )))

    if op == 'review':
        s.review(a['runId'], a['componentId'], a['state'], a['note'])
        return {'message': 'Review saved'}

    if op == 'evaluate':
        return records(compare_screening(s.results(a['runId'])))

    if op == 'diagnostics':
        return w.diagnostics()

    if op == 'smoke':
        return w.smoke()

    if op == 'reset':
        return {'batchId': w.reset_demo(True)}

    if op == 'settings':
        s.set('workspace_name', a['name'])
        s.event('settings_changed', {'workspace_name': a['name']})
        return {'message': 'Settings saved'}

    if op == 'report':
        kind = a['kind']
        tables = {}
        r = None
        if kind in ['batch', 'component']:
            r = s.results(a['runId'])
            if kind == 'component':
                r = r[r.component_id == a['componentId']]
            if r.empty:
                raise ValueError('No matching results')
            tables = {'Summary': component_summary(r), 'Evidence': r}
        elif kind == 'quality':
            _, h, issues = inspect(s.data(a['batchId']))
            tables = {'Quality': pd.DataFrame([{'field': k, 'value': str(v)} for k, v in h.items()]), 'Issues': issues}
        elif kind == 'evaluation':
            b = s.model(a['modelId'])
            tables = {'Comparison': b['comparison'], 'Test predictions': b['test_predictions']}
        elif kind == 'audit':
            tables = {'Audit': s.table('events')}
        elif kind == 'scenario':
            scenarios = list(s.db.scenarios.find())
            summary = []
            tables = {'Scenarios': pd.DataFrame([{'id': str(x['_id']), 'configuration': json.dumps(x['settings']), 'baseline': str(x['baseline_batch']), 'simulation': str(x['batch_id'])} for x in scenarios])}
            for x in scenarios:
                for label, key in [('Baseline', 'baseline_batch'), ('Simulation', 'batch_id')]:
                    run = s.latest_run(str(x[key]))
                    if run:
                        summary.append({'scenario': str(x['_id']), 'population': label, **run['summary']})
            tables['Disposition comparison'] = pd.DataFrame(summary)
        else:
            raise ValueError('Invalid report kind')

        oid = ObjectId()
        rid = str(oid)
        for ext, content in [
            ('pdf', report_pdf('ESS Sentinel Web 3.0 — ' + kind, {'run': a.get('runId', ''), 'source': 'See batch source; demo data is synthetic'}, tables, r)),
            ('xlsx', excel_bytes(tables)),
            ('csv', csv_bytes(next(iter(tables.values()))))
        ]:
            # Save to GridFS (and local cache)
            s.artifact_store.save('reports', rid, 'report.' + ext, content, extra_metadata={'report_id': rid, 'kind': kind})

        s.db.reports.insert_one(dict(_id=oid, kind=kind, created=now(), context=a))
        s.event('report_generated', {'report_id': rid, 'kind': kind})
        return {'reportId': rid}

    if op == 'backup':
        rid = str(ObjectId())
        backup_content = s.backup()
        s.artifact_store.save('reports', rid, 'backup.zip', backup_content, content_type='application/zip', extra_metadata={'report_id': rid, 'kind': 'backup'})
        s.db.reports.insert_one(dict(_id=ObjectId(rid), kind='backup', created=now()))
        s.event('backup_generated', {'report_id': rid})
        return {'reportId': rid}

    raise ValueError('Unknown operation')

if __name__ == '__main__':
    try:
        result = main(json.load(sys.stdin))
        print(json.dumps({'ok': True, 'data': result}, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x), allow_nan=False))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e), 'type': type(e).__name__}))
        sys.exit(1)
