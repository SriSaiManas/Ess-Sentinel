"""Import a trusted ESS 2.0 workspace into an EMPTY MongoDB database.
Usage: python scripts/migrate_sqlite.py /absolute/old/outputs/workspace
Environment: MONGO_URI, MONGO_DB, ARTIFACT_DIR. Never imports untrusted model files.
"""
import os,sys,json,sqlite3,shutil
from pathlib import Path
from bson import ObjectId
from pymongo import MongoClient
source=Path(sys.argv[1]).resolve();target=Path(os.environ['ARTIFACT_DIR']).resolve()
if source==target:raise SystemExit('Source and target must differ')
db=MongoClient(os.environ['MONGO_URI'])[os.environ.get('MONGO_DB','ess_sentinel')]
collections=['batches','models','policies','runs','events','reviews','settings']
if any(db[c].count_documents({}) for c in collections):raise SystemExit('Migration requires an empty target database')
if target.exists() and any(target.iterdir()):raise SystemExit('Artifact target must be empty')
con=sqlite3.connect('file:'+str(source/'catalog.sqlite')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
rows={t:[dict(r) for r in con.execute('SELECT * FROM '+t)] for t in collections};con.close()
maps={t:{str(r['id']):ObjectId() for r in rows[t]} for t in ['batches','models','policies','runs','events']}
def ref(t,v):return maps[t].get(str(v)) if v else None
# Validate all relationships and artifacts before writing.
for r in rows['runs']:
 for field,t in [('batch_id','batches'),('model_id','models'),('policy_id','policies')]:
  if r[field] and ref(t,r[field]) is None:raise SystemExit('Unresolved '+field)
for category in ['batches','models','runs']:
 for old,new in maps[category].items():
  if not (source/category/old).is_dir():raise SystemExit('Missing artifact directory '+category+'/'+old)
# Offline migration: keep source backup until verification; an interrupted target must be discarded explicitly.
for category in ['batches','models','runs']:
 for old,new in maps[category].items():shutil.copytree(source/category/old,target/category/str(new))
for category in collections:
 docs=[]
 for r in rows[category]:
  if category in maps:r['_id']=maps[category][str(r.pop('id'))]
  else:r['_id']=ObjectId()
  for field in ['metadata','manifest','config','summary','details']:
   if field in r:r[field]=json.loads(r[field])
  for field,t in [('batch_id','batches'),('model_id','models'),('policy_id','policies'),('run_id','runs')]:
   if field in r:r[field]=ref(t,r[field])
  if category=='policies':
   import hashlib
   r['hash']=hashlib.sha256(json.dumps(r['config'],sort_keys=True).encode()).hexdigest()
  if category=='settings':
   r['value']=json.loads(r['value'])
   if r['key'] in ['active_batch','active_model']:r['value']=str(ref('batches' if r['key']=='active_batch' else 'models',r['value'])) if r['value'] else None
  docs.append(r)
 if docs:db[category].insert_many(docs)
(target/'migration-map.json').write_text(json.dumps({t:{k:str(v) for k,v in m.items()} for t,m in maps.items()},indent=2))
print('Imported counts:',{c:len(rows[c]) for c in collections})
print('Source retained. Verify all screens before retiring the original workspace.')
