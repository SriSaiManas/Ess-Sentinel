"""Explicit policy changes, searchable audit, and real persisted exports."""
from dataclasses import asdict
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from ess.config import Policy
from ess.risk.engine import screen,component_summary
from ess.prediction.evaluation import compare_screening
from services.store import policy_id,atomic,uid
from services.reports import report_pdf,excel_bytes
from ess.reports.export import csv_bytes
from ui.theme import chart
from ui.common import action,table,exports,download,metadata

def policy(c):
    st.caption('Illustrative engineering rules, not industrial standards. Policy modifies decisions, never the stored measurements.')
    st.code(policy_id(c.policy),language=None)
    with st.form('policy_editor'):
        columns=st.columns(3);values={}
        for i,(k,v) in enumerate(asdict(c.policy).items()):
            values[k]=columns[i%3].number_input(k.replace('_',' ').title(),value=v,step=1 if isinstance(v,int) else .01,key='policy_'+k)
        preview=st.form_submit_button('Validate and preview policy')
    if preview:
        draft=action(c,'Policy validation',lambda:Policy(**values).validate())
        if draft:st.session_state.policy_draft=asdict(draft);st.session_state.pop('policy_comparison',None)
    draft_data=st.session_state.get('policy_draft')
    if draft_data:
        draft=Policy(**draft_data).validate()
        changes=pd.DataFrame([{'field':k,'current':v,'proposed':draft_data[k]} for k,v in asdict(c.policy).items() if v!=draft_data[k]])
        st.dataframe(changes,hide_index=True)
        if c.data is not None and st.button('Simulate policy on active batch'):
            stage=c.model['manifest']['cutoff'] if c.model else 24
            with st.spinner('Computing actual before/after decisions…'):
                before=action(c,'Current policy simulation',lambda:screen(c.data,c.model,c.policy,stage))
                after=action(c,'Draft policy simulation',lambda:screen(c.data,c.model,draft,stage))
            if before is not None and after is not None:
                st.session_state.policy_comparison=(c.bid,policy_id(draft),pd.DataFrame({'component_id':before.component_id,'parameter':before.parameter,'before':before.status,'after':after.status,'score_before':before.risk_score,'score_after':after.risk_score}))
        comparison=st.session_state.get('policy_comparison')
        if comparison and comparison[:2]==(c.bid,policy_id(draft)):
            q=comparison[2];st.write(f'{int((q.before!=q.after).sum())} of {len(q)} parameter records change category.');table(q[q.before!=q.after],'policychange');exports(c,q,'policy_simulation','policyexport')
        confirm=st.checkbox('I confirm the displayed policy changes for future screenings.')
        if st.button('Save policy version',disabled=not confirm,type='primary'):
            result=action(c,'Policy update',lambda:c.store.save_policy(draft,True))
            if result:st.session_state.pop('policy_draft',None);st.rerun()
    if c.run:st.caption('Latest screening used policy '+c.run['policy_id']+'. Historical results remain immutable.')
    st.subheader('Policy version history');table(c.store.table('policies'),'policyversions')

def audit(c):
    events=c.store.table('events').sort_values('id',ascending=False)
    a,b,z=st.columns(3);query=a.text_input('Search audit events');types=b.multiselect('Actions',sorted(events.action.unique()));outcomes=z.multiselect('Outcomes',sorted(events.outcome.unique()))
    if query:events=events[events.astype(str).agg(' '.join,axis=1).str.contains(query,case=False,regex=False)]
    if types:events=events[events.action.isin(types)]
    if outcomes:events=events[events.outcome.isin(outcomes)]
    table(events,'audit');exports(c,events,'audit_trail','auditexport')
    st.caption('Read-only UI. Local SQLite records are transactional, but are not cryptographically tamper-proof.')

def reporting(c):
    choices=['Data quality','Model evaluation','Audit trail']
    if c.result is not None:choices=['Batch screening','Component inspection']+choices
    if st.session_state.get('scenario_pair'):choices+=['Scenario comparison']
    kind=st.selectbox('Report type',choices);tables={};r=None
    if kind in ['Batch screening','Component inspection']:
        c.require_results();r=c.result
        if kind=='Component inspection':
            component=st.selectbox('Report component',r.component_id.unique());r=r[r.component_id==component]
            tables['Measurements']=r[['parameter','unit','value_0h','value_24h','predicted_168h','risk_score','status']]
        else:
            tables['Component dispositions']=component_summary(r).status.value_counts().rename_axis('Disposition').reset_index(name='Components')
            tables['Lot summary']=r.groupby('lot_id').agg(records=('component_id','size'),flagged_records=('dynamic_flag','sum'),predicted_crossings=('predicted_crossing','sum')).reset_index()
            tables['Priority findings · top 20']=r.sort_values('risk_score',ascending=False).head(20)[['component_id','parameter','unit','risk_score','status','explanation']]
    elif kind=='Data quality':
        _,health,issues=c.health();tables['Validation findings']=issues.head(500)
        if len(issues)>500:st.caption('PDF preview limited to first 500 issue rows; export the full quality CSV from Data Quality.')
    elif kind=='Model evaluation':
        if c.model is None:st.info('No evaluated model available.');return
        tables['Regression comparison']=c.model['comparison'];tables['Test errors by parameter']=c.model['test_predictions'].groupby('parameter').residual.agg(['count','mean','std']).reset_index()
    elif kind=='Audit trail':tables['Recent audit events · up to 500']=c.store.table('events').tail(500)[['id','timestamp','action','batch_id','outcome']]
    elif kind=='Scenario comparison':
        rows=[]
        for label,bid in zip(['Baseline','Simulation'],st.session_state.scenario_pair):
            run=c.store.latest_run(bid);s=component_summary(c.store.results(run['id']));rows.append({'Population':label,'Components':len(s),'Flagged':int(s.dynamic_flag.sum()),'Critical':int((s.status=='CRITICAL').sum())})
        tables['Scenario comparison']=pd.DataFrame(rows)
    for name,frame in tables.items():st.subheader(name);st.dataframe(frame.head(25),hide_index=True)
    signature=(kind,c.bid,c.run['id'] if c.run else None,c.mid,component if kind=='Component inspection' else '')
    if st.button('Generate report files',type='primary',icon=':material/description:'):
        def build():
            pdf=report_pdf(kind,metadata(c),tables,screening=r)
            excel=excel_bytes(tables);csv=csv_bytes(next(iter(tables.values())))
            rid=uid('report')
            for extension,content in [('pdf',pdf),('xlsx',excel),('csv',csv)]:atomic(c.store.path('reports',rid,'report.'+extension),content)
            c.store.event('report_generated',{'report_id':rid,'kind':kind,'table_rows':{k:len(v) for k,v in tables.items()}},c.bid or '')
            return pdf,excel,csv
        files=action(c,'Report generation',build)
        if files:st.session_state.report_files=(signature,files)
    saved=st.session_state.get('report_files')
    if saved and saved[0]==signature:
        for label,content,ext,mime in zip(['Download PDF','Download Excel','Download summary CSV'],saved[1],['pdf','xlsx','csv'],['application/pdf','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','text/csv']):
            download(c,label,content,'ess_report.'+ext,mime)
        st.caption('PDF and Excel contain all listed sections; summary CSV contains the first section. Files were generated and persisted before these buttons appeared.')
