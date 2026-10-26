"""Local append-only application audit, using SQLite transactions."""
from datetime import datetime, timezone
from pathlib import Path
import json,sqlite3
from contextlib import closing
import pandas as pd

class Audit:
    def __init__(self,path='data/audit.sqlite'):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT, details TEXT)')
    def record(self,action,details):
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('INSERT INTO events(timestamp,action,details) VALUES (?,?,?)',
                (datetime.now(timezone.utc).isoformat(),action,json.dumps(details,default=str)))
    def read(self):
        with closing(sqlite3.connect(self.path)) as con, con: return pd.read_sql_query('SELECT * FROM events ORDER BY id DESC',con)
