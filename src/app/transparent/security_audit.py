"""Local security journal. Metadata only; bodies are authenticated/encrypted.

Runs in the caller's engine transaction for administrative mutations. This is
not an external SIEM or protection against an OS administrator rolling back a DB.
"""
import re
import time

from app.common import digest

CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
KINDS = frozenset({'AUTH_FAILURE','ACCESS_DENIED','APPROVAL','SESSION_PURGE','SESSION_CLOSE',
                   'RETENTION_DELETE','KEY_ROTATION','BACKUP_CREATE','BACKUP_RESTORE','ALERT_ACK','PROVIDER_REAUTHORIZE'})


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS security_events(id INTEGER PRIMARY KEY,at REAL,kind TEXT,result TEXT,body BLOB);
        CREATE TABLE IF NOT EXISTS security_alerts(id INTEGER PRIMARY KEY,at REAL,code TEXT,event INTEGER,acknowledged INTEGER DEFAULT 0);
    """)


def record(engine, db, kind, actor, resource, result):
    if kind not in KINDS or not CODE.fullmatch(result):
        raise ValueError('SECURITY_EVENT_INVALID')
    now = time.time()
    value = {'at':now,'kind':kind,'result':result,'actor_hash':digest(str(actor)),
             'resource_hash':digest(str(resource))}
    event = db.execute('INSERT INTO security_events(at,kind,result,body) VALUES(?,?,?,?)',
                       (now,kind,result,engine.seal(value))).lastrowid
    warning = None
    if kind in ('AUTH_FAILURE','ACCESS_DENIED'):
        threshold = 10 if kind == 'AUTH_FAILURE' else 3
        if db.execute('SELECT count(*) FROM security_events WHERE kind=? AND at>?', (kind,now-60)).fetchone()[0] >= threshold:
            warning = kind + '_BURST'
    elif kind == 'KEY_ROTATION':
        warning = 'CREDENTIALS_ROTATED'
    if warning and not db.execute('SELECT 1 FROM security_alerts WHERE code=? AND at>?', (warning,now-60)).fetchone():
        db.execute('INSERT INTO security_alerts(at,code,event) VALUES(?,?,?)', (now,warning,event))
    sweep(db)
    return event


def sweep(db):
    # No user text, bearer, destination, headers or reversible subject is stored.
    db.execute('DELETE FROM security_events WHERE at<? OR id NOT IN (SELECT id FROM security_events ORDER BY id DESC LIMIT 4096)', (time.time()-604800,))
    db.execute('DELETE FROM security_alerts WHERE at<? OR id NOT IN (SELECT id FROM security_alerts ORDER BY id DESC LIMIT 512)', (time.time()-604800,))


def read(engine, db):
    sweep(db)
    events = []
    for row in db.execute('SELECT * FROM security_events ORDER BY id DESC LIMIT 100'):
        event = engine.open(row['body'])
        if event.get('at') != row['at'] or event.get('kind') != row['kind'] or event.get('result') != row['result']:
            raise ValueError('SECURITY_EVENT_INVALID')
        events.append({'id':row['id'],**event})
    return {'scope':'LOCAL_RUNTIME_LATEST_100','events':events,
            'alerts':[dict(row) for row in db.execute('SELECT * FROM security_alerts ORDER BY id DESC LIMIT 100')]}
