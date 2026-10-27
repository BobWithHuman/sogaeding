"""Private synthetic runtimes: no real keys, user DBs or provider requests."""
import sqlite3
import time

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.transparent import maintenance
from app.transparent.engine import Engine
from app.transparent.runtime_lock import lease


@pytest.fixture
def runtime(tmp_path):
    from team_runtime import prepare
    prepare(tmp_path,'synthetic')
    root = tmp_path/'artifacts/team-dev/synthetic'
    key = (root/'control/storage.key').read_bytes()
    grant = {'workspace':'/files','tools':{'mcp':['read_file','write_file'],'native':[]}}
    engine = Engine(root/'control-data/control.sqlite3',key,grant)
    engine.turn('m','s','t','PRIVATE_LOCAL_CANARY','/files')
    engine.register('m','s','t','c','read_file',{'path':'docs/release.md'},'mcp')
    engine.connect('m','old-live-connection')
    return root,engine


def reopened(root, original):
    return Engine(original.path,(root/'control/storage.key').read_bytes(),original.grant)


def test_rotation_preserves_history_but_revokes_keys_connections_and_sessions(runtime):
    root, engine = runtime
    old_key = (root/'control/storage.key').read_bytes()
    old_human = (root/'control/human.token').read_bytes()
    old_forward = (root/'control/forward.key').read_bytes()
    old_ca = (root/'control/ca.pem').read_bytes()
    assert maintenance.rotate(root)['state'] == 'ROTATED'
    assert not (root/'pki').exists()
    assert (root/'control/ca.pem').read_bytes() != old_ca
    assert (root/'control/human.token').read_bytes() != old_human
    assert (root/'control/forward.key').read_bytes() != old_forward
    assert (root/'host/human.token').read_bytes() == (root/'control/human.token').read_bytes()
    fresh = reopened(root,engine)
    with fresh.db() as db:
        encrypted = db.execute('SELECT body FROM turns').fetchone()[0]
        assert b'PRIVATE_LOCAL_CANARY' in fresh.box.decrypt(encrypted)
        with pytest.raises(InvalidToken):
            Fernet(old_key).decrypt(encrypted)
        assert db.execute('SELECT count(*) FROM connections').fetchone()[0] == 0
        assert db.execute('SELECT state FROM calls').fetchone()[0] == 'STALE'
        assert db.execute("SELECT 1 FROM closed_sessions WHERE id='s'").fetchone()
    assert not (root/'control-data/rotation.pending').exists()


def test_known_legacy_generated_pki_is_removed_after_rotation(runtime):
    from prepare_tls import generate
    root,_ = runtime
    generate(root/'pki',[('upstream',['upstream'])])
    assert (root/'pki/wrong-host.key').is_file()
    assert (root/'pki/expired.key').is_file()
    assert maintenance.rotate(root)['state'] == 'ROTATED'
    assert not (root/'pki').exists()


def test_journal_directory_is_durable_before_database_rekey(runtime,monkeypatch):
    root,engine = runtime
    original = (root/'control/storage.key').read_bytes()
    sync = maintenance.sync_directory
    def interrupted(path):
        if path == root/'control-data':
            raise OSError('synthetic journal directory fsync failure')
        sync(path)
    monkeypatch.setattr(maintenance,'sync_directory',interrupted)
    with pytest.raises(OSError):
        maintenance.rotate(root)
    assert (root/'control/storage.key').read_bytes() == original
    with sqlite3.connect(engine.path) as db:
        assert b'PRIVATE_LOCAL_CANARY' in Fernet(original).decrypt(db.execute('SELECT body FROM turns').fetchone()[0])


@pytest.mark.parametrize('name',['control-data/control.sqlite3','upstream-data/attempts.sqlite3'])
def test_running_services_block_rotation_without_key_changes(runtime,name):
    root,_ = runtime
    original = (root/'control/storage.key').read_bytes()
    with lease(root/name),pytest.raises(ValueError,match='RUNTIME_IS_RUNNING'):
        maintenance.rotate(root)
    assert (root/'control/storage.key').read_bytes() == original


def test_committed_rotation_recovers_after_key_file_write_interruption(runtime,monkeypatch):
    root, engine = runtime
    real_write = maintenance.write_private
    def interrupted(path,data):
        if str(path).endswith('control/storage.key'):
            raise OSError('synthetic interrupted write')
        real_write(path,data)
    monkeypatch.setattr(maintenance,'write_private',interrupted)
    with pytest.raises(OSError):
        maintenance.rotate(root)
    assert (root/'control-data/rotation.pending').exists()
    monkeypatch.setattr(maintenance,'write_private',real_write)
    with maintenance.offline(root):
        assert maintenance.recover(root)
    assert reopened(root,engine).history()[0]['state'] == 'STALE'


def test_failed_database_rekey_rolls_back_without_losing_original_data(runtime):
    root,engine = runtime
    before = (root/'control/storage.key').read_bytes()
    with engine.db() as db:
        db.execute("UPDATE calls SET reason='{}'")
    with pytest.raises(ValueError,match='LEGACY_RUNTIME_MIGRATION_REQUIRED'):
        maintenance.rotate(root)
    assert (root/'control/storage.key').read_bytes() == before
    with sqlite3.connect(engine.path) as db:
        assert b'PRIVATE_LOCAL_CANARY' in Fernet(before).decrypt(db.execute('SELECT body FROM turns').fetchone()[0])
    assert not (root/'control-data/rotation.pending').exists()


