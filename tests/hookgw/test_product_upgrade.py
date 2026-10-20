"""Explicit code revision preserves previous bundle and requires known old bytes."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_code_only_upgrade_preserves_archive_and_refuses_unknown_old_bytes(tmp_path):
    build, installer = load("hookgw_bundle"), load("hookgw_install")
    app = tmp_path / "src/app"
    app.mkdir(parents=True)
    (app / "engine.py").write_text("old reviewed code")
    contract = tmp_path / "docs/mvp/contracts"
    contract.mkdir(parents=True)
    (contract / "test.json").write_text("{}")
    runtime = tmp_path / "artifacts/runtime-hookgw"
    runtime.mkdir(parents=True)
    build.bundle(tmp_path)
    deployed = tmp_path / "installed/product"
    shutil.copytree(runtime / "bundle", deployed)
    (app / "engine.py").write_text("new reviewed code")
    with pytest.raises(SystemExit, match="differs"):
        build.bundle(tmp_path, verify=True, current=True)
    build.bundle(tmp_path, update=True)
    previous = next((runtime / "bundle-history").glob("*/manifest.json"))
    assert (previous.parent / "src/app/engine.py").read_text() == "old reviewed code"
    (deployed / "src/app/engine.py").write_text("unexpected bytes")
    with pytest.raises(SystemExit):
        installer.upgrade_product(runtime, deployed, previous)
    assert (deployed / "src/app/engine.py").read_text() == "unexpected bytes"
    (deployed / "src/app/engine.py").write_text("old reviewed code")
    installer.upgrade_product(runtime, deployed, previous)
    assert (deployed / "src/app/engine.py").read_text() == "new reviewed code"
    assert (previous.parent / "src/app/engine.py").read_text() == "old reviewed code"
    assert not list(deployed.rglob("*.pending-upgrade"))


def test_span_schema_file_matches_api_contract():
    from app.pdp.semantic import SPAN_JUDGE_SCHEMA
    assert json.loads((ROOT / "docs/mvp/contracts/hookgw_judge.schema.json").read_text()) == SPAN_JUDGE_SCHEMA
