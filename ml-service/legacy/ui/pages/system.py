"""Local settings, non-destructive demo reset, backup and real diagnostics."""
import json,platform
import pandas as pd
import streamlit as st
from ui.common import action,download,table

def settings(c):
    st.subheader('Local workspace')
    label=st.text_input('Workspace display name',value=c.store.get('workspace_name','Engineering workspace'))
    if st.button('Save workspace settings'):
        if label.strip() and len(label)<=100:
            c.store.set('workspace_name',label);c.store.event('settings_changed',{'workspace_name':label});st.success('Workspace settings saved.')
        else:st.error('Use a name between 1 and 100 characters.')
    st.caption('The application does not connect to cloud telemetry or send datasets to external services.')
    if st.button('Create workspace backup'):
        content=action(c,'Workspace backup',c.store.backup)
        if content:st.session_state.backup_bytes=content;c.store.event('backup_generated',{'bytes':len(content)})
    if 'backup_bytes' in st.session_state:download(c,'Download workspace backup',st.session_state.backup_bytes,'ess_workspace_backup.zip','application/zip')
    st.subheader('Reset demonstration context')
    st.write('Creates a fresh synthetic batch and selects it. Existing imports, models, results and audit records are retained.')
    confirm=st.checkbox('Confirm creation of a fresh demo batch.')
    if st.button('Reset demo workspace',disabled=not confirm):
        bid=action(c,'Demo reset',lambda:c.work.reset_demo(True))
        if bid:st.rerun()

def diagnostics(c):
    diagnostic=action(c,'Environment inspection',c.work.diagnostics)
    if diagnostic:
        a,b,z=st.columns(3);a.metric('Python',diagnostic['python']);b.metric('Operating system',diagnostic['os']);z.metric('Application',diagnostic['app'])
        st.write('Workspace writable:',diagnostic['writable']);st.caption('Data directory: '+str(c.store.root))
        st.dataframe(pd.DataFrame(diagnostic['dependencies']),hide_index=True)
        st.write('Registered models:',len(c.store.table('models')));st.write('Schema version:',diagnostic['schema_version'])
        st.json(c.policy.__dict__,expanded=False)
    if st.button('Run minimal backend smoke test'):
        result=action(c,'Backend smoke test',c.work.smoke)
        if result:st.write(result)
    events=c.store.table('events');st.subheader('Last successful operation')
    st.dataframe(events[events.outcome=='success'].tail(1)[['timestamp','action','batch_id']],hide_index=True)
    st.subheader('Recent recorded errors');table(events[events.outcome=='error'].tail(25),'errors')
    st.caption('No environment variables, tokens or passwords are displayed. Model uploads and arbitrary shell commands are not supported.')
