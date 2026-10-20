"""Isolated JEV rules-only preflight; never opens actor CLI or any model API."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location("jev_test_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider():
    return {"pdp_mode": "JEV", "model": "jev-1.13.0", "settings_enabled": False,
            "live_authorization": "NOT_AUTHORIZED", "runtime_directory_preserved": True,
            "existing_literal_masking": True, "provider_key_present": False, "provider_ledger_present": False}


@pytest.fixture
def ready(tmp_path, monkeypatch):
    module = load("hookgw_preflight")
    exe = tmp_path / "codex"
    exe.write_bytes(b"fake-executable")
    for name in ("machine.token", "human.token"):
        (tmp_path / name).write_text("fake-host-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-actor-secret")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    def command(args, timeout=15):
        return subprocess.CompletedProcess(args, 0, "codex-cli 0.154.0" if args[-1] == "--version" else "hooks stable true\n", "")
    monkeypatch.setattr(module, "command", command)
    monkeypatch.setattr(module, "tls_health", lambda _host, jev=False: {"spec": "MVP-SPEC-5", "judge_mode": "JEV_RULES_ONLY" if jev else "LIVE_USER", "gateway_tls": True})
    monkeypatch.setattr(module, "mcp_startup", lambda *_: {"ready": True, "tools_call_count": 0, "paid_requests": 0})
    monkeypatch.setattr(module, "control_probe", lambda _root, jev=False: provider() if jev else pytest.fail("OpenAI key/budget must not be required in JEV rules mode"))
    return module, tmp_path, exe


def report(ready):
    module, root, exe = ready
    return module.run(root, root, str(exe), [], "gpt-5.6-luna", jev=True)


def test_rules_readiness_distinguishes_actor_from_disabled_semantics(ready):
    value = report(ready)
    assert value["ready_to_open_cli"] and value["issues"] == []
    assert value["semantic_write_ready"] is False
    assert value["jev_live"] == "NOT_AUTHORIZED"
    assert value["jev_model_access"] == "NOT_VERIFIED_NO_REQUEST"
    assert "control_judge" not in value and "fake-" not in json.dumps(value)
    assert value["paid_requests"] == 0
    assert value["mcp_startup"]["tools_call_count"] == 0


@pytest.mark.parametrize("changed,issue", [
    ({"pdp_mode": "GPT"}, "CONTROL_NOT_JEV_RULES_ONLY"),
    ({"model": "jev-latest"}, "JEV_MODEL_NOT_PINNED"),
    ({"settings_enabled": True}, "JEV_LIVE_CONFIGURATION_REQUIRES_SEPARATE_REVIEW"),
    ({"live_authorization": "AUTHORIZED"}, "JEV_LIVE_CONFIGURATION_REQUIRES_SEPARATE_REVIEW"),
    ({"provider_key_present": True}, "JEV_RULES_EXPECTS_NO_PROVIDER_KEY_OR_LEDGER"),
    ({"provider_ledger_present": True}, "JEV_RULES_EXPECTS_NO_PROVIDER_KEY_OR_LEDGER"),
    ({"existing_literal_masking": False}, "EXISTING_SECRET_MASKING_UNVERIFIED"),
])
def test_rules_mode_never_silently_claims_jev_live_readiness(ready, monkeypatch, changed, issue):
    module, _, _ = ready
    monkeypatch.setattr(module, "control_probe", lambda _root, jev=False: {**provider(), **changed})
    value = report(ready)
    assert not value["ready_to_open_cli"] and issue in value["issues"]
    assert not value["semantic_write_ready"]


def test_rules_still_requires_actor_key_and_mcp_tls(ready, monkeypatch):
    module, _, _ = ready
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.setattr(module, "tls_health", lambda _host, jev=False: {"spec": "MVP-SPEC-5", "judge_mode": "LIVE_USER"})
    monkeypatch.setattr(module, "mcp_startup", lambda *_: {"ready": False})
    value = report(ready)
    assert {"ACTOR_API_KEY_MISSING", "CONTROL_NOT_JEV_RULES_ONLY", "WITH_HUMAN_MCP_STARTUP_FAILED"} <= set(value["issues"])


@pytest.mark.parametrize("jev", [True, False])
def test_tls_health_rejects_other_profile_ports_before_io(tmp_path, jev):
    module = load("hookgw_preflight")
    opposite = {"control_url": "https://127.0.0.1:8030" if jev else "https://127.0.0.1:8032",
                "gateway_url": "https://127.0.0.1:8040/mcp" if jev else "https://127.0.0.1:8042/mcp"}
    (tmp_path / "profile.json").write_text(json.dumps(opposite))
    with pytest.raises(ValueError, match="UNEXPECTED_ENDPOINT"):
        module.tls_health(tmp_path, jev=jev)


def test_control_probe_selects_isolated_compose_and_readonly_code(tmp_path, monkeypatch):
    module = load("hookgw_preflight")
    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/docker")
    calls = []
    def command(args, timeout=15):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, json.dumps(provider()), "")
    monkeypatch.setattr(module, "command", command)
    assert module.control_probe(tmp_path, jev=True) == provider()
    args = calls[0]
    assert str(tmp_path / "compose.hookgw.jev.yaml") in args
    assert str(tmp_path / "compose.hookgw.live.yaml") not in args
    assert args[-1] == module.JEV_CONTROL_PROBE
    assert all(text not in module.JEV_CONTROL_PROBE for text in ("import sqlite3", "sqlite3.connect", "DevelopmentJudge", ".claim(", ".write_", "mkdir", "openai"))


def test_launcher_jev_preflight_uses_own_profile_without_connect_or_actor(tmp_path, monkeypatch, capsys):
    module = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "unused"))
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fake", "--api", "--model", "gpt-5.6-luna", "--jev-rules", "--preflight"])
    captured = []
    class Helper:
        @staticmethod
        def run(*args, **kwargs):
            captured.append((args, kwargs))
            return {"ready_to_open_cli": True, "issues": [], "semantic_write_ready": False}
    monkeypatch.setattr(module, "trusted_helper", lambda _: Helper)
    monkeypatch.setattr(module, "trusted_send", lambda: pytest.fail("Preflight never connects actor session"))
    monkeypatch.setattr(module.subprocess, "call", lambda *_args, **_kwargs: pytest.fail("No actor CLI launch"))
    with pytest.raises(SystemExit) as status:
        module.main()
    assert status.value.code == 0
    args, kwargs = captured[0]
    assert args[1] == tmp_path / "artifacts/runtime-hookgw/host-jev" and kwargs == {"jev": True}
    assert '"semantic_write_ready": false' in capsys.readouterr().out


def test_jev_launcher_requires_explicit_api_mode(tmp_path, monkeypatch):
    module = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fake", "--jev-rules"])
    with pytest.raises(SystemExit, match="requires explicit --api"):
        module.main()


def test_powershell_switch_preserves_historical_path_and_refuses_legacy_mount_mutation():
    text = (ROOT / "scripts/hookgw_connect.ps1").read_text()
    assert "[switch]$JevRules" in text
    assert "'-JevRules requires -Api -Model" in text
    assert "if ($launch.JevRules) { $modeArgs+=@('--jev-rules') }" in text
    assert "Personal login unchanged" in text
