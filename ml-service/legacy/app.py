"""ESS Sentinel 2.0: local-first engineering intelligence shell."""
from pathlib import Path
from html import escape
import streamlit as st
from services.workspace import Workspace,APP_VERSION
from ui.navigation import ROUTES
from ui.common import Context,goto
from ui.theme import apply,title

st.set_page_config(page_title='ESS Sentinel 2.0',page_icon=':material/memory:',layout='wide',initial_sidebar_state='expanded')
apply()
work=Workspace()
try:work.bootstrap()
except Exception as exc:
    ref=work.error('Workspace initialization',exc);st.error(f'Workspace initialization failed. Reference {ref}. {str(exc) if isinstance(exc,ValueError) else "Check the local installation and workspace permissions."}');st.stop()
s=work.store
if 'page' not in st.session_state:st.session_state.page='Overview'
with st.sidebar:
    st.image(str(Path(__file__).parent/'assets/logo.svg'),width=245)
    for group,routes in ROUTES.items():
        st.html(f'<div class="ess-nav-label">{group}</div>')
        for name,(_,icon,_,_) in routes.items():
            st.button(name,icon=f':material/{icon}:',width='stretch',type='primary' if st.session_state.page==name else 'tertiary',on_click=goto,args=(name,),key='nav_'+name)
    st.html(f'<div class="ess-status">VERSION {APP_VERSION}<br>LOCAL ENVIRONMENT<br>Model: {"available" if s.get("active_model") else "not selected"}<br>No telemetry connection</div>')
batches=s.table('batches');ids=['']+list(batches.id);saved=s.get('active_batch','')
st.session_state.batch_context=saved if saved in ids else ''
def batch_changed():s.set('active_batch',st.session_state.batch_context)
head=st.columns([3,1])
with head[0]:st.selectbox('Active batch',ids,format_func=lambda x:'No active batch' if not x else batches.set_index('id').loc[x,'name'],key='batch_context',on_change=batch_changed)
with head[1]:st.caption(s.get('workspace_name','Engineering workspace'));st.caption('LOCAL / DEMO' if st.session_state.batch_context and batches.set_index('id').loc[st.session_state.batch_context,'source']=='SYNTHETIC' else 'LOCAL / STORED DATA')
try:context=Context(work,st.session_state.batch_context or None)
except ValueError as exc:
    st.error(str(exc));st.info('Saved artifact could not be loaded. Use a compatible model or restore a workspace backup.');st.stop()
page=st.session_state.page
for group,routes in ROUTES.items():
    if page in routes:
        render,icon,heading,sub=routes[page];title(heading,sub,group);break
if context.meta:
    meta=context.meta
    st.html(f'<div class="ess-batch"><b>{escape(meta["name"])}</b> &nbsp; <span class="ess-pill">{escape(meta["source"])}</span><br>{meta["components"]:,} components · {meta["rows"]:,} measurement records · {context.data.lot_id.nunique()} lots<br><span style="color:#96a6bc">Imported {escape(meta["created"])} · Last screening {escape(context.run["created"] if context.run else "not executed")}</span></div>')
    if meta['source']=='SYNTHETIC':st.caption('SYNTHETIC DATA · illustrative thresholds · not real-world qualification evidence')
try:render(context)
except Exception as exc:
    # Streamlit rerun/stop inherit BaseException and are intentionally not caught.
    ref=work.error(page,exc,context.bid or '')
    st.error(f'{page} could not complete. {str(exc) if isinstance(exc,ValueError) else "See System Diagnostics."} Reference {ref}.')
st.caption('Decision support only. Final component disposition requires qualified engineering review.')
