"""False-negative-sensitive metrics; undefined rates remain unavailable."""
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

def classification(y, flags, score=None):
    y=np.asarray(y,dtype=int); flags=np.asarray(flags,dtype=int)
    tn,fp,fn,tp=confusion_matrix(y,flags,labels=[0,1]).ravel()
    ratio=lambda a,b:float(a/b) if b else None
    result=dict(TN=int(tn),FP=int(fp),FN=int(fn),TP=int(tp),
        Recall=ratio(tp,tp+fn),Precision=ratio(tp,tp+fp),F1=float(f1_score(y,flags,zero_division=0)),
        Specificity=ratio(tn,tn+fp),FNR=ratio(fn,fn+tp),FPR=ratio(fp,fp+tn),ROC_AUC=None,PR_AUC=None)
    if len(np.unique(y))==2 and score is not None:
        result.update(ROC_AUC=float(roc_auc_score(y,score)),PR_AUC=float(average_precision_score(y,score)))
    return result

def compare_screening(r):
    if 'defect_label' not in r: return pd.DataFrame()
    methods={'Static only':(r.static_violation,r.static_violation.astype(float)),
        'Robust statistics':(r.population_anomaly|r.temporal_anomaly,
            np.maximum(r.population_z.abs(),r.temporal_z.abs()).fillna(0)),
        'Isolation Forest':(r.ml_anomaly,r.if_percentile.fillna(0)),
        'Hybrid review policy':(r.dynamic_flag,r.risk_score)}
    return pd.DataFrame([dict(method=name,**classification(r.defect_label,flag,score)) for name,(flag,score) in methods.items()])
