"""Import, data quality, screening and component investigation pages."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from ess.data.validation import ingest,REQUIRED,DEFAULTS
from ess.data.synthetic import generate
from ess.ui.charts import trajectory
from ess.risk.engine import component_summary
from services.quality import inspect,timestamped
from services.reports import report_pdf
from ui.theme import chart,kpis,COLORS
from ui.common import action,table,exports,download,filtered,goto,select_component,metadata

def ingestion(c):
    st.caption('CSV / XLSX · maximum 25 MB · measurements remain local · original upload retained')
    exports(c,timestamped(generate(20,2)),'example_schema','schema')
    file=st.file_uploader('Drop a measurement dataset here',type=['csv','xlsx'])
    if file is None:
        st.info('Upload a dataset to preview its schema, map columns, validate units and confirm import.');return
    try:raw=ingest(file.getvalue(),file.name)
    except ValueError as e:st.error(str(e));return
    st.write(f'**{file.name}** · {len(file.getvalue()):,} bytes · {len(raw):,} records')
    table(raw.head(50),'raw');st.dataframe(pd.DataFrame({'column':raw.columns,'detected_type':raw.dtypes.astype(str).values}),hide_index=True)
    mapping={}
    with st.expander('Column mapping',expanded=True):
        cols=st.columns(3)
        for i,target in enumerate(REQUIRED+list(DEFAULTS)+['value_96h','value_168h','defect_label']):
            options=['Not supplied']+list(raw.columns)
            chosen=cols[i%3].selectbox(target,options,index=options.index(target) if target in options else 0,key='map_'+target)
            if chosen!='Not supplied':
                if chosen in mapping:st.error('A source column is mapped more than once.');return
                mapping[chosen]=target
    try:normalized=ingest(file.getvalue(),file.name,mapping)
    except ValueError as e:st.error(str(e));return
    edits={}
    with st.expander('Explicit unit assignment'):
        st.caption('This assigns unit labels only; it does not convert measurements. Leave blank to preserve the source unit.')
        if 'parameter' in normalized:
            for par in normalized.parameter.dropna().unique():
                unit=st.text_input(str(par)+' unit override',key='unit_'+str(par))
                if unit:edits[str(par)]=unit;normalized.loc[normalized.parameter==par,'unit']=unit
    clean,health,issues=inspect(normalized)
    st.subheader('Normalized preview');table(clean.head(25),'normalized')
    st.write(f'Blocking errors: {len(health["errors"])} · completeness {health["completeness"]:.1f}%')
    table(issues,'import_issues');exports(c,issues,'validation_findings','import_findings')
    name=st.text_input('Batch name',value=file.name.rsplit('.',1)[0])
    confirm=st.checkbox('I reviewed mappings and units and confirm importing this dataset.')
    if st.button('Commit dataset',type='primary',disabled=bool(health['errors']) or not confirm):
        bid=action(c,'Dataset import',lambda:c.work.commit(clean,name,'UPLOADED',raw=file.getvalue(),metadata={'filename':file.name,'column_mapping':mapping,'unit_assignments':edits,'validation_warnings':health['warnings'],'defaults_applied':[k for k in DEFAULTS if k not in normalized]}))
        if bid:st.rerun()

def quality(c):
    c.require_data();clean,h,issues=c.health()
    kpis([('Completeness',f'{h["completeness"]:.1f}%','Available measurement cells','#36D6C5'),('Dataset health',f'{h["score"]}/100','Heuristic schema score','#57A6FF'),('Blocking messages',len(h['errors']),'Resolve before screening','#F16C76'),('Finding instances',h['issue_count'],'May include dataset-level summaries','#F5B84B'),('Timestamp fields',h['timestamp_columns'],'ISO timestamp columns verified','#F1F5FB'),('Measurement records',len(clean),'One parameter / session / condition','#F1F5FB')])
    if not h['timestamp_columns']:st.info('No acquisition timestamps supplied; chronological validation is unavailable. Nominal burn-in stage labels are retained.')
    severity=st.multiselect('Issue severity',['ERROR','WARNING','INFO'],default=['ERROR','WARNING','INFO'])
    table(issues[issues.severity.isin(severity)],'qualityissues')
    if h['details_truncated']:st.warning('Row-level detail is capped at 5,000 issue instances; total count is not truncated.')
    values=[x for x in clean if x.startswith('value_')];a,b=st.columns(2)
    with a: chart(px.bar(clean[values].isna().sum().rename_axis('feature').reset_index(name='missing'),x='feature',y='missing',title='Missing observations'))
    with b:
        sample=clean[values].head(200).isna().astype(int);chart(px.imshow(sample.to_numpy(),x=values,aspect='auto',color_continuous_scale=['#17243A','#F5B84B'],title='Missingness · first 200 records'))
    cov=clean.assign(coverage=clean[values].notna().mean(axis=1)*100).groupby('lot_id').coverage.mean().reset_index();chart(px.bar(cov,x='lot_id',y='coverage',labels={'coverage':'Measurement coverage %'}))
    exports(c,issues,'data_quality','qualityexport')

def screening(c):
    c.require_data();_,health,_=c.health()
    st.write('**1** Batch readiness → **2** Model & policy → **3** Execute → **4** Review evidence')
    a,b=st.columns(2)
    with a:
        stage=st.selectbox('Screening stage (hours)',[24,96,168],key='screen_stage')
        st.caption(f'{len(c.data):,} records · health {health["score"]}/100 · {len(health["errors"])} blocking issues')
    with b:
        mode=st.radio('Evidence mode',['Active model + statistics','Statistics only'])
        st.caption(f'Active model: {c.mid or "None"} · policy {__import__("services.store",fromlist=["policy_id"]).policy_id(c.policy)[:12]}')
    if st.button('Execute screening',type='primary',disabled=bool(health['errors']),icon=':material/play_arrow:'):
        progress=st.progress(0.,text='Loading batch')
        rid=action(c,'Screening',lambda:c.work.screen(c.bid,stage,mid='' if mode=='Statistics only' else c.mid,progress=lambda value,text:progress.progress(value,text=text)))
        if rid:st.rerun()
    c.require_results();s=component_summary(c.result)
    kpis([('Screened',len(s),'Unique component IDs','#F1F5FB'),('Normal',int((s.status=='NORMAL').sum()),'No configured review rule triggered','#37C991'),('Flagged',int(s.dynamic_flag.sum()),'WATCH + HIGH RISK + CRITICAL','#F5B84B'),('Critical',int((s.status=='CRITICAL').sum()),'Subset of flagged components','#F16C76'),('Incomplete',int(c.result.groupby('component_id').incomplete_assessment.any().sum()),'May overlap flagged categories','#57A6FF'),('Records',len(c.result),'Per-parameter evidence rows','#F1F5FB')])
    st.caption(f'Run {c.run["id"]} · assessed at {c.run["stage"]}h · {c.run["created"]}')
    r=filtered(c,'screen');default=['component_id','lot_id','parameter','status','risk_score','predicted_168h','unit','review_state']
    columns=st.multiselect('Visible columns',list(r.columns),default=default)
    selected=table(r[columns] if columns else r[default],'screen_results',select=True)
    # A separate selector stays usable even if the ID column is hidden.
    if len(r):
        cid=st.selectbox('Open component',r.component_id.unique(),key='screen_open')
        st.button('Inspect selected component',on_click=goto,args=('Component Explorer',cid))
    exports(c,r,'screening_results','screenexports')

def anomaly(c):
    c.require_results();r=filtered(c,'anomaly')
    a,b=st.columns(2);par=a.selectbox('Measurement',sorted(c.result.parameter.unique()));score=b.slider('Minimum engineering risk',0,100,0)
    r=r[(r.parameter==par)&(r.risk_score>=score)]
    st.caption('Robust Z uses cohort median/MAD. Isolation Forest percentile is relative to training scores. Neither proves a physical defect.')
    if r.empty:st.info('No matching measurement records.');return
    a,b=st.columns(2)
    with a:chart(px.histogram(r,x='population_z',color='status',color_discrete_map=COLORS,title='Population deviation · robust Z'))
    with b:chart(px.scatter(r,x='population_median',y='current',color='status',color_discrete_map=COLORS,hover_data=['component_id','lot_id'],labels={'current':f'Observed ({r.unit.iloc[0]})','population_median':f'Peer median ({r.unit.iloc[0]})'}))
    chart(px.scatter(r,x='value_0h',y='value_24h',color='risk_score',hover_data=['component_id'],title='Early measurement comparison'))
    table(r[['component_id','lot_id','population_z','temporal_z','if_percentile','risk_score','status']],'anomalytable')
    row=select_component(c,'anomaly_component');chart(trajectory(c.data,row))
    st.write('**Measured evidence:**');st.write(f'Current {row.current:.4g} {row.unit}; peer median {row.population_median:.4g}; observed drift {row.absolute_drift:.4g}.')
    st.write('**Model inference and policy reasons:**');st.write(row.explanation)
    points=['population_points','drift_points','prediction_points','proximity_points','isolation_points'];chart(px.bar(x=points,y=[row[x] for x in points],labels={'x':'Evidence','y':'Risk points'}))

def component(c):
    c.require_results();row=select_component(c)
    st.subheader(f'{row.component_id} · {row.status}')
    tabs=st.tabs(['Trajectory','Evidence & prediction','Review & history','Report'])
    with tabs[0]:
        chart(trajectory(c.data,row));st.caption('Peer future ranges and gray future points are retrospective only. They are excluded from early predictions.')
        records=c.data[c.data.component_id==row.component_id];table(records,'component_history')
    with tabs[1]:
        st.write(row.explanation)
        fields=['current','population_median','population_mad','population_z','temporal_z','if_score','predicted_168h','interval_lower','interval_upper','predicted_margin','risk_score','static_violation','population_anomaly','predicted_crossing','model_version','policy_hash']
        st.dataframe(pd.DataFrame({'Evidence':fields,'Value':[str(row[f]) for f in fields]}),hide_index=True)
        st.caption('Approximate calibration intervals are withheld outside model support. Category overrides can exceed the category implied by the additive score.')
    with tabs[2]:
        reviews=c.store.table('reviews');existing=reviews[(reviews.run_id==c.run['id'])&(reviews.component_id==row.component_id)]
        states=['Unreviewed','In review','Reviewed'];previous=existing.iloc[0].state if len(existing) else 'Unreviewed'
        state=st.selectbox('Review state',states,index=states.index(previous),key='review_state_'+row.component_id)
        note=st.text_area('Engineering review note',value=existing.iloc[0].note if len(existing) else '',max_chars=2000,key='review_note_'+row.component_id)
        st.caption('Review state is an annotation. It does not change the measured data, risk score or disposition.')
        if st.button('Save review note'):action(c,'Review update',lambda:c.store.review(c.run['id'],row.component_id,state,note))
        events=c.store.table('events');matches=events.details.str.contains(row.component_id,regex=False);table(events[matches][['timestamp','action','outcome','details']],'component_events')
    with tabs[3]:
        if st.button('Generate component report',type='primary'):
            subset=c.result[c.result.component_id==row.component_id]
            pdf=action(c,'Component report',lambda:report_pdf('Component inspection',metadata(c),{'Measurements':subset[['parameter','unit','value_0h','value_24h','predicted_168h','risk_score','status']]},screening=subset))
            if pdf:
                st.session_state['component_pdf']=(c.run['id'],row.component_id,pdf);c.store.event('report_generated',{'kind':'component','component_id':row.component_id},c.bid)
        saved=st.session_state.get('component_pdf')
        if saved and saved[:2]==(c.run['id'],row.component_id):download(c,'Download component PDF',saved[2],'component_inspection.pdf','application/pdf')
