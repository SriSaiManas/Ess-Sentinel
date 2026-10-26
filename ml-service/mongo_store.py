"""MongoDB catalog adapter; preserves original artifact and algorithm contracts."""
import os,json,zipfile,hashlib
from io import BytesIO
from datetime import datetime,timezone
from bson import ObjectId
from pymongo import MongoClient
import pandas as pd
from services.store import Store as LegacyStore,atomic,policy_id,now
from ess.config import Policy
from ess.prediction.training import save_bundle,dataset_hash

class MongoStore(LegacyStore):
 def __init__(self,root):
  from pathlib import Path
  self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
  self.client=MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=5000)
  self.db=self.client[os.environ.get('MONGO_DB','ess_sentinel')]
 def table(self,name):
  cols={'batches':['id','name','source','created','hash','rows','components','health','metadata'],'models':['id','created','manifest'],'policies':['id','created','config'],'runs':['id','batch_id','model_id','policy_id','stage','created','summary'],'events':['id','timestamp','action','batch_id','outcome','details'],'reviews':['run_id','component_id','state','note','updated']}
  if name not in cols: raise ValueError('Unknown catalog')
  rows=[]
  for doc in self.db[name].find():
   r={('id' if k=='_id' else k):str(v) if isinstance(v,ObjectId) else json.dumps(v) if isinstance(v,dict) else v for k,v in doc.items()};rows.append(r)
  return pd.DataFrame(rows,columns=cols[name])
 def event(self,action,details=None,batch_id='',outcome='success'):
  self.db.events.insert_one(dict(timestamp=now(),action=action,batch_id=ObjectId(batch_id) if batch_id else None,outcome=outcome,details=details or {}))
 def set(self,key,value): self.db.settings.update_one({'key':key},{'$set':{'value':value}},upsert=True)
 def get(self,key,default=None):
  r=self.db.settings.find_one({'key':key});return r['value'] if r else default
 def add_batch(self,data,name,source,health,raw=None,metadata=None):
  oid=ObjectId();bid=str(oid);payload=data.to_csv(index=False).encode();atomic(self.path('batches',bid,'normalized.csv'),payload);atomic(self.path('batches',bid,'original.bin'),raw or payload)
  self.db.batches.insert_one(dict(_id=oid,name=name,source=source,created=now(),hash=dataset_hash(data),rows=len(data),components=int(data.component_id.nunique()),health=health,metadata={**(metadata or {}),'original_sha256':hashlib.sha256(raw or payload).hexdigest()}));self.event('dataset_imported',{'name':name,'source':source},bid);return bid
 def register_model(self,bundle):
  oid=ObjectId();mid=str(oid);save_bundle(bundle,self.path('models',mid,'model.joblib').parent)
  self.db.models.insert_one(dict(_id=oid,created=now(),manifest=bundle['manifest']));self.event('model_registered',{'model_id':mid});return mid
 def save_policy(self,policy,confirmed=False):
  if not confirmed: raise ValueError('Confirmation required')
  policy.validate();pid=self._policy(policy);self.set('active_policy',policy.__dict__);self.event('policy_changed',{'policy_id':pid});return pid
 def _policy(self,p):
  h=policy_id(p);self.db.policies.update_one({'hash':h},{'$setOnInsert':{'created':now(),'config':p.__dict__}},upsert=True);return str(self.db.policies.find_one({'hash':h})['_id'])
 def save_run(self,bid,mid,policy,stage,result):
  from ess.risk.engine import component_summary
  oid=ObjectId();rid=str(oid);atomic(self.path('runs',rid,'results.csv'),result.to_csv(index=False).encode());summary=component_summary(result).status.value_counts().to_dict()
  self.db.runs.insert_one(dict(_id=oid,batch_id=ObjectId(bid),model_id=ObjectId(mid) if mid else None,policy_id=ObjectId(self._policy(policy)),stage=stage,created=now(),summary=summary));self.event('screening_completed',{'run_id':rid,'summary':summary},bid);return rid
 def latest_run(self,bid):
  r=self.db.runs.find_one({'batch_id':ObjectId(bid)},sort=[('created',-1)])
  return {('id' if k=='_id' else k):str(v) if isinstance(v,ObjectId) else v for k,v in r.items()} if r else None
 def review(self,rid,component_id,state,note):
  if state not in ['Unreviewed','In review','Reviewed'] or len(note)>2000: raise ValueError('Invalid review')
  if component_id not in set(self.results(rid).component_id): raise ValueError('Component not in run')
  self.db.reviews.update_one({'run_id':ObjectId(rid),'component_id':component_id},{'$set':dict(state=state,note=note,updated=now())},upsert=True);self.event('review_updated',dict(run_id=rid,component_id=component_id,state=state,note=note))
 def backup(self):
  from bson.json_util import dumps
  buf=BytesIO()
  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
   for name in ['batches','models','policies','runs','events','reviews','settings','reports','scenarios']:z.writestr('catalog/'+name+'.json',dumps(list(self.db[name].find())))
   for category in ['batches','models','runs','reports']:
    for p in (self.root/category).rglob('*'):
     if p.is_file() and p.name!='backup.zip':z.write(p,p.relative_to(self.root))
  return buf.getvalue()
