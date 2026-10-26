"""Prediction, reproducible model laboratory, simulation and honest evaluation."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import roc_curve,precision_recall_curve
from ess.data.synthetic import SCENARIOS
from ess.features.engineering import features
from ess.prediction.training import predict,dataset_hash
from ess.prediction.evaluation import compare_screening
from ess.risk.engine import screen,component_summary
from services.quality import inspect
from ui.theme import chart,kpis,COLORS
from ui.common import action,table,exports,download,goto,model_at

CANDIDATES=['Linear','Ridge-1','Ridge-10','RandomForest','GradientBoosting-2','GradientBoosting-3']

def predictions(c):
    c.require_data(); models=c.store.table('models')
    if models.empty:st.info('No registered models. Train a model in Model Laboratory.');return
    mid=st.selectbox('Prediction model',list(models.id),index=list(models.id).index(c.mid) if c.mid in list(models.id) else 0)
    b=model_at(c.root,mid);st.write(f'**Target:** value_168h · **Input cutoff:** {b["manifest"]["cutoff"]}h · **Version:** {b["manifest"]["version"]}')
    st.caption('Running a prediction with this selector does not activate or replace the screening model.')
    if st.button('Predict active batch',type='primary'):
        output=action(c,'Prediction',lambda:predict(b,c.data))
        if output is not None:
            st.session_state.prediction=(c.bid,mid,c.data[['component_id','lot_id','parameter','unit']].join(output))
            c.store.event('prediction_completed',{'model_id':mid,'records':len(output)},c.bid)
    saved=st.session_state.get('prediction')
    if saved and saved[:2]==(c.bid,mid):
        out=saved[2];st.warning('Extrapolated points are not qualified predictions. See the support flag and notes; unsupported intervals are withheld.')
        table(out,'predictiontable');exports(c,out,'168h_predictions','predictionexport')
        par=st.selectbox('Prediction measurement',sorted(out.parameter.unique()));q=out[out.parameter==par];chart(px.histogram(q,x='predicted_168h',title=f'168h estimate ({q.unit.iloc[0]})'))
    st.subheader('Feature importance from validation');par=st.selectbox('Model parameter',list(b['units']))
    importance=b['importance'].query('parameter == @par');chart(px.bar(importance.sort_values('importance'),x='importance',y='feature',orientation='h',labels={'importance':f'Increase in MAE ({b["units"][par]["unit"]})'}))
    st.caption('Permutation importance is not causal attribution or an individual model explanation. Correlated features may share importance.')

def laboratory(c):
    c.require_data();_,health,_=inspect(c.data,True)
    for error in health['errors']:st.error(error)
    with st.form('train_form'):
        a,b=st.columns(2)
        with a:
            cutoff=st.selectbox('Input cutoff / supported feature set',[24,96])
            candidates=st.multiselect('Candidate models',CANDIDATES,default=CANDIDATES)
            seed=int(st.number_input('Random seed',min_value=0,max_value=2147483647,value=42))
        with b:
            trees=int(st.number_input('Random forest trees',20,300,80,20))
            stages=int(st.number_input('Gradient boosting stages',20,300,100,20))
            st.write('**Target:** 168h measurement, per parameter')
            st.caption('Lot-disjoint train / validation / calibration / test. Approximate fractions: 50 / 15 / 15 / 20%. Linear baseline always retained. Target and feature semantics are locked against future leakage.')
        submitted=st.form_submit_button('Train candidate models',type='primary',disabled=bool(health['errors']))
    st.caption('Supported features: '+', '.join(features(c.data,cutoff).columns))
    if submitted:
        progress=st.progress(0.,text='Validating training batch')
        mid=action(c,'Model training',lambda:c.work.train(c.bid,cutoff=cutoff,seed=seed,candidate_names=candidates,trees=trees,boosting_stages=stages,progress=lambda value,text:progress.progress(value,text=text)))
        if mid:st.session_state.trained_model=mid
    models=c.store.table('models')
    if models.empty:return
    mid=st.selectbox('Registered model',list(models.id),index=list(models.id).index(st.session_state.get('trained_model')) if st.session_state.get('trained_model') in list(models.id) else len(models)-1,key='registered_model')
    b=model_at(c.root,mid);m=b['manifest']
    kpis([('Model status','Registered','Not activated automatically','#36D6C5'),('Parameters',len(b['units']),'Independent estimators','#57A6FF'),('Features',len(m['features']),'As-of whitelist','#F1F5FB'),('Input cutoff',str(m['cutoff'])+'h','Target fixed at 168h','#F1F5FB'),('Training time',f'{m["duration_seconds"]:.1f}s' if 'duration_seconds' in m else 'Not recorded','Measured duration where available','#F1F5FB'),('Random seed',m['seed'],'Recorded in manifest','#F1F5FB')])
    st.dataframe(b['comparison'],hide_index=True);st.write('Selected models:',m['winners'])
    st.dataframe(pd.DataFrame({'split':list(m['split']),'lots':[', '.join(v) for v in m['split'].values()]}),hide_index=True)
    st.caption('Version '+m['version']+' · dataset '+m['dataset_hash'])
    confirm=st.checkbox('Confirm this model should become active for future screenings.')
    if st.button('Activate selected model',disabled=not confirm):
        if action(c,'Model activation',lambda:c.store.activate(mid,confirmed=True)) is None:
            # Activation returns None on success as well; verify actual stored selection.
            if c.store.get('active_model')==mid:st.rerun()

def simulator(c):
    names=SCENARIOS+['Elevated measurement variation','Missing measurements','Mixed-quality population']
    name=st.selectbox('Scenario',names)
    st.info('SYNTHETIC EXPERIMENT — generated mechanisms, not a production event.')
    fixed=name in SCENARIOS
    if fixed:st.caption('Preserved reference recipe: 120 components, one lot, leakage current. One selected component is modified except Normal Lot. Seed controls measurement perturbations.')
    with st.form('scenario_form'):
        seed=int(st.number_input('Simulation seed',0,100000,42))
        n=int(st.number_input('Generated components',100,100000,600,100,disabled=fixed))
        lots=int(st.number_input('Generated lots',1,100,12,disabled=fixed))
        noise=st.slider('Noise fraction',0.,.2,.08 if name=='Elevated measurement variation' else .015,.005,disabled=fixed)
        severity=st.slider('Drift severity',.2,2.,1.,.1,disabled=fixed)
        defect=st.slider('Defect fraction',0.,.5,.15,.01,disabled=fixed)
        submitted=st.form_submit_button('Run scenario',type='primary')
    if submitted:
        with st.spinner('Generating baseline and simulation; screening both populations…'):
            result=action(c,'Scenario execution',lambda:c.work.simulate(name,seed,n,lots,noise,severity,defect))
        if result:st.session_state.scenario_pair=result;st.rerun()
    pair=st.session_state.get('scenario_pair')
    if pair:
        rows=[]
        for label,bid in zip(['Baseline','Simulation'],pair):
            run=c.store.latest_run(bid);r=c.store.results(run['id']);s=component_summary(r)
            rows.append(dict(population=label,components=len(s),flagged=int(s.dynamic_flag.sum()),static_breaches=int(s.static_violation.sum()),predicted_crossings=int(r.predicted_crossing.sum())))
        comparison=pd.DataFrame(rows);st.dataframe(comparison,hide_index=True);chart(px.bar(comparison,x='population',y=['flagged','static_breaches'],barmode='group'))
        meta=c.store.table('batches').set_index('id').loc[pair[1],'metadata'];st.write('Recorded experiment configuration:',json.loads(meta))
        exports(c,comparison,'scenario_comparison','scenarioexport')
        st.button('Investigate simulated components',on_click=goto,args=('Component Explorer',))

def evaluation(c):
    if c.model is None:st.info('Train or activate a model to view evaluation.');return
    b=c.model;st.caption('Validation chooses the model. Test rows are held out by lot. Tuning policy while viewing test outcomes requires a new external test set.')
    st.subheader('Regression validation and test evidence');st.dataframe(b['comparison'],hide_index=True)
    par=st.selectbox('Evaluation parameter',list(b['units']));q=b['test_predictions'].query('parameter == @par')
    a,z=st.columns(2)
    with a:chart(px.scatter(q,x='actual',y='predicted',hover_data=['lot_id'],title=f'Held-out test: {par} ({b["units"][par]["unit"]})'))
    with z:chart(px.histogram(q,x='residual',title='Held-out residual distribution'))
    errors=q.assign(absolute_error=q.residual.abs());a,z=st.columns(2)
    with a:chart(px.bar(errors.groupby('lot_id').absolute_error.mean().reset_index(),x='lot_id',y='absolute_error',title='Test MAE by lot'))
    with z:chart(px.scatter(errors,x='actual',y='absolute_error',title='Error by measurement range'))
    c.require_data();matches=dataset_hash(c.data)==b['manifest']['dataset_hash']
    evaldata=c.data[c.data.lot_id.isin(b['manifest']['split']['test'])] if matches else c.data
    st.subheader('Screening policy comparison')
    if not matches:st.warning('Active data differs from the training dataset. The following classification metrics are descriptive, not untouched test performance. Regression charts above remain saved test results.')
    if 'defect_label' not in evaldata:
        st.info('Unlabeled dataset: precision, recall and confusion matrix are unavailable. Inspect anomaly distributions in Anomaly Analysis.');return
    if st.button('Evaluate screening policy',type='primary'):
        r=action(c,'Screening evaluation',lambda:screen(evaldata,b,c.policy,stage=b['manifest']['cutoff']))
        if r is not None:st.session_state.eval_result=(c.bid,c.mid,json.dumps(c.policy.__dict__,sort_keys=True),r)
    saved=st.session_state.get('eval_result')
    if saved and saved[:3]==(c.bid,c.mid,json.dumps(c.policy.__dict__,sort_keys=True)):
        r=saved[3];metrics=compare_screening(r);st.dataframe(metrics,hide_index=True)
        row=metrics.iloc[-1];chart(px.imshow([[row.TN,row.FP],[row.FN,row.TP]],x=['No review','Review'],y=['Normal truth','Defect truth'],text_auto=True,color_continuous_scale='Blues'))
        if r.defect_label.nunique()==2:
            fp,tp,_=roc_curve(r.defect_label,r.risk_score);precision,recall,_=precision_recall_curve(r.defect_label,r.risk_score)
            a,z=st.columns(2)
            with a:chart(px.line(x=fp,y=tp,labels={'x':'False positive rate','y':'True positive rate'},title='ROC · engineering score'))
            with z:chart(px.line(x=recall,y=precision,labels={'x':'Recall','y':'Precision'},title='Precision–recall'))
        exports(c,metrics,'screening_evaluation','evaluationexport')
