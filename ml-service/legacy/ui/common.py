"""Shared session context, bounded tables, downloads and error handling."""
from dataclasses import dataclass
from pathlib import Path
from html import escape
import json,math
import pandas as pd
import streamlit as st
from services.workspace import Workspace
from services.store import Store,policy_id
from services.quality import inspect
from services.reports import excel_bytes
from ess.reports.export import csv_bytes
from ess.risk.engine import component_summary

@st.cache_data(show_spinner=False)
def data_at(root,bid): return Store(root).data(bid)
@st.cache_data(show_spinner=False)
def results_at(root,rid): return Store(root).results(rid)
@st.cache_data(show_spinner=False)
def health_at(root,bid): return inspect(data_at(root,bid))
@st.cache_resource(show_spinner=False)
def model_at(root,mid): return Store(root).model(mid)

@dataclass
class Context:
    work: Workspace
    bid: str|None
    def __post_init__(self):
        self.store=self.work.store; self.root=str(self.store.root)
        batches=self.store.table('batches'); selected=batches[batches.id==self.bid]
        self.meta=selected.iloc[0].to_dict() if len(selected) else None
        self.data=data_at(self.root,self.bid) if self.meta else None
        self.run=self.store.latest_run(self.bid) if self.meta else None
        self.result=results_at(self.root,self.run['id']) if self.run else None
        self.mid=self.store.get('active_model'); self.policy=self.store.policy()
        try: self.model=model_at(self.root,self.mid) if self.mid else None
        except ValueError as exc:
            self.model=None
            st.warning(str(exc)+' Select or train a compatible model in Model Laboratory.')
    def require_data(self):
        if self.data is None: st.info('Select a batch in the header or import a dataset to begin.');st.stop()
    def require_results(self):
        self.require_data()
        if self.result is None: st.info('No screening run for this batch. Open Screening and execute an assessment.');st.stop()
        if self.run['policy_id']!=policy_id(self.policy) or self.run['model_id']!=(self.mid or ''):
            st.warning('Historical screening result: the active model or policy has changed. Re-screen to apply current settings.')
    def health(self): self.require_data();return health_at(self.root,self.bid)

def goto(page,component=None):
    st.session_state.page=page
    if component: st.session_state.focus_component=component

def action(ctx,name,fn):
    try:
        result=fn(); st.success(name+' completed.'); return result
    except Exception as e:
        ref=ctx.work.error(name,e,ctx.bid or '')
        st.error(f'{name} failed: {str(e) if isinstance(e,ValueError) else "See System Diagnostics for the recorded error."} Reference {ref}.')
        return None

def download(ctx,label,data,filename,mime,key=None):
    st.download_button(label,data,file_name=filename,mime=mime,key=key,on_click=lambda:ctx.store.event('export_downloaded',{'filename':filename,'bytes':len(data)},ctx.bid or ''))

def exports(ctx,data,prefix,key=''):
    a,b=st.columns(2)
    with a: download(ctx,'Download CSV',csv_bytes(data),prefix+'.csv','text/csv',key+'csv')
    with b: download(ctx,'Download Excel',excel_bytes({'Records':data}),prefix+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key+'xlsx')

def table(data,key,limit=50,select=False):
    if data.empty: st.info('No records match this view.');return None
    pages=max(1,math.ceil(len(data)/limit))
    n=int(st.number_input('Page',min_value=1,max_value=pages,value=1,key=key+'_page'))
    subset=data.iloc[(n-1)*limit:n*limit]
    st.caption(f'{len(data):,} records · page {n}/{pages} · {limit} rows per page')
    if select:
        event=st.dataframe(subset,hide_index=True,width='stretch',key=key,on_select='rerun',selection_mode='single-row')
        rows=event.selection.rows
        if rows and rows[0]<len(subset): return subset.iloc[rows[0]]
    else: st.dataframe(subset,hide_index=True,width='stretch')
    return None

def filtered(ctx,key):
    ctx.require_results();r=ctx.result.copy()
    key=key+ctx.bid
    memory=st.session_state.setdefault('filter_memory',{})
    for suffix,default in [('q',''),('lots',[]),('states',[])]:
        if key+suffix not in st.session_state:st.session_state[key+suffix]=memory.get(key+suffix,default)
    def remember():
        for suffix in ['q','lots','states']:memory[key+suffix]=st.session_state.get(key+suffix)
    a,b,c=st.columns([2,2,2])
    query=a.text_input('Find component',key=key+'q',on_change=remember)
    lots=b.multiselect('Lot',sorted(r.lot_id.unique()),key=key+'lots',on_change=remember)
    states=c.multiselect('Disposition',['NORMAL','WATCH','HIGH RISK','CRITICAL'],key=key+'states',on_change=remember)
    if query:r=r[r.component_id.str.contains(query,case=False,regex=False)]
    if lots:r=r[r.lot_id.isin(lots)]
    if states:r=r[r.status.isin(states)]
    reviews=ctx.store.table('reviews');reviews=reviews[reviews.run_id==ctx.run['id']]
    r=r.merge(reviews[['component_id','state']].rename(columns={'state':'review_state'}),on='component_id',how='left')
    r['review_state']=r.review_state.fillna('Unreviewed')
    return r.sort_values('risk_score',ascending=False)

def select_component(ctx,key='component'):
    ctx.require_results(); r=ctx.result.sort_values('risk_score',ascending=False)
    ids=list(r.component_id.unique());focus=st.session_state.get('focus_component')
    selected=st.selectbox('Component ID',ids,index=ids.index(focus) if focus in ids else 0,key=key+'id')
    subset=r[r.component_id==selected]
    idx=st.selectbox('Measurement / session / condition',list(subset.index),format_func=lambda i:f'{r.loc[i,"parameter"]} · {r.loc[i,"session_id"]} · {r.loc[i,"temperature"]} °C / {r.loc[i,"voltage"]} V',key=key+'row')
    return r.loc[idx]

def metadata(ctx):
    return {'Batch':ctx.meta['name'] if ctx.meta else 'None','Batch ID':ctx.bid or 'None','Source':ctx.meta['source'] if ctx.meta else 'None','Dataset hash':ctx.meta['hash'] if ctx.meta else 'None','Run':ctx.run['id'] if ctx.run else 'None','Model':ctx.run['model_id'] if ctx.run else ctx.mid or 'None','Policy':ctx.run['policy_id'] if ctx.run else policy_id(ctx.policy)}
