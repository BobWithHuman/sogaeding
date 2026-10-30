import os
import tempfile
import unittest
from pathlib import Path
from app.private_files import read_private


class PrivateFilesTest(unittest.TestCase):
    def test_regular_and_rejected_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / 'key'
            key.write_bytes(b'secret')
            key.chmod(0o600)
            self.assertEqual(read_private(key), b'secret')
            with self.assertRaises(OSError):
                read_private(key, 2)
            link = root / 'link'
            link.symlink_to(key)
            with self.assertRaises(OSError):
                read_private(link)
            directory = root / 'directory'
            directory.symlink_to(root, target_is_directory=True)
            with self.assertRaises(OSError):
                read_private(directory / 'key')
            key.chmod(0o666)
            with self.assertRaises(OSError):
                read_private(key)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(OSError):
                read_private(fifo)


class PrivateDatabaseTest(unittest.TestCase):
    def test_restart_transactions_and_sidecars(self):
        from app.private_files import private_connect
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'private' / 'history.db'
            with private_connect(db) as connection:
                connection.execute('create table history(value)')
                connection.execute('insert into history values (?)', ('retained',))
            self.assertEqual(db.stat().st_mode & 0o777, 0o600)
            with private_connect(db) as connection:
                self.assertEqual(connection.execute('select * from history').fetchall(), [('retained',)])
            sidecar = Path(str(db) + '-wal')
            sidecar.symlink_to(db)
            with self.assertRaises(OSError):
                with private_connect(db):
                    pass
            sidecar.unlink()
            os.link(db, sidecar)
            with self.assertRaises(OSError):
                with private_connect(db):
                    pass

    def test_unsafe_directory_and_final_link(self):
        from app.private_files import private_connect
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / 'public'
            public.mkdir(mode=0o755)
            with self.assertRaises(OSError):
                with private_connect(public / 'db'):
                    pass
            link = root / 'db'
            target = root / 'untouched'
            target.write_bytes(b'original')
            link.symlink_to(target)
            with self.assertRaises(OSError):
                with private_connect(link):
                    pass
            self.assertEqual(target.read_bytes(), b'original')

    def test_concurrent_writers(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.private_files import private_connect
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'db'
            with private_connect(db) as connection:
                connection.execute('create table counts(value integer)')
                connection.execute('insert into counts values (0)')
            def increment(_):
                with private_connect(db, timeout=3) as connection:
                    connection.execute('update counts set value=value+1')
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(increment, range(16)))
            with private_connect(db) as connection:
                self.assertEqual(connection.execute('select value from counts').fetchone()[0], 16)

    def test_application_audit_and_budget_survive_restart(self):
        from app.storage.auth_audit import AuthAudit
        from app.transparent.jev import JevClient, JevSettings
        from app.private_files import private_connect
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / 'audit.db'
            AuthAudit(audit).record('HUMAN', 401)
            AuthAudit(audit).record('HUMAN', 401)
            with private_connect(audit, read_only=True) as db:
                self.assertEqual(db.execute('select sum(count) from auth_failures').fetchone()[0], 2)
            budget = root / 'budget.db'
            settings = JevSettings(budget_path=budget, policy_id='test', unlimited=True)
            JevClient(settings)._claim('first', 'A')
            JevClient(settings)._claim('second', 'B')
            with private_connect(budget, read_only=True) as db:
                self.assertEqual(db.execute('select count(*) from jev_attempts').fetchone()[0], 2)

    def test_replacement_between_directory_open_and_file_open(self):
        from unittest.mock import patch
        from app.private_files import read_private
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / 'key'
            victim = root / 'victim'
            key.write_bytes(b'original')
            key.chmod(0o600)
            victim.write_bytes(b'must-not-read')
            victim.chmod(0o600)
            original_open = os.open
            def replace(name, flags, *args, **kwargs):
                if name == 'key':
                    key.unlink()
                    key.symlink_to(victim)
                return original_open(name, flags, *args, **kwargs)
            with patch('app.private_files.os.open', side_effect=replace):
                with self.assertRaises(OSError):
                    read_private(key)

    def test_runtime_lease_excludes_other_owner_and_rejects_links(self):
        from app.transparent.runtime_lock import lease
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'db'
            with lease(path):
                with self.assertRaises(ValueError):
                    with lease(path):
                        pass
            lock = Path(str(path) + '.service-lock')
            lock.unlink()
            lock.symlink_to(path)
            with self.assertRaises(OSError):
                with lease(path):
                    pass

    def test_read_only_bind_mount_uses_mount_boundary(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from app.private_files import read_private
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'key'
            key.write_bytes(b'key')
            key.chmod(0o644)
            with self.assertRaises(OSError):
                read_private(key)
            with patch('app.private_files.os.fstatvfs', return_value=SimpleNamespace(f_flag=os.ST_RDONLY)):
                self.assertEqual(read_private(key), b'key')
