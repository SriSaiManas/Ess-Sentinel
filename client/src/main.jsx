import React, {useState, useEffect, useMemo} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter, NavLink, useLocation} from 'react-router-dom';
import {ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, ScatterChart, Scatter, PieChart, Pie, Cell} from 'recharts';
import {Activity, Menu, ShieldCheck, RefreshCw, Database} from 'lucide-react';
import {api, action, setToken, download} from './api';
import './style.css';

const groups = {
    COMMAND: ['Overview', 'Live Operations', 'Batch Explorer'],
    ENGINEERING: ['Data Ingestion', 'Data Quality', 'Screening', 'Anomaly Analysis', 'Component Explorer'],
    INTELLIGENCE: ['Predictive Analytics', 'Model Laboratory', 'Scenario Simulator', 'Model Evaluation'],
    GOVERNANCE: ['Policy Center', 'Audit Trail', 'Reports & Exports'],
    SYSTEM: ['Settings', 'System Diagnostics']
};

const slug = s => s.toLowerCase().replaceAll(' & ', '-').replaceAll(' ', '-');
const pages = Object.values(groups).flat();

const fmt = v => v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : typeof v === 'number' ? Number.isInteger(v) ? v.toLocaleString() : v.toPrecision(5) : String(v);

function Table({rows = [], columns, caption = 'Records'}) {
    const [search, S] = useState('');
    const [page, P] = useState(1);
    const cols = columns || Object.keys(rows[0] || {});
    const filtered = rows.filter(r => JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));
    useEffect(() => P(1), [search, rows]);

    return (
        <section className="panel">
            <div className="row">
                <h2>{caption}</h2>
                <label>Filter records
                    <input value={search} onChange={e => S(e.target.value)} placeholder="Search displayed data"/>
                </label>
            </div>
            {!rows.length ? (
                <p className="empty">No records yet. Import a dataset or run the relevant operation.</p>
            ) : (
                <>
                    <div className="table-scroll">
                        <table>
                            <thead>
                                <tr>{cols.map(c => <th key={c}>{c.replaceAll('_', ' ')}</th>)}</tr>
                            </thead>
                            <tbody>
                                {filtered.slice((page - 1) * 25, page * 25).map((r, i) => (
                                    <tr key={i}>
                                        {cols.map(c => (
                                            <td key={c}>
                                                <span className={c === 'status' ? 'badge ' + slug(r[c] || '') : ''}>{fmt(r[c])}</span>
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="row">
                        <span>{filtered.length} matching records · page {page}</span>
                        <button disabled={page === 1} onClick={() => P(page - 1)}>Previous</button>
                        <button disabled={page * 25 >= filtered.length} onClick={() => P(page + 1)}>Next</button>
                    </div>
                </>
            )}
        </section>
    );
}

function Chart({data, x, y, title, type = 'bar'}) {
    return (
        <section className="panel">
            <h2>{title}</h2>
            {!data || !data.length ? (
                <p>No computed data available.</p>
            ) : (
                <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                        {type === 'pie' ? (
                            <PieChart>
                                <Pie data={data} dataKey={y} nameKey={x} innerRadius='58%' outerRadius='85%' paddingAngle={2}>
                                    {data.map((r, i) => (
                                        <Cell key={i} fill={['#37c991', '#f5b84b', '#ee9754', '#f16c76'][i % 4]}/>
                                    ))}
                                </Pie>
                                <Tooltip/>
                            </PieChart>
                        ) : type === 'line' ? (
                            <LineChart data={data}>
                                <CartesianGrid stroke="#23324a"/>
                                <XAxis dataKey={x}/>
                                <YAxis domain={['auto', 'auto']}/>
                                <Tooltip/>
                                <Line dataKey={y} stroke="#36d6c5" dot/>
                                <Line dataKey="prediction" stroke="#f5b84b" dot/>
                            </LineChart>
                        ) : type === 'scatter' ? (
                            <ScatterChart>
                                <CartesianGrid stroke="#23324a"/>
                                <XAxis dataKey={x} type="number" name={x}/>
                                <YAxis dataKey={y} type="number" name={y}/>
                                <Tooltip cursor={{strokeDasharray: '3 3'}}/>
                                <Scatter data={data} fill="#36d6c5"/>
                            </ScatterChart>
                        ) : (
                            <BarChart data={data}>
                                <CartesianGrid stroke="#23324a"/>
                                <XAxis dataKey={x}/>
                                <YAxis/>
                                <Tooltip/>
                                <Bar dataKey={y} fill="#36d6c5" radius={[3, 3, 0, 0]}/>
                            </BarChart>
                        )}
                    </ResponsiveContainer>
                </div>
            )}
        </section>
    );
}

function Field({label, value, onChange, type = 'text', ...rest}) {
    return (
        <label>{label}
            <input type={type} value={value} onChange={e => onChange(type === 'number' ? Number(e.target.value) : e.target.value)} {...rest}/>
        </label>
    );
}

function App() {
    const [open, O] = useState(false);
    const [busy, B] = useState(false);
    const [notice, N] = useState(null);
    const [ctx, C] = useState({});
    const [batches, BS] = useState([]);
    const [models, MS] = useState([]);
    const [rows, R] = useState([]);
    const [data, D] = useState([]);
    const [aux, A] = useState(null);
    const [version, V] = useState(0);
    const [batch, SB] = useState('');
    const [component, SC] = useState('');
    const [initialized, setInitialized] = useState(false);

    const location = useLocation();
    const page = pages.find(p => '/' + slug(p) === location.pathname) || 'Overview';

    async function task(fn, message = 'Operation completed') {
        B(true);
        N(null);
        try {
            const r = await fn();
            if (message) N({type: 'success', text: message});
            return r;
        } catch (e) {
            N({type: 'error', text: e.message});
            return null;
        } finally {
            B(false);
        }
    }

    // Fast initial progressive load: context + batches + models
    async function refresh(bid = batch) {
        try {
            const [c, b, m] = await Promise.all([
                api('/context' + (bid ? '?batchId=' + bid : '')),
                api('/batches?limit=100'),
                api('/models?limit=100')
            ]);
            C(c);
            BS(b.items || []);
            MS(m.items || []);
            const activeBid = c.batchId || (b.items && b.items[0] ? b.items[0]._id : '');
            SB(activeBid);

            // Progressive: only load results if a screening run exists
            if (c.run) {
                action('results', {runId: c.run.id}).then(r => R(r || [])).catch(() => R([]));
            } else {
                R([]);
            }

            setInitialized(true);
        } catch (e) {
            N({type: 'error', text: e.message});
            setInitialized(true);
        }
    }

    useEffect(() => {
        task(() => refresh(), null);
    }, [version]);

    // Progressive asynchronous loading for specific pages only when visited
    useEffect(() => {
        A(null);
        O(false);
        const resources = {
            'Live Operations': 'screening-runs',
            'Batch Explorer': 'batches',
            'Audit Trail': 'audit-events',
            'Reports & Exports': 'reports'
        };

        if (resources[page]) {
            task(async () => A(await api('/' + resources[page] + '?limit=100')), null);
        }
        if (page === 'Data Quality' && batch) {
            task(async () => A(await action('quality', {batchId: batch})), null);
        }
        if (page === 'System Diagnostics') {
            task(async () => A(await action('diagnostics')), null);
        }
        if ((page === 'Model Evaluation' || page === 'Model Laboratory') && ctx.modelId) {
            task(async () => A(await action('model', {modelId: ctx.modelId})), null);
        }
        if ((page === 'Batch Explorer' || page === 'Live Operations') && batch && !data.length) {
            action('measurements', {batchId: batch}).then(d => D(d || [])).catch(() => D([]));
        }
    }, [page, batch, version, ctx.modelId]);

    async function run(op, args = {}, message) {
        return task(async () => {
            const r = await action(op, args);
            if (r?.batchId) SB(r.batchId);
            V(v => v + 1);
            return r;
        }, message);
    }

    const selected = batches.find(b => b._id === batch);
    const componentRows = rows.filter(r => r.component_id === component);
    const chosen = componentRows[0];

    // Memoize summaries for instant rendering
    const {summaries, counts} = useMemo(() => {
        if (!rows.length) return {summaries: [], counts: ['NORMAL', 'WATCH', 'HIGH RISK', 'CRITICAL'].map(s => ({status: s, count: 0}))};
        const map = rows.reduce((a, r) => {
            const levels = ['NORMAL', 'WATCH', 'HIGH RISK', 'CRITICAL'];
            const old = a[r.component_id];
            if (!old || levels.indexOf(r.status) > levels.indexOf(old.status) || (r.status === old.status && r.risk_score > old.risk_score)) {
                a[r.component_id] = r;
            }
            return a;
        }, {});
        const sum = Object.values(map);
        const cnt = ['NORMAL', 'WATCH', 'HIGH RISK', 'CRITICAL'].map(status => ({
            status,
            count: sum.filter(r => r.status === status).length
        }));
        return {summaries: sum, counts: cnt};
    }, [rows]);

    return (
        <div className="shell">
            <aside className={open ? 'open' : ''}>
                <div className="brand">
                    <img src="/logo.svg" alt="ESS Sentinel — Engineering Intelligence"/>
                </div>
                <nav aria-label="Main navigation">
                    {Object.entries(groups).map(([g, ps]) => (
                        <section key={g}>
                            <p className="eyebrow">{g}</p>
                            {ps.map(p => (
                                <NavLink key={p} to={'/' + slug(p)}>
                                    <Activity size={14}/>
                                    {p}
                                </NavLink>
                            ))}
                        </section>
                    ))}
                </nav>
                <div className="sidebar-foot">
                    <div style={{display: 'flex', alignItems: 'center', gap: '6px', color: '#36d6c5', marginBottom: '4px'}}>
                        <Database size={12}/> Academic Demo Mode
                    </div>
                    GridFS Persistent Artifacts<br/>React → Express → Atlas
                </div>
            </aside>
            <main>
                <header>
                    <button className="mobile" aria-label="Toggle navigation" onClick={() => O(!open)}>
                        <Menu/>
                    </button>
                    <span className="eyebrow">{Object.keys(groups).find(k => groups[k].includes(page))} / WORKSPACE</span>
                    <button aria-label="Refresh workspace" disabled={busy} onClick={() => V(v => v + 1)}>
                        <RefreshCw size={16}/>
                    </button>
                </header>
                <h1>{page === 'Overview' ? 'Engineering Intelligence Overview' : page}</h1>
                <p className="subtitle">Quality surveillance · Predictive analytics · Traceable engineering decisions</p>

                <div className="context">
                    <label>Active batch
                        <select value={batch} disabled={busy} onChange={e => { SB(e.target.value); task(() => refresh(e.target.value), null); }}>
                            <option value="">Select a batch</option>
                            {batches.map(b => (
                                <option key={b._id} value={b._id}>
                                    {b.name}{b.archived ? ' (archived)' : ''}
                                </option>
                            ))}
                        </select>
                    </label>
                    <span className="badge">{selected?.source || 'NO DATA'}</span>
                    <span>
                        {selected
                            ? `${selected.components} components · ${selected.rows} measurements · health ${selected.health}/100`
                            : 'Create the synthetic demonstration or import measurements.'}
                    </span>
                </div>

                {notice && (
                    <div role={notice.type === 'error' ? 'alert' : 'status'} className={'notice ' + notice.type}>
                        {notice.text}
                    </div>
                )}
                {busy && <div className="loading" role="status">Processing actual data…</div>}
                {data.some(r => r.synthetic === true || r.synthetic === 'True') && (
                    <p className="notice">SYNTHETIC MEASUREMENTS — generated demonstration data, including when uploaded as a file.</p>
                )}

                <fieldset disabled={busy} className="workspace">
                    {!batches.length && initialized && (
                        <section className="panel">
                            <h2>Start an engineering workspace</h2>
                            <p>The bundled demonstration is synthetic. Imported measurements remain explicitly labeled.</p>
                            <button className="primary" onClick={() => run('seed', {}, 'Demonstration initialized')}>Initialize synthetic demo</button>
                        </section>
                    )}

                    {page === 'Overview' && (
                        <>
                            <div className="kpis">
                                {[
                                    ['Total components', selected?.components || 0],
                                    ['Screened components', summaries.length],
                                    ['Flagged components', summaries.filter(r => r.status !== 'NORMAL').length],
                                    ['Critical findings', counts[3]?.count || 0],
                                    ['Data quality', selected?.health == null ? '—' : selected.health + '/100'],
                                    ['Model readiness', ctx.modelId ? 'Available' : 'Not active']
                                ].map(([label, v]) => (
                                    <div className="kpi" key={label}>
                                        <small>{label}</small>
                                        <strong>{fmt(v)}</strong>
                                        <span>{ctx.run ? 'Computed screening evidence' : 'Awaiting screening'}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="grid">
                                <Chart title="Screening disposition" type="pie" data={counts} x="status" y="count"/>
                                <Chart
                                    title="Risk distribution"
                                    data={Array.from({length: 10}, (_, i) => ({
                                        score: `${i * 10}–${i * 10 + 9}`,
                                        count: summaries.filter(r => r.risk_score >= i * 10 && (i === 9 || r.risk_score < (i + 1) * 10)).length
                                    }))}
                                    x="score"
                                    y="count"
                                />
                            </div>
                            <Table caption="Priority findings" rows={[...summaries].sort((a, b) => b.risk_score - a.risk_score).slice(0, 20)} columns={['component_id', 'lot_id', 'status', 'risk_score', 'explanation']}/>
                        </>
                    )}

                    {page === 'Live Operations' && (
                        <>
                            <p className="notice">Stored processing activity; no industrial telemetry connection is configured.</p>
                            <Table caption="Screening history" rows={aux?.items || []}/>
                            <Table caption="Latest measurements" rows={data.slice(-100)}/>
                        </>
                    )}

                    {page === 'Batch Explorer' && <BatchPage batches={batches} selected={selected} task={task} refresh={() => V(v => v + 1)} data={data}/>}

                    {page === 'Data Ingestion' && <ImportPage task={task} onCommit={r => { SB(r.batchId); V(v => v + 1); }}/>}

                    {page === 'Data Quality' && (
                        <>
                            <section className="panel">
                                <h2>Validation summary</h2>
                                {aux?.health && Object.entries(aux.health).map(([k, v]) => (
                                    <p key={k}><b>{k}: </b>{fmt(v)}</p>
                                ))}
                            </section>
                            <Table caption="Row-level findings" rows={aux?.issues || []}/>
                        </>
                    )}

                    {page === 'Screening' && <ScreenPage batch={batch} ctx={ctx} rows={rows} run={run}/>}

                    {page === 'Anomaly Analysis' && <Anomaly rows={rows}/>}

                    {page === 'Component Explorer' && (
                        <>
                            <label>Component
                                <select value={component} onChange={e => SC(e.target.value)}>
                                    <option value="">Choose a component</option>
                                    {[...new Set(rows.map(r => r.component_id))].map(c => <option key={c}>{c}</option>)}
                                </select>
                            </label>
                            {chosen && (
                                <>
                                    <h2>{component} · <span className={'badge ' + slug(chosen.status)}>{chosen.status}</span></h2>
                                    {componentRows.map((r, i) => (
                                        <Chart
                                            key={i}
                                            title={`${r.parameter} (${r.unit}) — future actuals are retrospective`}
                                            type="line"
                                            data={[0, 24, 96, 168].map(t => ({hour: t, value: r['value_' + t + 'h'], prediction: t === 168 ? r.predicted_168h : null}))}
                                            x="hour"
                                            y="value"
                                        />
                                    ))}
                                    <Table caption="Evidence and explanations" rows={componentRows}/>
                                    <Review runId={ctx.run?.id} component={component} task={task}/>
                                    <button onClick={async () => {
                                        const r = await run('report', {kind: 'component', runId: ctx.run?.id, componentId: component});
                                        if (r) task(() => download(r.reportId, 'pdf'), 'Component PDF downloaded');
                                    }}>Download component report</button>
                                </>
                            )}
                        </>
                    )}

                    {page === 'Predictive Analytics' && <Prediction batch={batch} models={models} task={task}/>}

                    {page === 'Model Laboratory' && <Laboratory batch={batch} models={models} aux={aux} run={run} task={task} setAux={A}/>}

                    {page === 'Scenario Simulator' && <Simulator run={run}/>}

                    {page === 'Model Evaluation' && (
                        <>
                            <p className="notice">Saved regression evidence uses held-out lots. Screening metrics for an active batch are descriptive unless it is the untouched held-out population.</p>
                            <Table caption="Saved validation and test metrics" rows={aux?.comparison || []}/>
                            <Chart title="Observed versus predicted on held-out data" type="scatter" data={aux?.test_predictions || []} x="actual" y="predicted"/>
                            <button disabled={!ctx.run} onClick={() => task(async () => {
                                const r = await action('evaluate', {runId: ctx.run.id});
                                A(a => ({...a, classification: r}));
                            }, 'Policy evaluation completed')}>Evaluate current screening</button>
                            <Table caption="Screening policy metrics" rows={aux?.classification || []}/>
                        </>
                    )}

                    {page === 'Policy Center' && <PolicyEditor ctx={ctx} batch={batch} task={task} run={run}/>}

                    {page === 'Audit Trail' && (
                        <>
                            <p>Append-only operation history. Review notes are annotations and never change engineering scores.</p>
                            <Catalog route="audit-events"/>
                        </>
                    )}

                    {page === 'Reports & Exports' && <Reports ctx={ctx} batch={batch} run={run} task={task} aux={aux}/>}

                    {page === 'Settings' && <Settings ctx={ctx} run={run} task={task}/>}

                    {page === 'System Diagnostics' && (
                        <>
                            <Table caption="Runtime dependencies" rows={aux?.dependencies || []}/>
                            <section className="panel">
                                {aux && Object.entries(aux).filter(([k]) => k !== 'dependencies').map(([k, v]) => (
                                    <p key={k}>{k}: {fmt(v)}</p>
                                ))}
                            </section>
                            <button onClick={() => task(async () => {
                                const smoke = await action('smoke');
                                A(a => ({...a, smoke}));
                            }, 'Backend smoke check completed')}>Run backend smoke check</button>
                        </>
                    )}
                </fieldset>
                <footer>ESS SENTINEL WEB 3.0 · Academic Demonstration · Persistent MongoDB GridFS Storage</footer>
            </main>
        </div>
    );
}

function Catalog({route}) {
    const [out, S] = useState({items: []});
    const [page, P] = useState(1);
    const [error, E] = useState('');

    useEffect(() => {
        api('/' + route + '?page=' + page).then(S).catch(e => E(e.message));
    }, [route, page]);

    return (
        <>
            {error && <p role="alert">{error}</p>}
            <Table rows={out.items}/>
            <button disabled={page === 1} onClick={() => P(page - 1)}>Previous API page</button>
            <button disabled={page * 25 >= (out.total || 0)} onClick={() => P(page + 1)}>Next API page</button>
            <span> {out.total || 0} stored records</span>
        </>
    );
}

function BatchPage({batches, selected, task, refresh, data}) {
    const [n, S] = useState('');
    useEffect(() => S(selected?.name || ''), [selected?._id]);

    return (
        <>
            <Table caption="Batch catalog" rows={batches} columns={['_id', 'name', 'source', 'created', 'rows', 'components', 'health', 'archived']}/>
            {selected && (
                <section className="panel">
                    <h2>Manage selected batch</h2>
                    <Field label="Batch name" value={n} onChange={S} maxLength={120}/>
                    <div className="row">
                        <button onClick={() => task(async () => {
                            await api('/batches/' + selected._id, {method: 'PATCH', body: JSON.stringify({name: n})});
                            refresh();
                        }, 'Batch renamed')}>Save name</button>
                        <button onClick={() => task(async () => {
                            await api('/batches/' + selected._id, {method: 'PATCH', body: JSON.stringify({archived: !selected.archived})});
                            refresh();
                        }, 'Archive status updated')}>{selected.archived ? 'Restore' : 'Archive'} batch</button>
                        <button className="danger" onClick={() => {
                            if (confirm('Delete this unreferenced batch? Historical artifacts will remain retained.')) {
                                task(async () => {
                                    await api('/batches/' + selected._id, {method: 'DELETE'});
                                    refresh();
                                }, 'Batch deleted');
                            }
                        }}>Delete unreferenced batch</button>
                    </div>
                </section>
            )}
            <Table caption="Cross-batch descriptive comparison" rows={batches.map(b => ({batch: b.name, source: b.source, components: b.components, measurement_records: b.rows, health: b.health, created: b.created}))}/>
            <Table caption="Batch measurements" rows={data}/>
        </>
    );
}

function ImportPage({task, onCommit}) {
    const [file, F] = useState(null);
    const [name, N] = useState('');
    const [mapping, M] = useState('{}');
    const [units, U] = useState('{}');
    const [preview, P] = useState(null);
    const [confirm, C] = useState(false);

    async function submit(commit) {
        const form = new FormData();
        form.append('file', file);
        form.append('name', name);
        form.append('mapping', mapping);
        form.append('units', units);
        form.append('commit', String(commit));
        const r = await task(() => api('/batches', {method: 'POST', body: form}), commit ? 'Dataset committed' : 'Validation completed');
        if (r) {
            if (commit) onCommit(r);
            else P(r);
        }
    }

    return (
        <section className="panel">
            <h2>Preview → map → validate → commit</h2>
            <p>CSV/XLSX, maximum 25 MiB. Original bytes are retained in MongoDB GridFS. Unit overrides assign labels; they do not convert measurements.</p>
            <label>Measurement file
                <input type="file" accept=".csv,.xlsx" onChange={e => { F(e.target.files[0]); N(e.target.files[0]?.name || ''); P(null); C(false); }}/>
            </label>
            <Field label="Batch name" value={name} onChange={N} maxLength={120}/>
            <label>Column mapping JSON (source column → required column)
                <textarea value={mapping} onChange={e => { M(e.target.value); P(null); C(false); }}/>
            </label>
            <label>Unit override JSON (parameter → unit)
                <textarea value={units} onChange={e => { U(e.target.value); P(null); C(false); }}/>
            </label>
            <button disabled={!file || !name} onClick={() => submit(false)}>Validate and preview</button>
            {preview && (
                <>
                    <p>Health: {preview.health.score}/100 · {preview.health.errors.length} blocking errors</p>
                    {preview.health.errors.map(e => <p role="alert" key={e}>{e}</p>)}
                    <Table rows={preview.preview}/>
                    <Table caption="Validation findings" rows={preview.issues}/>
                    <label className="check">
                        <input type="checkbox" checked={confirm} onChange={e => C(e.target.checked)}/>
                        I reviewed the mappings and units.
                    </label>
                    <button className="primary" disabled={!confirm || preview.health.errors.length > 0} onClick={() => submit(true)}>Commit dataset</button>
                </>
            )}
        </section>
    );
}

function ScreenPage({batch, ctx, rows, run}) {
    const [stage, S] = useState(24);
    const [stat, T] = useState(false);

    return (
        <>
            <section className="panel">
                <h2>Readiness → model & policy → execute → review</h2>
                <label>Screening stage
                    <select value={stage} onChange={e => S(Number(e.target.value))}>
                        {[24, 96, 168].map(t => <option key={t} value={t}>{t} hours</option>)}
                    </select>
                </label>
                <label className="check">
                    <input type="checkbox" checked={stat} onChange={e => T(e.target.checked)}/>Statistics only
                </label>
                <p>Active model: {ctx.modelId || 'None'} · Run: {ctx.run?.id || 'Not screened'}</p>
                <button className="primary" disabled={!batch} onClick={() => run('screen', {batchId: batch, stage, statisticsOnly: stat}, 'Screening persisted')}>Execute screening</button>
            </section>
            <Table caption="Screening evidence" rows={rows} columns={['component_id', 'lot_id', 'parameter', 'current', 'predicted_168h', 'risk_score', 'status', 'explanation']}/>
        </>
    );
}

function Anomaly({rows}) {
    const [par, P] = useState('');
    const [min, M] = useState(0);
    const r = rows.filter(row => (!par || row.parameter === par) && row.risk_score >= min);

    return (
        <>
            <div className="row">
                <label>Parameter
                    <select value={par} onChange={e => P(e.target.value)}>
                        <option value="">All measurements</option>
                        {[...new Set(rows.map(row => row.parameter))].map(p => <option key={p}>{p}</option>)}
                    </select>
                </label>
                <Field label="Minimum risk score" type="number" min="0" max="100" value={min} onChange={M}/>
            </div>
            <p>Robust peer deviations and model forecasts are separate evidence. Scores are not defect probabilities.</p>
            <Chart type="scatter" title="Observed drift versus risk" data={r} x="absolute_drift" y="risk_score"/>
            <Table rows={r} columns={['component_id', 'parameter', 'population_anomaly', 'temporal_anomaly', 'static_violation', 'risk_score', 'status', 'explanation']}/>
        </>
    );
}

function Review({runId, component, task}) {
    const [state, S] = useState('Unreviewed');
    const [note, N] = useState('');

    useEffect(() => {
        if (!runId || !component) return;
        api('/reviews?runId=' + runId + '&componentId=' + encodeURIComponent(component) + '&limit=1').then(r => {
            const v = r.items?.find(x => x.component_id === component);
            S(v?.state || 'Unreviewed');
            N(v?.note || '');
        }).catch(() => {});
    }, [runId, component]);

    return (
        <section className="panel">
            <h2>Engineering review</h2>
            <label>State
                <select value={state} onChange={e => S(e.target.value)}>
                    {['Unreviewed', 'In review', 'Reviewed'].map(v => <option key={v}>{v}</option>)}
                </select>
            </label>
            <label>Review note
                <textarea value={note} maxLength={2000} onChange={e => N(e.target.value)}/>
            </label>
            <button onClick={() => task(() => action('review', {runId, componentId: component, state, note}), 'Review saved')}>Save review note</button>
        </section>
    );
}

function Prediction({batch, models, task}) {
    const [mid, M] = useState('');
    const [out, O] = useState([]);

    return (
        <>
            <label>Prediction model
                <select value={mid} onChange={e => M(e.target.value)}>
                    <option value="">Choose model</option>
                    {models.map(m => <option key={m._id} value={m._id}>{m._id} · cutoff {m.manifest?.cutoff}h</option>)}
                </select>
            </label>
            <p>Prediction selection does not activate the model. Unsupported forecasts are flagged; uncertainty intervals may be withheld.</p>
            <button disabled={!batch || !mid} onClick={() => task(async () => O(await action('predict', {batchId: batch, modelId: mid})), 'Predictions computed')}>Predict active batch</button>
            <Table rows={out}/>
        </>
    );
}

function Laboratory({batch, models, aux, run, task, setAux}) {
    const [candidates, CC] = useState(['Linear', 'Ridge-1', 'Ridge-10', 'RandomForest', 'GradientBoosting-2', 'GradientBoosting-3']);
    const [cutoff, C] = useState(24);
    const [seed, S] = useState(42);
    const [trees, T] = useState(80);
    const [stages, G] = useState(100);
    const [mid, M] = useState('');

    return (
        <>
            <section className="panel">
                <h2>Controlled training experiment</h2>
                <p>Lot-disjoint train, validation, calibration and test sets. Target: 168-hour measurement.</p>
                <div className="grid">
                    <label>Input cutoff
                        <select value={cutoff} onChange={e => C(Number(e.target.value))}>
                            <option value={24}>24 hours</option>
                            <option value={96}>96 hours</option>
                        </select>
                    </label>
                    <Field label="Random seed" value={seed} onChange={S} type="number" min="0"/>
                    <Field label="Forest trees" value={trees} onChange={T} type="number" min="20" max="300"/>
                    <Field label="Boosting stages" value={stages} onChange={G} type="number" min="20" max="300"/>
                </div>
                <label>Candidate models
                    <select multiple value={candidates} onChange={e => CC(Array.from(e.target.selectedOptions, o => o.value))}>
                        {['Linear', 'Ridge-1', 'Ridge-10', 'RandomForest', 'GradientBoosting-2', 'GradientBoosting-3'].map(c => <option key={c}>{c}</option>)}
                    </select>
                </label>
                <button className="primary" disabled={!batch || !candidates.length} onClick={() => run('train', {batchId: batch, options: {cutoff, seed, trees, boosting_stages: stages, candidate_names: candidates}}, 'Model trained and registered in GridFS; activation remains explicit')}>Train candidate models</button>
            </section>
            <section className="panel">
                <label>Registered model
                    <select value={mid} onChange={e => { M(e.target.value); if (e.target.value) task(async () => setAux(await action('model', {modelId: e.target.value})), null); }}>
                        <option value="">Choose model</option>
                        {models.map(m => <option key={m._id}>{m._id}</option>)}
                    </select>
                </label>
                <button disabled={!mid} onClick={() => {
                    if (confirm('Activate this model for future screenings?')) run('activate', {modelId: mid}, 'Model activated');
                }}>Activate selected model</button>
            </section>
            <Table caption="Candidate comparisons" rows={aux?.comparison || []}/>
            <Table caption="Validation permutation importance (not causal attribution)" rows={aux?.importance || []}/>
            {aux?.manifest && (
                <details>
                    <summary>Model manifest and split provenance</summary>
                    <pre>{JSON.stringify(aux.manifest, null, 2)}</pre>
                </details>
            )}
        </>
    );
}

function Simulator({run}) {
    const [name, N] = useState('Latent Defect');
    const [seed, S] = useState(42);
    const [n, C] = useState(600);
    const [lots, L] = useState(12);
    const [noise, O] = useState(.015);
    const [severity, V] = useState(1);
    const [defect, D] = useState(.15);
    const [out, R] = useState(null);

    return (
        <section className="panel">
            <h2>Reproducible synthetic experiment</h2>
            <p>Reference scenarios use the original 120-component recipe. Custom populations use the controls below. Baseline and simulation are both screened and retained.</p>
            <label>Scenario
                <select value={name} onChange={e => N(e.target.value)}>
                    {['Normal Lot', 'Obvious Failure', 'Latent Defect', 'Early Warning', 'Population Anomaly', 'Missing measurements', 'Mixed-quality population', 'Elevated measurement variation'].map(n => <option key={n}>{n}</option>)}
                </select>
            </label>
            <div className="grid">
                {[
                    ['Seed', seed, S, 0, 2147483647, 1],
                    ['Components', n, C, 100, 100000, 1],
                    ['Lots', lots, L, 1, 100, 1],
                    ['Noise', noise, O, 0, .2, .005],
                    ['Severity', severity, V, .2, 2, .1],
                    ['Defect fraction', defect, D, 0, .5, .01]
                ].map(([label, value, onChange, min, max, step]) => (
                    <Field key={label} {...{label, value, onChange, min, max, step}} type="number"/>
                ))}
            </div>
            <button className="primary" onClick={async () => R(await run('simulate', {name, seed, n, lots, noise, severity, defect_fraction: defect}, 'Baseline and scenario persisted'))}>Run scenario</button>
            {out && <Table caption="Baseline versus simulation dispositions" rows={out.comparison || []}/>}
            {out && <p>Baseline: {out.baseline}<br/>Simulation: {out.batchId}. Select either batch to inspect its screening results.</p>}
        </section>
    );
}

function PolicyEditor({ctx, batch, task, run}) {
    const [config, C] = useState(ctx.policy || {});
    const [out, O] = useState(null);
    useEffect(() => C(ctx.policy || {}), [ctx.policy]);

    return (
        <>
            <section className="panel">
                <h2>Versioned engineering policy</h2>
                <p>Illustrative rules, not industrial standards. Changes affect future screenings only.</p>
                <div className="grid">
                    {Object.entries(config).map(([k, v]) => (
                        <Field key={k} label={k.replaceAll('_', ' ')} value={v} type="number" step="any" onChange={x => { C({...config, [k]: x}); O(null); }}/>
                    ))}
                </div>
                <button onClick={() => task(async () => O(await action('policy', {config, ...(batch ? {batchId: batch} : {})})), 'Policy validated and preview computed')}>Validate and preview</button>
                <button disabled={!out} onClick={() => {
                    if (confirm('Save this policy version for future screenings?')) run('policy', {config, save: true}, 'Policy version saved');
                }}>Save policy version</button>
            </section>
            {Array.isArray(out) && <Table caption="Before/after policy decisions" rows={out}/>}
            <Catalog route="policies"/>
        </>
    );
}

function Reports({ctx, batch, run, task, aux}) {
    const [kind, K] = useState('batch');
    const [made, M] = useState(null);

    return (
        <>
            <section className="panel">
                <label>Report type
                    <select value={kind} onChange={e => K(e.target.value)}>
                        {['batch', 'quality', 'evaluation', 'audit', 'scenario'].map(k => <option key={k}>{k}</option>)}
                    </select>
                </label>
                <p>Component reports are available in Component Explorer. Reports are durably stored in MongoDB GridFS.</p>
                <button onClick={async () => M(await run('report', {kind, ...(batch ? {batchId: batch} : {}), ...(ctx.run ? {runId: ctx.run.id} : {}), ...(ctx.modelId ? {modelId: ctx.modelId} : {})}, 'Report files persisted to GridFS'))}>Generate report</button>
                {made && ['pdf', 'xlsx', 'csv'].map(ext => (
                    <button key={ext} onClick={() => task(() => download(made.reportId, ext), 'Downloaded ' + ext.toUpperCase())}>{ext.toUpperCase()}</button>
                ))}
            </section>
            <Table caption="Report history" rows={aux?.items || []}/>
            <label>Download stored report
                <select defaultValue="" onChange={e => { if (e.target.value) task(() => download(e.target.value, 'pdf'), 'PDF downloaded'); }}>
                    <option value="">Choose a report</option>
                    {(aux?.items || []).filter(r => r.kind !== 'backup').map(r => (
                        <option key={r._id} value={r._id}>{r.kind} · {r.created}</option>
                    ))}
                </select>
            </label>
        </>
    );
}

function Settings({ctx, run, task}) {
    const [name, N] = useState(ctx.workspace || 'Engineering workspace');

    return (
        <section className="panel">
            <Field label="Workspace display name" value={name} onChange={N} maxLength={100}/>
            <button onClick={() => run('settings', {name}, 'Settings saved')}>Save settings</button>
            <h2>Backup and demonstration context</h2>
            <button onClick={async () => {
                const r = await run('backup', {}, 'Backup created');
                if (r) task(() => download(r.reportId, 'zip'), 'Backup downloaded');
            }}>Download workspace backup</button>
            <button onClick={() => {
                if (confirm('Create a fresh synthetic batch? Existing work is preserved.')) run('reset', {}, 'Fresh synthetic batch created');
            }}>Create fresh demo batch</button>
        </section>
    );
}

export {App, Table, ImportPage, ScreenPage};

if (!globalThis.__ESS_TEST__) {
    createRoot(document.getElementById('root')).render(<BrowserRouter><App/></BrowserRouter>);
}
