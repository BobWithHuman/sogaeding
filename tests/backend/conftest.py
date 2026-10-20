import importlib.util

import pytest


@pytest.fixture
def repo(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("prepare_tls", "/workspace/tools/prepare_tls.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pki = tmp_path / "pki"
    module.generate(pki)
    monkeypatch.setenv("RUNTIME_DIR", str(pki))
    from app import common
    monkeypatch.setattr(common, "RUNTIME", pki)
    from app.storage.repository import Repository
    return Repository(tmp_path / "control.sqlite3")