def test_encrypted_backup_restore_rekeys_and_expiry_is_enforced(runtime,tmp_path,monkeypatch):
    root,engine = runtime
    key = tmp_path/'private-key/backup.key'
    maintenance.write_private(key,Fernet.generate_key())
    backup = tmp_path/'managed-backups/test.whb'
    created = maintenance.make_backup(root,backup,key,ttl=60)
    assert b'PRIVATE_LOCAL_CANARY' not in backup.read_bytes()
    assert (root/'control/human.token').read_bytes() not in backup.read_bytes()
    restored = tmp_path/'restored'
    assert maintenance.restore(backup,restored,key)['state'] == 'RESTORED_NEW_CREDENTIALS'
    assert (restored/'control/human.token').read_bytes() != (root/'control/human.token').read_bytes()
    fresh = Engine(restored/'control-data/control.sqlite3',(restored/'control/storage.key').read_bytes(),engine.grant)
    assert fresh.history()[0]['state'] == 'STALE'
    assert (restored/'workspace/docs').is_dir()
    assert (restored/'workspace/reports').is_dir()
    assert (restored/'jev-budget').is_dir()
    assert (restored/'control-data/provider-reapproval.required').is_file()
    assert not (restored/'workspace/docs/release.md').exists()
    monkeypatch.setattr(time,'time',lambda:created['expires']+1)
    with pytest.raises(ValueError,match='BACKUP_EXPIRED'):
        maintenance.restore(backup,tmp_path/'too-late',key)
    assert not (tmp_path/'too-late').exists()
    assert maintenance.sweep_backups(backup.parent,key)['deleted'] == 1
    assert not backup.exists()


def test_managed_backup_extension_and_restored_new_budget_gate(runtime,tmp_path):
    import json
    root,_ = runtime
    key = tmp_path/'private-key/backup.key'
    maintenance.write_private(key,Fernet.generate_key())
    with pytest.raises(ValueError,match='MANAGED_BACKUP_EXTENSION_REQUIRED'):
        maintenance.make_backup(root,tmp_path/'managed/test.enc',key)
    ledger = root/maintenance.DATABASES[3]
    with sqlite3.connect(ledger) as db:
        db.execute('CREATE TABLE jev_policy(singleton INTEGER PRIMARY KEY,binding TEXT)')
        db.execute('INSERT INTO jev_policy VALUES(1,?)',(json.dumps({'policy_id':'original'}),))
    backup = tmp_path/'managed/test.whb'
    maintenance.make_backup(root,backup,key)
    restored = tmp_path/'restored-budget'
    maintenance.restore(backup,restored,key)
    policy = tmp_path/'policy.json'
    settings = {'enabled':True,'model':'jev-1.13.0','request_limit':2,'input_token_limit':128000,'policy_id':'original'}
    policy.write_text(json.dumps(settings))
    with pytest.raises(ValueError,match='EXPLICIT_NEW_PROVIDER_BUDGET_REQUIRED'):
        maintenance.approve_restored_provider(restored,policy)
    with pytest.raises(ValueError,match='NEW_PROVIDER_POLICY_ID_REQUIRED'):
        maintenance.approve_restored_provider(restored,policy,True)
    settings['policy_id'] = 'explicit-new-local-approval'
    policy.write_text(json.dumps(settings))
    audit = maintenance.offline_audit
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(maintenance,'offline_audit',lambda *args:(_ for _ in ()).throw(OSError('synthetic interrupted approval')))
        with pytest.raises(OSError):
            maintenance.approve_restored_provider(restored,policy,True)
    assert (restored/'control-data/provider-reapproval.required').exists()
    settings['policy_id'] = 'original'
    policy.write_text(json.dumps(settings))
    with pytest.raises(ValueError,match='NEW_PROVIDER_POLICY_ID_REQUIRED'):
        maintenance.approve_restored_provider(restored,policy,True)
    assert maintenance.offline_audit is audit
    settings['policy_id'] = 'explicit-new-local-approval'
    policy.write_text(json.dumps(settings))
    assert maintenance.approve_restored_provider(restored,policy,True)['state'] == 'NEW_PROVIDER_BUDGET_APPROVED'
    assert not (restored/'control-data/provider-reapproval.required').exists()
    assert not (restored/maintenance.DATABASES[3]).exists()
    assert (restored/'control-data/pre-restore-budget.sqlite3').is_file()


def test_backup_tamper_and_symlink_never_restore(runtime,tmp_path):
    root,_ = runtime
    key = tmp_path/'private-key/backup.key'
    maintenance.write_private(key,Fernet.generate_key())
    backup = tmp_path/'managed/test.whb'
    maintenance.make_backup(root,backup,key)
    data = bytearray(backup.read_bytes())
    data[-12] ^= 1
    backup.write_bytes(data)
    with pytest.raises(InvalidToken):
        maintenance.restore(backup,tmp_path/'invalid',key)
    linked = tmp_path/'linked'
    linked.symlink_to(root,target_is_directory=True)
    with pytest.raises(ValueError):
        maintenance.rotate(linked)
