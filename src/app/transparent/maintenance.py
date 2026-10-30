"""Offline local runtime rotation and encrypted, expiring managed backups.

Never contact a provider, print key material, touch an unrelated runtime, or
restore live credentials. Private journals permit recovery across interruptions.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import secrets
import shutil
from app.private_files import open_private_database
import stat
import tempfile
import time
from contextlib import closing, contextmanager
from pathlib import Path

from cryptography.fernet import Fernet

from app.common import canonical
from app.transparent.runtime_lock import lease

MAX_BACKUP = 64 * 1024 * 1024
ROLE_FILES = frozenset({'ca.pem','control.pem','control.key','storage.key','human.token','machine.token',
                        'machine.id','forward.key','grant.json','operators.json','gateway.pem','gateway.key',
                        'gateway-client.pem','gateway-client.key','upstream.pem','upstream.key'})
DATABASES = ('control-data/control.sqlite3','control-data/control.sqlite3.auth',
             'upstream-data/attempts.sqlite3','jev-budget/typesafe-budget.sqlite3')
# SQL identifiers are part of complete, reviewed statements, never interpolated.
SEALED_QUERIES = (
    ('sessions', 'SELECT rowid,body FROM sessions WHERE body IS NOT NULL',
     'UPDATE sessions SET body=? WHERE rowid=?'),
    ('turns', 'SELECT rowid,body FROM turns WHERE body IS NOT NULL',
     'UPDATE turns SET body=? WHERE rowid=?'),
    ('calls', 'SELECT rowid,body FROM calls WHERE body IS NOT NULL',
     'UPDATE calls SET body=? WHERE rowid=?'),
    ('sources', 'SELECT rowid,body FROM sources WHERE body IS NOT NULL',
     'UPDATE sources SET body=? WHERE rowid=?'),
    ('transport', 'SELECT rowid,body FROM transport WHERE body IS NOT NULL',
     'UPDATE transport SET body=? WHERE rowid=?'),
    ('security_events', 'SELECT rowid,body FROM security_events WHERE body IS NOT NULL',
     'UPDATE security_events SET body=? WHERE rowid=?'),
)
ROTATION_FILES = ('control/storage.key','control/machine.token','host/machine.token',
                  'control/human.token','host/human.token','control/forward.key','upstream/forward.key')


def sync_directory(path):
    """Persist directory entries before a later database/key transition."""
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def checked(root, name):
    root = Path(root).absolute()
    relative = Path(name)
    if any(p.is_symlink() for p in (root,*root.parents)) or relative.is_absolute() or '..' in relative.parts:
        raise ValueError('UNSAFE_RUNTIME_PATH')
    result = root / relative
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('UNSAFE_RUNTIME_PATH')
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('UNSAFE_RUNTIME_PATH')
    return result


def write_private(path, data):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('UNSAFE_RUNTIME_PATH')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.private-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def offline(root):
    root = Path(root).absolute()
    if not root.is_dir() or root.is_symlink():
        raise ValueError('RUNTIME_REQUIRED')
    control = checked(root, DATABASES[0])
    upstream = checked(root, DATABASES[2])
    with lease(control), lease(upstream):
        yield root


def database(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('RUNTIME_DATABASE_REQUIRED')
    db = open_private_database(path, isolation_level=None, timeout=1)
    db.execute('PRAGMA secure_delete=ON')
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        db.close()
        raise ValueError('DATABASE_INTEGRITY_FAILED')
    return db


def recover(root):
    journal = checked(root, 'control-data/rotation.pending')
    if not journal.exists():
        return False
    if journal.stat().st_size > 262144:
        raise ValueError('ROTATION_JOURNAL_INVALID')
    value = json.loads(journal.read_bytes())
    with closing(database(checked(root, DATABASES[0]))) as db:
        present = db.execute("SELECT 1 FROM sqlite_master WHERE name='key_rotation'").fetchone()
        row = db.execute('SELECT generation FROM key_rotation WHERE id=1').fetchone() if present else None
    selected = 'new' if row and row[0] == value['generation'] else 'old'
    if (set(value) != {'generation','old','new'} or set(value['old']) != set(value['new'])
            or not set(ROTATION_FILES).issubset(value[selected]) or not all(allowed(name) for name in value[selected])):
        raise ValueError('ROTATION_JOURNAL_INVALID')
    for name, text in value[selected].items():
        write_private(checked(root, name), text.encode('ascii'))
    if selected == 'new':
        staging = checked(root,'pki')
        if staging.exists():
            permitted = ROLE_FILES | {'ca.key','service.token','effects-storage.key',
                                      'wrong-host.pem','wrong-host.key','expired.pem','expired.key'}
            rows = list(staging.iterdir())
            if any(p.is_symlink() or not p.is_file() or p.name not in permitted for p in rows):
                raise ValueError('UNEXPECTED_LEGACY_PKI_FILES')
            for path in rows:
                path.unlink()
            staging.rmdir()
            sync_directory(root)
    journal.unlink()
    sync_directory(journal.parent)
    return True


def new_tls():
    helper = Path(__file__).resolve().parents[3]/'tools/prepare_tls.py'
    if helper.is_symlink() or not helper.is_file():
        raise ValueError('PACKAGED_TLS_HELPER_REQUIRED')
    spec = importlib.util.spec_from_file_location('local_runtime_pki', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    roles = {'control':('ca.pem','control.pem','control.key'),
             'host':('ca.pem',),
             'gateway':('ca.pem','gateway.pem','gateway.key','gateway-client.pem','gateway-client.key'),
             'upstream':('ca.pem','upstream.pem','upstream.key')}
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary)/'pki'
        module.generate(target,[('upstream',['upstream'])])
        return {role+'/'+name:(target/name).read_text(encoding='ascii') for role,names in roles.items() for name in names}


def _rotate(root):
    recover(root)
    old = {name:checked(root,name).read_text(encoding='ascii').strip() for name in ROTATION_FILES}
    new = dict(old)
    for name, value in new_tls().items():
        old[name] = checked(root,name).read_text(encoding='ascii')
        new[name] = value
    new['control/storage.key'] = Fernet.generate_key().decode('ascii')
    for names in (('control/machine.token','host/machine.token'),('control/human.token','host/human.token'),
                  ('control/forward.key','upstream/forward.key')):
        token = secrets.token_urlsafe(48)
        for name in names:
            new[name] = token
    operators = checked(root, 'control/operators.json')
    if operators.exists():
        old['control/operators.json'] = operators.read_text(encoding='ascii')
        new['control/operators.json'] = '[]'
    before, after = Fernet(old['control/storage.key'].encode()), Fernet(new['control/storage.key'].encode())
    generation = secrets.token_hex(16)
    journal = checked(root, 'control-data/rotation.pending')
    write_private(journal, canonical({'generation':generation,'old':old,'new':new}).encode())
    try:
        db = database(checked(root, DATABASES[0]))
        try:
            db.execute('BEGIN EXCLUSIVE')
            for table, select_sql, update_sql in SEALED_QUERIES:
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    continue
                for rowid, body in db.execute(select_sql).fetchall():
                    db.execute(update_sql, (after.encrypt(before.decrypt(body)), rowid))
            for rowid, reason in db.execute('SELECT rowid,reason FROM calls WHERE reason IS NOT NULL').fetchall():
                value = json.loads(reason)
                if value.get('format') != 'sealed-decision-context-1':
                    raise ValueError('LEGACY_RUNTIME_MIGRATION_REQUIRED')
                value['body'] = after.encrypt(before.decrypt(value['body'].encode())).decode()
                db.execute('UPDATE calls SET reason=? WHERE rowid=?', (canonical(value),rowid))
            db.execute("UPDATE calls SET state='UNKNOWN' WHERE state IN ('ANALYZING','EXECUTING')")
            db.execute("UPDATE calls SET state='STALE' WHERE state IN ('PENDING','READY','CONFIRM','APPROVED')")
            db.execute('UPDATE approvals SET consumed=1')
            db.execute('UPDATE demo_confirmations SET resumed=1')
            db.execute('DELETE FROM connections')
            db.execute("DELETE FROM expiry WHERE kind='connection'")
            db.execute("UPDATE expiry SET deadline=0 WHERE kind='session'")
            db.execute('INSERT OR IGNORE INTO closed_sessions SELECT id FROM sessions')
            db.execute('CREATE TABLE IF NOT EXISTS key_rotation(id INTEGER PRIMARY KEY,generation TEXT)')
            db.execute('INSERT OR REPLACE INTO key_rotation VALUES(1,?)', (generation,))
            # Audit is part of the same transaction and is sealed with the NEW key.
            from types import SimpleNamespace

            from app.transparent.security_audit import record
            record(SimpleNamespace(seal=lambda x:after.encrypt(canonical(x).encode())), db,
                   'KEY_ROTATION','local-maintenance',generation,'COMPLETED')
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
    finally:
        # Transaction marker resolves both committed and rolled-back interruptions.
        recover(root)
    return {'state':'ROTATED','connections_revoked':True,'operators_require_reenrollment':True}


def rotate(root):
    with offline(root) as root:
        return _rotate(root)


def allowed(name):
    path = Path(name)
    return name in DATABASES or len(path.parts) == 2 and path.parts[0] in {'control','host','gateway','upstream'} and path.parts[1] in ROLE_FILES


def backup_key(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('UNSAFE_BACKUP_KEY')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > 128:
        raise ValueError('PRIVATE_BACKUP_KEY_REQUIRED')
    return Fernet(path.read_bytes().strip())


def offline_audit(root,kind,resource,result):
    from types import SimpleNamespace

    from app.transparent.security_audit import record
    box = Fernet(checked(root,'control/storage.key').read_bytes().strip())
    with closing(database(checked(root,DATABASES[0]))) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            record(SimpleNamespace(seal=lambda value:box.encrypt(canonical(value).encode())),db,
                   kind,'local-maintenance',resource,result)
            db.commit()
        except BaseException:
            db.rollback()
            raise


def make_backup(root, destination, key_file, ttl=86400):
    if type(ttl) is not int or not 60 <= ttl <= 604800:
        raise ValueError('BACKUP_RETENTION_INVALID')
    destination, key_file = Path(destination).absolute(), Path(key_file).absolute()
    if destination.suffix != '.whb':
        raise ValueError('MANAGED_BACKUP_EXTENSION_REQUIRED')
    if (destination.exists() or any(p.is_symlink() for p in (destination,*destination.parents))
            or destination.is_relative_to(Path(root).absolute()) or key_file.is_relative_to(Path(root).absolute())
            or key_file.is_relative_to(destination.parent)):
        raise ValueError('SEPARATE_PRIVATE_BACKUP_KEY_REQUIRED')
    box = backup_key(key_file)
    with offline(root) as root:
        recover(root)
        offline_audit(root,'BACKUP_CREATE',destination.name,'REQUESTED')
        files = {}
        for role in ('control','host','gateway','upstream'):
            for path in checked(root,role).iterdir():
                name = path.relative_to(root).as_posix()
                if allowed(name) and path.is_file():
                    files[name] = checked(root,name).read_bytes()
        for name in DATABASES:
            path = checked(root,name)
            if path.exists():
                with tempfile.TemporaryDirectory() as staging:
                    copy = Path(staging)/'snapshot.sqlite3'
                    source = database(path)
                    target = open_private_database(copy)
                    try:
                        source.backup(target)
                    finally:
                        source.close()
                        target.close()
                    files[name] = copy.read_bytes()
        if sum(map(len,files.values())) > MAX_BACKUP:
            raise ValueError('BACKUP_SIZE_LIMIT')
        now = time.time()
        value = {'format':'with-human-local-backup-1','created':now,'expires':now+ttl,
                 'files':{name:base64.b64encode(data).decode() for name,data in files.items()},
                 'hashes':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
        write_private(destination, box.encrypt(canonical(value).encode()))
        offline_audit(root,'BACKUP_CREATE',destination.name,'COMPLETED')
    return {'state':'BACKUP_CREATED','files':len(files),'expires':now+ttl}


def read_backup(path, key_file):
    if path.is_symlink() or key_file.is_symlink() or path.stat().st_size > MAX_BACKUP*2:
        raise ValueError('BACKUP_INVALID')
    value = json.loads(backup_key(key_file).decrypt(path.read_bytes()))
    if (set(value) != {'format','created','expires','files','hashes'} or value['format'] != 'with-human-local-backup-1'
            or type(value['created']) not in (int,float) or type(value['expires']) not in (int,float)
            or not 60 <= value['expires']-value['created'] <= 604800
            or not isinstance(value['files'],dict) or set(value['files']) != set(value['hashes'])
            or len(value['files']) > 80 or not set(ROTATION_FILES).issubset(value['files']) or DATABASES[0] not in value['files']):
        raise ValueError('BACKUP_INVALID')
    files = {}
    for name, encoded in value['files'].items():
        if not allowed(name):
            raise ValueError('BACKUP_INVALID')
        data = base64.b64decode(encoded, validate=True)
        if hashlib.sha256(data).hexdigest() != value['hashes'][name]:
            raise ValueError('BACKUP_INVALID')
        files[name] = data
    if sum(map(len,files.values())) > MAX_BACKUP:
        raise ValueError('BACKUP_SIZE_LIMIT')
    return value, files


def restore(backup, root, key_file):
    root = Path(root).absolute()
    if root.exists() or root.is_symlink() or root.parent.is_symlink():
        raise ValueError('NEW_RUNTIME_REQUIRED')
    value, files = read_backup(Path(backup),Path(key_file))
    if value['expires'] <= time.time():
        raise ValueError('BACKUP_EXPIRED')
    root.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    staging = Path(tempfile.mkdtemp(prefix='.restore-',dir=root.parent))
    try:
        for directory in ('control','host','gateway','upstream','control-data','upstream-data',
                          'jev-budget','workspace/docs','workspace/reports'):
            checked(staging,directory).mkdir(parents=True,exist_ok=True,mode=0o700)
        for name, data in files.items():
            write_private(checked(staging,name),data)
        with offline(staging):
            _rotate(staging)
            write_private(checked(staging,'control-data/provider-reapproval.required'),b'NEW_EXPLICIT_BUDGET_REQUIRED\n')
        for directory in sorted((p for p in staging.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            sync_directory(directory)
        sync_directory(staging)
        if root.exists():
            raise ValueError('NEW_RUNTIME_REQUIRED')
        os.rename(staging,root)
        sync_directory(root.parent)
        offline_audit(root,'BACKUP_RESTORE',root.name,'COMPLETED')
    finally:
        if staging.exists():
            if staging.is_symlink() or not staging.resolve().is_relative_to(root.parent.resolve()):
                raise ValueError('UNSAFE_RUNTIME_PATH')
            shutil.rmtree(staging)
    return {'state':'RESTORED_NEW_CREDENTIALS','files':len(files)}


def approve_restored_provider(root, policy_file, approved=False):
    """A restore never refunds provider use absent from the old snapshot.

    Only an explicit new policy/budget starts a new ledger. The old snapshot's
    ledger is preserved as evidence, and startup is bound to the approved policy.
    """
    from app.transparent.jev_config import load_settings
    if not approved:
        raise ValueError('EXPLICIT_NEW_PROVIDER_BUDGET_REQUIRED')
    policy_file = Path(policy_file)
    settings = load_settings(policy_file)
    if not settings.authorized():
        raise ValueError('AUTHORIZED_PROVIDER_POLICY_REQUIRED')
    with offline(root) as root:
        marker = checked(root,'control-data/provider-reapproval.required')
        if not marker.is_file():
            raise ValueError('RESTORED_PROVIDER_GATE_REQUIRED')
        ledger = checked(root,DATABASES[3])
        previous = checked(root,'control-data/pre-restore-budget.sqlite3')
        evidence = ledger if ledger.exists() else previous
        if evidence.exists():
            with closing(database(evidence)) as db:
                table = db.execute("SELECT 1 FROM sqlite_master WHERE name='jev_policy'").fetchone()
                row = db.execute('SELECT binding FROM jev_policy WHERE singleton=1').fetchone() if table else None
            if row and json.loads(row[0])['policy_id'] == settings.policy_id:
                raise ValueError('NEW_PROVIDER_POLICY_ID_REQUIRED')
        if ledger.exists():
            if previous.exists():
                raise ValueError('PREVIOUS_BUDGET_EVIDENCE_PRESERVED')
            os.rename(ledger,previous)
            sync_directory(ledger.parent)
            sync_directory(previous.parent)
        binding = hashlib.sha256(policy_file.read_bytes()).hexdigest()
        write_private(checked(root,'control-data/provider.authorization'),binding.encode('ascii'))
        offline_audit(root,'PROVIDER_REAUTHORIZE',binding,'COMPLETED')
        marker.unlink()
        sync_directory(marker.parent)
    return {'state':'NEW_PROVIDER_BUDGET_APPROVED','policy_id':settings.policy_id}


def sweep_backups(directory, key_file):
    directory, key_file = Path(directory).absolute(), Path(key_file).absolute()
    if directory.is_symlink() or key_file.is_relative_to(directory):
        raise ValueError('SEPARATE_PRIVATE_BACKUP_KEY_REQUIRED')
    deleted = 0
    for path in directory.glob('*.whb'):
        value, _ = read_backup(path,key_file)
        if value['expires'] <= time.time():
            path.unlink()
            sync_directory(directory)
            deleted += 1
    return {'state':'BACKUPS_SWEPT','deleted':deleted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('rotate','recover','backup','restore','sweep','create-backup-key','approve-restored-provider'))
    parser.add_argument('--runtime',type=Path)
    parser.add_argument('--backup',type=Path)
    parser.add_argument('--key-file',type=Path)
    parser.add_argument('--ttl',type=int,default=86400)
    parser.add_argument('--policy-file',type=Path)
    parser.add_argument('--approve-new-provider-budget',action='store_true')
    args = parser.parse_args()
    try:
        if args.mode == 'rotate':
            result = rotate(args.runtime)
        elif args.mode == 'recover':
            with offline(args.runtime) as root:
                result = {'state':'RECOVERY_CHECKED','recovered':recover(root)}
        elif args.mode == 'backup':
            result = make_backup(args.runtime,args.backup,args.key_file,args.ttl)
        elif args.mode == 'restore':
            result = restore(args.backup,args.runtime,args.key_file)
        elif args.mode == 'sweep':
            result = sweep_backups(args.backup,args.key_file)
        elif args.mode == 'approve-restored-provider':
            result = approve_restored_provider(args.runtime,args.policy_file,args.approve_new_provider_budget)
        else:
            if args.key_file.exists():
                raise ValueError('EXISTING_KEY_PRESERVED')
            write_private(args.key_file,Fernet.generate_key())
            result = {'state':'BACKUP_KEY_CREATED'}
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({'state':'FAILED','error_type':type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
