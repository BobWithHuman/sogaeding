"""Explicit child argv opt-in; fake CLI only and unchanged human approval boundary."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_child_manual_then_default_restored(tmp_path, monkeypatch):
    launch = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    config = home / "config.toml"
    config.write_text('approvals_reviewer="auto_review"\napproval_policy="on-request"\nsandbox_mode="read-only"\n')
    auth = home / "auth.json"
    auth.write_text('{"fake":"never used"}')
    before = [p.read_bytes() for p in (config, auth)]
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setattr(launch, "check_manual_requirements", lambda: None)
    runs, preflight = [], []
    class Helper:
        @staticmethod
        def run(*args, **kwargs):
            preflight.append(kwargs)
            return {"ready_to_open_cli": True}
    monkeypatch.setattr(launch, "trusted_helper", lambda _: Helper)
    monkeypatch.setattr(launch, "trusted_send", lambda: lambda *_: {"connection": "fake-child-connection"})
    monkeypatch.setattr(launch.subprocess, "call", lambda args, **kw: runs.append((args, kw)) or 0)
    base = ["launcher", "--root", str(tmp_path), "--exe", "fake-cli", "--api", "--model", "gpt-5.6-luna", "--jev-rules"]
    for extra in (["--manual-review"], []):
        monkeypatch.setattr(sys, "argv", base + extra)
        with pytest.raises(SystemExit) as status:
            launch.main()
        assert status.value.code == 0
    manual, default = runs[0][0], runs[1][0]
    assert manual == default + launch.manual_review_overrides()
    assert launch.manual_review_overrides() == ["-c", 'approvals_reviewer="user"', "-c", 'approval_policy="on-request"']
    assert not any("sandbox" in flag or "never" in flag or "yolo" in flag for flag in manual)
    assert sum('hooks.' in flag for flag in manual) == 3
    assert preflight == [{"jev": True, "manual_review": True}, {"jev": True}]
    assert [p.read_bytes() for p in (config, auth)] == before


@pytest.mark.parametrize("modes,extra", [
    ([], ["--manual-review"]),
    (["--api", "--model", "gpt-5.6-luna"], ["--manual-review"]),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-review", "--manual-review"]),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-rev"]),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-review", "-c", 'approval_policy="never"']),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-review", "--sandbox", "danger-full-access"]),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-review", "--profile", "x"]),
    (["--api", "--model", "gpt-5.6-luna", "--jev-rules"], ["--manual-review", "--yolo"]),
])
def test_no_other_scope_or_security_override(tmp_path, monkeypatch, modes, extra):
    launch = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty"))
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fake", *modes, *extra])
    monkeypatch.setattr(launch, "trusted_helper", lambda _: pytest.fail("No preflight or actor on invalid flags"))
    with pytest.raises(SystemExit):
        launch.main()


def test_managed_reviewer_constraint_prevents_any_actor(tmp_path, monkeypatch):
    launch = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    managed = tmp_path / "managed_config.toml"
    managed.write_text('approvals_reviewer="auto_review"')
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fake", "--api", "--model", "gpt-5.6-luna", "--jev-rules", "--manual-review"])
    with pytest.raises(SystemExit, match="Managed defaults"):
        launch.main()
    assert managed.read_text() == 'approvals_reviewer="auto_review"'


def test_ps_does_not_persist_manual_review():
    script = (ROOT / "scripts/hookgw_connect.ps1").read_text()
    assert "[switch]$ManualReview" not in script
    assert "codex --manual-review" in script
    assert "ManualReview=" not in script


@pytest.mark.parametrize("stderr,exitcode,issue", [("managed fallback to auto_review", 0, "HOST_MANUAL_REVIEW_CLI_WARNING"), ("", 1, "HOST_MANUAL_REVIEW_CONFIGURATION_REJECTED"), ("", 0, None)])
def test_preflight_manual_route_and_managed_fallback(tmp_path, monkeypatch, stderr, exitcode, issue):
    pre = load("hookgw_preflight")
    launch = load("hookgw_launch")
    exe = tmp_path / "fake-cli"
    exe.write_bytes(b"fake")
    for name in ("human.token", "machine.token"):
        (tmp_path / name).write_text("fake-credential")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    def command(args, timeout=15):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "codex-cli 0.154.0", "")
        if args[-2:] == ["features", "list"]:
            return subprocess.CompletedProcess(args, exitcode, "hooks stable true\n", stderr)
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(pre, "command", command)
    monkeypatch.setattr(pre, "tls_health", lambda *a, **k: {"spec": "MVP-SPEC-5", "judge_mode": "JEV_RULES_ONLY", "gateway_tls": True})
    monkeypatch.setattr(pre, "mcp_startup", lambda *_: {"ready": True})
    monkeypatch.setattr(pre, "control_probe", lambda *a, **k: {"pdp_mode": "JEV", "model": "jev-1.13.0", "settings_enabled": False, "live_authorization": "NOT_AUTHORIZED", "runtime_directory_preserved": True, "existing_literal_masking": True, "provider_key_present": False, "provider_ledger_present": False})
    flags = launch.manual_review_overrides()
    result = pre.run(tmp_path, tmp_path, str(exe), flags, "gpt-5.6-luna", jev=True, manual_review=True)
    assert result["host_review"]["requested_reviewer"] == "user"
    assert result["host_review"]["sandbox"] == "INHERITED_UNCHANGED"
    assert result["host_review"]["human_tool_approval"] == "NOT_RUN_USER_NEXT"
    assert result["model_access"] == "NOT_VERIFIED_NO_REQUEST"
    assert (issue in result["issues"]) if issue else result["ready_to_open_cli"]
    assert result["ready_to_open_cli"] is (issue is None)
    assert "managed fallback" not in json.dumps(result)
