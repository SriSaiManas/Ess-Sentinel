"""Command views: truthful overview, local operations and batch comparison."""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from ui.theme import kpis,chart,COLORS
from ui.common import table,goto,action,exports,filtered
from ess.risk.engine import component_summary

def overview(c):
    c.require_data(); _,health,issues=c.health();r=c.result
    s=component_summary(r) if r is not None else None
    kpis([('Total components',f'{c.data.component_id.nunique():,}','Unique IDs in active batch','#F1F5FB'),('Screened components',f'{len(s):,}' if s is not None else '—','Latest persisted screening run','#57A6FF'),('Flagged components',int(s.dynamic_flag.sum()) if s is not None else '—','At least one record requires review','#F5B84B'),('Critical findings',int((s.status=='CRITICAL').sum()) if s is not None else '—','Unique components at worst severity','#F16C76'),('Data quality',f'{health["score"]}/100','Schema heuristic; not confidence','#36D6C5'),('Model readiness','Available' if c.model else 'Not trained','Unqualified for production use','#36D6C5')])
    cols=st.columns(3)
    cols[0].button('Inspect batch',on_click=goto,args=('Batch Explorer',),icon=':material/inventory_2:')
    cols[1].button('Open screening',on_click=goto,args=('Screening',),icon=':material/fact_check:')
    cols[2].button('Review data quality',on_click=goto,args=('Data Quality',),icon=':material/rule:')
    if r is None: st.info('The batch is ready for screening. No results have been invented.');return
    a,b=st.columns([1,1.4])
    with a:
        st.subheader('Screening disposition');q=s.status.value_counts().rename_axis('status').reset_index(name='components');chart(px.pie(q,names='status',values='components',hole=.7,color='status',color_discrete_map=COLORS))
    with b:
        st.subheader('Risk distribution');chart(px.histogram(s,x='risk_score',color='status',color_discrete_map=COLORS,nbins=24,labels={'risk_score':'Engineering score / 100'}))
    a,b=st.columns([1.4,1])
    with a:
        st.subheader('Priority findings')
        for i,(_,row) in enumerate(s[s.dynamic_flag].head(4).iterrows()):
            with st.container(border=True):
                st.write(f'**{row.component_id}** · {row.lot_id} · **{row.status}**')
                st.caption(row.explanation)
                st.caption('Detected '+str(row.timestamp)+' · Recommended next step: qualified engineering review')
                st.button('Inspect component',key='finding'+str(i),on_click=goto,args=('Component Explorer',row.component_id))
    with b:
        st.subheader('Flagged by lot');q=s.groupby('lot_id').dynamic_flag.sum().reset_index();chart(px.bar(q,x='lot_id',y='dynamic_flag',labels={'dynamic_flag':'Components requiring review'}))
        st.subheader('Quality findings');st.dataframe(issues.groupby('severity').size().rename('Issues'),width='stretch')
    par=st.selectbox('Measurement trend',sorted(c.data.parameter.unique()))
    q=c.data[c.data.parameter==par];v=[x for x in q if x.startswith('value_')]
    agg=q[v].median().rename_axis('stage').reset_index(name='median');chart(px.line(agg,x='stage',y='median',markers=True,labels={'median':f'Median ({q.unit.iloc[0]})'}))
    if c.model:
        st.subheader('Evaluated model performance');st.dataframe(c.model['comparison'].query("split == 'test'"),hide_index=True)
    st.subheader('Recent activity');st.dataframe(c.store.table('events').tail(6).iloc[::-1][['timestamp','action','outcome']],hide_index=True)

def operations(c):
    c.require_data();st.info('Local historical batch monitoring. No industrial telemetry connection or background queue is configured.')
    if st.button('Refresh local activity',icon=':material/refresh:'): c.store.event('view_refreshed',{'dataset_changed':False},c.bid);st.rerun()
    st.caption('Refreshing reloads the local event store. It does not acquire new measurements.')
    a,b=st.columns(2)
    with a:
        st.subheader('Recent screening executions');st.dataframe(c.store.table('runs').tail(10).iloc[::-1].drop(columns=['summary']),hide_index=True)
    with b:
        st.subheader('Operational events');st.dataframe(c.store.table('events').tail(15).iloc[::-1][['timestamp','action','outcome']],hide_index=True)
    st.subheader('Latest stored measurements');table(c.data.tail(100),'latest')
    if c.result is not None: table(filtered(c,'ops')[['component_id','lot_id','parameter','status','review_state','risk_score']],'opstable')

def batches(c):
    allb=c.store.table('batches');query=st.text_input('Search batch name, ID or lot');sources=st.multiselect('Source',sorted(allb.source.unique()))
    b=allb.copy()
    if sources:b=b[b.source.isin(sources)]
    if query:
        matched=[]
        for _,row in b.iterrows():
            lots=c.store.data(row.id).lot_id.unique()
            if query.lower() in ' '.join([row.id,row['name'],*map(str,lots)]).lower():matched.append(row.id)
        b=b[b.id.isin(matched)]
    runs=c.store.table('runs');latest=runs.sort_values('created').drop_duplicates('batch_id',keep='last') if len(runs) else runs
    b['screening_status']=b.id.map({row.batch_id:'Screened' for _,row in latest.iterrows()}).fillna('Not screened')
    state=st.selectbox('Screening state',['All','Screened','Not screened'])
    if state!='All':b=b[b.screening_status==state]
    dates=st.date_input('Imported on or after',value=None)
    if dates:b=b[pd.to_datetime(b.created,utc=True).dt.date>=dates]
    table(b[['id','name','source','created','components','rows','health','screening_status']],'batches')
    if len(b):
        selected=st.selectbox('Batch details',list(b.id),format_func=lambda x:b.set_index('id').loc[x,'name'])
        d=c.store.data(selected);record=b[b.id==selected].iloc[0]
        st.write(f'{d.lot_id.nunique()} lots · {len(d)} records · {d.component_id.nunique()} components')
        st.dataframe(d.filter(regex='^value_').notna().mean().mul(100).rename('Coverage %'),width='stretch')
        latest=c.store.latest_run(selected)
        if latest:st.caption(f'Model {latest["model_id"]} · policy {latest["policy_id"]} · stage {latest["stage"]}h')
        if st.button('Set active batch',type='primary'):c.store.set('active_batch',selected);st.rerun()
    comparisons=st.multiselect('Compare up to three batches',list(allb.id),format_func=lambda x:allb.set_index('id').loc[x,'name'],max_selections=3)
    if len(comparisons)>1:
        rows=[];measurements=[]
        for bid in comparisons:
            data=c.store.data(bid);run=c.store.latest_run(bid);s=component_summary(c.store.results(run['id'])) if run else None
            rows.append(dict(batch=allb.set_index('id').loc[bid,'name'],components=data.component_id.nunique(),flagged=int(s.dynamic_flag.sum()) if s is not None else None))
            q=data.groupby(['parameter','unit']).value_24h.median().reset_index();q['batch']=allb.set_index('id').loc[bid,'name'];measurements.append(q)
        st.dataframe(pd.DataFrame(rows),hide_index=True);st.dataframe(pd.concat(measurements),hide_index=True)
        st.caption('Descriptive comparison only. Differences between batches do not establish a causal process change.')
    exports(c,b.drop(columns='metadata'),'batch_catalog','batch_export')
