"""Local SQLite catalog plus atomic immutable data/model/run artifacts."""
from contextlib import contextmanager,closing
from datetime import datetime,timezone
from pathlib import Path
from io import BytesIO
import hashlib,json,os,re,sqlite3,uuid,zipfile
import pandas as pd
from ess.config import Policy
from ess.prediction.training import dataset_hash,save_bundle,load_bundle
from ess.data.validation import ingest

SCHEMA_VERSION=1

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return prefix+'-'+uuid.uuid4().hex[:16]
def policy_id(p): return hashlib.sha256(json.dumps(p.__dict__,sort_keys=True).encode()).hexdigest()
def atomic(path: Path, content: bytes):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('wb') as f: f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally: tmp.unlink(missing_ok=True)

class Store:
    def __init__(self,root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True); self.db=self.root/'catalog.sqlite'
        with self.connect() as c:
            ver=c.execute('PRAGMA user_version').fetchone()[0]
            if ver not in [0,SCHEMA_VERSION]: raise ValueError('Unsupported catalog version; restore a compatible workspace.')
            c.executescript('''
            CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY,name TEXT,source TEXT,created TEXT,hash TEXT,rows INTEGER,components INTEGER,health INTEGER,metadata TEXT);
            CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY,created TEXT,manifest TEXT);
            CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY,created TEXT,config TEXT);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,batch_id TEXT,model_id TEXT,policy_id TEXT,stage INTEGER,created TEXT,summary TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,action TEXT,batch_id TEXT,outcome TEXT,details TEXT);
            CREATE TABLE IF NOT EXISTS reviews(run_id TEXT,component_id TEXT,state TEXT,note TEXT,updated TEXT,PRIMARY KEY(run_id,component_id));
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            '''); c.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
    @contextmanager
    def connect(self):
        con=sqlite3.connect(self.db,timeout=30); con.row_factory=sqlite3.Row
        try:
            with con: yield con
        finally: con.close()
    def path(self,category,identifier,filename):
        if category not in ['batches','models','runs','reports'] or not re.fullmatch(r'[A-Za-z0-9_-]+',identifier) or Path(filename).name!=filename:
            raise ValueError('Invalid artifact identifier.')
        return self.root/category/identifier/filename
    def event(self,action,details=None,batch_id='',outcome='success'):
        with self.connect() as c: c.execute('INSERT INTO events(timestamp,action,batch_id,outcome,details) VALUES(?,?,?,?,?)',(now(),action,batch_id,outcome,json.dumps(details or {},default=str)))
    def table(self,name):
        if name not in ['batches','models','policies','runs','events','reviews']: raise ValueError('Unknown catalog.')
        with self.connect() as c: return pd.read_sql_query('SELECT * FROM '+name,c)
    def set(self,key,value):
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(value)))
    def get(self,key,default=None):
        with self.connect() as c: row=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def add_batch(self,data,name,source,health,raw=None,metadata=None):
        bid=uid('batch'); meta=metadata or {}; payload=data.to_csv(index=False).encode()
        atomic(self.path('batches',bid,'normalized.csv'),payload)
        atomic(self.path('batches',bid,'original.bin'),raw if raw is not None else payload)
        meta['original_sha256']=hashlib.sha256(raw if raw is not None else payload).hexdigest()
        with self.connect() as c: c.execute('INSERT INTO batches VALUES(?,?,?,?,?,?,?,?,?)',(bid,name,source,now(),dataset_hash(data),len(data),data.component_id.nunique(),health,json.dumps(meta,default=str)))
        self.event('dataset_imported',dict(name=name,rows=len(data),source=source,**meta),bid)
        return bid
    def data(self,bid):
        return ingest(self.path('batches',bid,'normalized.csv').read_bytes(),'normalized.csv')
    def register_model(self,bundle):
        mid=uid('model'); location=self.path('models',mid,'model.joblib').parent
        # A model is invisible to the catalog until every artifact was successfully written.
        save_bundle(bundle,location)
        with self.connect() as c: c.execute('INSERT INTO models VALUES(?,?,?)',(mid,now(),json.dumps(bundle['manifest'])))
        self.event('model_registered',dict(model_id=mid,manifest=bundle['manifest']))
        return mid
    def model(self,mid): return None if not mid else load_bundle(self.path('models',mid,'model.joblib').parent)
    def activate(self,mid,confirmed=False):
        if not confirmed: raise ValueError('Confirm model activation.')
        self.model(mid); self.set('active_model',mid); self.event('model_activated',dict(model_id=mid))
    def policy(self):
        return Policy(**self.get('active_policy',Policy().__dict__)).validate()
    def save_policy(self,policy,confirmed=False):
        if not confirmed: raise ValueError('Confirm the policy change.')
        policy.validate(); pid=policy_id(policy)
        with self.connect() as c: c.execute('INSERT OR IGNORE INTO policies VALUES(?,?,?)',(pid,now(),json.dumps(policy.__dict__)))
        self.set('active_policy',policy.__dict__); self.event('policy_changed',dict(policy_id=pid,config=policy.__dict__))
        return pid
    def save_run(self,bid,mid,policy,stage,result):
        from ess.risk.engine import component_summary
        rid=uid('run'); atomic(self.path('runs',rid,'results.csv'),result.to_csv(index=False).encode())
        summary=component_summary(result).status.value_counts().to_dict(); pid=policy_id(policy)
        with self.connect() as c:
            c.execute('INSERT OR IGNORE INTO policies VALUES(?,?,?)',(pid,now(),json.dumps(policy.__dict__)))
            c.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?)',(rid,bid,mid or '',pid,stage,now(),json.dumps(summary)))
        self.event('screening_completed',dict(run_id=rid,model_id=mid,policy_id=pid,stage=stage,summary=summary),bid)
        return rid
    def latest_run(self,bid):
        with self.connect() as c: r=c.execute('SELECT * FROM runs WHERE batch_id=? ORDER BY created DESC LIMIT 1',(bid,)).fetchone()
        return dict(r) if r else None
    def results(self,rid):
        # IDs remain strings, and empty explanation notes remain empty strings.
        d=pd.read_csv(self.path('runs',rid,'results.csv'),dtype={'component_id':'string','lot_id':'string'},float_precision='round_trip')
        for c in ['prediction_note','explanation']: d[c]=d[c].fillna('')
        return d
    def review(self,rid,component_id,state,note):
        if state not in ['Unreviewed','In review','Reviewed']: raise ValueError('Invalid review state.')
        if len(note)>2000: raise ValueError('Review notes are limited to 2,000 characters.')
        if component_id not in set(self.results(rid).component_id): raise ValueError('Component is not in this run.')
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO reviews VALUES(?,?,?,?,?)',(rid,component_id,state,note,now()))
        self.event('review_updated',dict(run_id=rid,component_id=component_id,state=state,note=note))
    def backup(self):
        buf=BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            # SQLite backup provides a consistent catalog snapshot.
            temporary=self.root/('backup-'+uuid.uuid4().hex+'.sqlite')
            try:
                with self.connect() as source, closing(sqlite3.connect(temporary)) as dest:
                    source.backup(dest)
                z.write(temporary,'catalog.sqlite')
                for category in ['batches','models','runs','reports']:
                    for path in (self.root/category).rglob('*'):
                        if path.is_file(): z.write(path,path.relative_to(self.root))
            finally: temporary.unlink(missing_ok=True)
        return buf.getvalue()
