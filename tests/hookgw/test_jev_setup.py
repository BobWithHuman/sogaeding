import importlib.util
import json
from pathlib import Path

import pytest

from app.transparent.jev_config import load_settings


def test_absent_policy_has_no_provider_key_or_budget(tmp_path):
    assert not load_settings(tmp_path / "missing-policy.json").authorized()
    assert list(tmp_path.iterdir()) == []


def test_settings_cannot_supply_endpoint_key_or_legacy_ledger(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"enabled": True, "endpoint": "http://untrusted.invalid"}))
    with pytest.raises(ValueError):
        load_settings(path)
    path.write_text(json.dumps({"enabled": True, "model": "jev-latest", "request_limit": 2, "input_token_limit": 128000, "policy_id": "reviewed-test"}))
    with pytest.raises(ValueError):
        load_settings(path)


def test_separate_host_prepare_never_overwrites_existing_profile(tmp_path):
    spec = importlib.util.spec_from_file_location("prepare_jev", Path(__file__).resolve().parents[2] / "tools/hookgw_jev_prepare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    host = tmp_path / "artifacts/runtime-hookgw/host"
    host.mkdir(parents=True)
    for name in ("ca.pem", "machine.id", "machine.token", "human.token"):
        (host / name).write_text("fake-only-" + name)
    (host / "profile.json").write_text("original-profile")
    module.prepare(tmp_path)
    module.prepare(tmp_path)
    assert (host / "profile.json").read_text() == "original-profile"
    new = host.with_name("host-jev")
    assert json.loads((new / "profile.json").read_text())["control_url"] == "https://127.0.0.1:8032"
    (new / "machine.token").write_text("unexpected")
    with pytest.raises(SystemExit):
        module.prepare(tmp_path)
    assert (new / "machine.token").read_text() == "unexpected"
