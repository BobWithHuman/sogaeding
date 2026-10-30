import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hookgw_mcp import diagnostic
from trusted_paths import executable_path, load_helper


class LaunchSecurityTest(unittest.TestCase):
    def test_diagnostic_cannot_override_labels_or_emit_secret(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            diagnostic('INPUT', 'ADAPTER_UNAVAILABLE', {
                'stage': 'secret', 'code': 'secret', 'token': 'secret',
                'reason': 'secret', 'call_ref': 'secret'})
        value = json.loads(output.getvalue().split(' ', 1)[1])
        self.assertEqual(value, {'server': 'with_human', 'stage': 'INPUT', 'code': 'ADAPTER_UNAVAILABLE'})

    def test_missing_explicit_path_never_uses_path(self):
        with patch('trusted_paths.shutil.which') as which:
            with self.assertRaises(OSError):
                executable_path('/nonexistent/explicit/codex')
            which.assert_not_called()

    def test_path_resolution_and_literal_arguments(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test executable'
            path.write_text('#!/bin/sh\nprintf "%s" "$1"\n')
            path.chmod(0o700)
            with patch.dict(os.environ, {'PATH': tmp}):
                executable = executable_path(path.name)
            value = '$(echo injected); `whoami`'
            result = subprocess.run([str(executable), value], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, value)

    def test_helper_name_and_link_rejected(self):
        with self.assertRaises(ValueError):
            load_helper('../arbitrary')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'hookgw_hook.py').symlink_to(root / 'missing')
            with patch('trusted_paths.__file__', str(root / 'trusted_paths.py')):
                with self.assertRaises(ValueError):
                    load_helper('hookgw_hook')

    def test_secrets_are_private_at_creation(self):
        from trusted_paths import write_new_private
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'secret.pem'
            write_new_private(target, b'private-key')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_new_private(target, b'replacement')
            self.assertEqual(target.read_bytes(), b'private-key')

    def test_isolated_entrypoints(self):
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[1]
        for name in ('product_codex.py', 'hookgw_launch.py', 'hookgw_mcp.py'):
            result = subprocess.run([sys.executable, '-I', str(root / 'tools' / name), '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
