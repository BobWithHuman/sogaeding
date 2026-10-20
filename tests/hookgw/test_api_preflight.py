"""Stage A: readiness is not authentication success or semantic acceptance."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ready(tmp_path, monkeypatch):
    mod = load("hookgw_preflight")
    exe = tmp_path / "codex"
    exe.write_bytes(b"fixture executable")
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-only-not-a-real-key")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "auth.json").write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"access_token": "fixture-chatgpt"}}))
    for name in ("machine.token", "human.token"):
        (tmp_path / name).write_text("fixture-only-host-token")
    def command(args, timeout=15):
        text = "codex-cli 0.154.0" if args[-1] == "--version" else "hooks stable true\n"
        return subprocess.CompletedProcess(args, 0, text, "")
    monkeypatch.setattr(mod, "command", command)
    monkeypatch.setattr(mod, "tls_health", lambda _: {"spec": "MVP-SPEC-5", "judge_mode": "LIVE_USER", "gateway_tls": True})
    monkeypatch.setattr(mod, "mcp_startup", lambda *_: {"server": "with_human", "ready": True, "paid_requests": 0, "tools_call_count": 0})
    monkeypatch.setattr(mod, "control_probe", lambda _: {"live_env": True, "key_readable_nonempty": True, "budget_readable": True,
                                                       "runtime_directory_preserved": True, "existing_literal_masking": True,
                                                       "requests_attempted": 12, "remaining": 12, "limit": 24, "budget_unchanged": True})
    return mod, tmp_path, exe


def report(ready):
    mod, root, exe = ready
    return mod.run(root, root, str(exe), [], "gpt-5.6-luna")


def test_readiness_separates_personal_login_and_api_credentials_without_secrets(ready):
    value = report(ready)
    assert value["ready_to_open_cli"]
    assert value["actor"]["personal_stored_auth"] == "CHATGPT"
    assert value["actor"]["authentication"] == "ENV_API_KEY"
    assert value["model_access"] == "NOT_VERIFIED_NO_REQUEST"
    assert value["hook_trust"].startswith("NOT_VERIFIED")
    assert "fixture" not in json.dumps(value)


@pytest.mark.parametrize("issue", ["actor", "judge_key", "budget", "live", "tls", "cli", "mask"])
def test_preflight_blockers_are_separate(ready, monkeypatch, issue):
    mod, _, _ = ready
    expected = {"actor": "ACTOR_API_KEY_MISSING", "judge_key": "CONTROL_JUDGE_KEY_UNREADABLE_OR_EMPTY",
                "budget": "JUDGE_BUDGET_INSUFFICIENT_FOR_READ_AND_WRITE", "live": "CONTROL_NOT_LIVE_USER",
                "tls": "APP_CA_OR_TLS_HEALTH_FAILED", "cli": "CLI_HOOK_CONFIGURATION_FAILED", "mask": "EXISTING_SECRET_MASKING_UNVERIFIED"}[issue]
    if issue == "actor":
        monkeypatch.delenv("OPENAI_API_KEY")
    elif issue in ("judge_key", "budget", "mask"):
        old = mod.control_probe(None)
        old.update({"key_readable_nonempty": False} if issue == "judge_key" else {"existing_literal_masking": False} if issue == "mask" else {"requests_attempted": 22, "remaining": 2})
        monkeypatch.setattr(mod, "control_probe", lambda _: old)
    elif issue == "live":
        monkeypatch.setattr(mod, "tls_health", lambda _: {"spec": "MVP-SPEC-5", "judge_mode": "UNAVAILABLE"})
    elif issue == "tls":
        def fail(_):
            raise OSError("secret must not appear")
        monkeypatch.setattr(mod, "tls_health", fail)
    else:
        monkeypatch.setattr(mod, "command", lambda args, timeout=15: subprocess.CompletedProcess(args, 1, "", "secret must not appear"))
    value = report(ready)
    assert not value["ready_to_open_cli"] and expected in value["issues"]
    assert "secret must" not in json.dumps(value)


def test_api_flags_use_env_only_and_do_not_force_login_or_sandbox():
    flags = load("hookgw_launch").api_overrides("gpt-5.6-luna")
    text = " ".join(flags)
    assert 'requires_openai_auth=false' in text and 'env_key="OPENAI_API_KEY"' in text
    assert 'https://api.openai.com/v1' in text and 'gpt-5.6-luna' in text
    assert all(x not in text for x in ("forced_login", "sandbox", "approval", "api_key=", "fixture-only"))


@pytest.mark.parametrize("config", ['forced_login_method="chatgpt"', 'forced_login_method="api"', '[model_providers.with_human_openai_api]\nname="other"', '[profiles.personal.hooks]\nUserPromptSubmit=[]', '[profiles.personal]\nforced_login_method="chatgpt"'])
def test_login_restrictions_and_reserved_provider_fail_before_cli(tmp_path, monkeypatch, config):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text(config)
    with pytest.raises(SystemExit):
        load("hookgw_launch").check_conflicts(tmp_path, [], api=True)


def test_managed_layer_never_silently_overrides_api_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "managed_config.toml").write_text('model_provider="other"')
    with pytest.raises(SystemExit, match="Managed defaults"):
        load("hookgw_launch").check_conflicts(tmp_path, [], api=True)


def test_persisted_cli_hook_consent_is_not_an_executable_definition_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    config = tmp_path / "config.toml"
    text = '[hooks.state.saved]\ntrusted_hash="sha256:fixture-consent-state"\n'
    config.write_text(text)
    load("hookgw_launch").check_conflicts(tmp_path, [], api=True)
    assert config.read_text() == text
    config.write_text(text + '\n[[hooks.PreToolUse]]\nmatcher="*"\n')
    with pytest.raises(SystemExit, match="reviewed merge"):
        load("hookgw_launch").check_conflicts(tmp_path, [], api=True)


@pytest.mark.parametrize("args", [["--model", "other"], ["-mother"], ["resume"], ["login"], ["--model-provider=other"]])
def test_api_launch_rejects_arguments_changing_auth_model_or_session(tmp_path, monkeypatch, args):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "unused"))
    with pytest.raises(SystemExit):
        load("hookgw_launch").check_conflicts(tmp_path, args, api=True)


@pytest.mark.parametrize("ready_only", [False, True])
def test_readiness_gate_never_connects_or_starts_model_when_failed_or_preflight(tmp_path, monkeypatch, capsys, ready_only):
    launch = load("hookgw_launch")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "unused"))
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fixture", "--api", "--model", "gpt-5.6-luna"] + (["--preflight"] if ready_only else []))
    class Helper:
        @staticmethod
        def run(*_args):
            return {"ready_to_open_cli": ready_only, "issues": [] if ready_only else ["CONTROL_NOT_LIVE_USER"]}
    monkeypatch.setattr(launch, "trusted_helper", lambda _: Helper)
    def forbidden(*_args, **_kwargs):
        pytest.fail("readiness failure must never connect or start Codex")
    monkeypatch.setattr(launch, "trusted_send", forbidden)
    monkeypatch.setattr(launch.subprocess, "call", forbidden)
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == (0 if ready_only else 2)
    assert ("true" if ready_only else "CONTROL_NOT_LIVE_USER") in capsys.readouterr().out


def test_duplicate_model_cannot_override_terminal_selection(tmp_path, monkeypatch):
    launch = load("hookgw_launch")
    monkeypatch.setattr(sys, "argv", ["launcher", "--root", str(tmp_path), "--exe", "fixture", "--api", "--model", "gpt-5.6-luna", "--model=other"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2


def test_empty_mountpoint_preserves_existing_role_files_and_refuses_replacement(tmp_path):
    mod = load("hookgw_key_mountpoint")
    for name in ("ca.pem", "control.pem", "control.key", "storage.key", "human.token", "machine.token", "machine.id", "forward.key", "grant.json"):
        (tmp_path / name).write_text("fixture-existing-role")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert mod.prepare(tmp_path)["existing_role_files_unchanged"] == 9
    assert mod.prepare(tmp_path)["legacy_key_copied"] is False
    assert all((tmp_path / name).read_bytes() == value for name, value in before.items())
    (tmp_path / "judge.api-key").write_text("existing-file-must-stay")
    with pytest.raises(ValueError, match="no replacement"):
        mod.prepare(tmp_path)
    assert (tmp_path / "judge.api-key").read_text() == "existing-file-must-stay"


def test_control_probe_never_executes_workspace_docker(tmp_path, monkeypatch):
    mod = load("hookgw_preflight")
    monkeypatch.setattr(mod.shutil, "which", lambda _: str(tmp_path / "docker"))
    with pytest.raises(ValueError, match="TRUSTED_DOCKER"):
        mod.control_probe(tmp_path)


def test_preserved_runtime_masks_literal_even_next_to_unicode(tmp_path, monkeypatch):
    from app import common
    token = "A" * 48
    (tmp_path / "human.token").write_text(token)
    monkeypatch.setattr(common, "RUNTIME", tmp_path)
    assert common.mask("가" + token + "나") == "가[REDACTED]나"


def test_runtime_installer_preserves_empty_mountpoint_compatibility(tmp_path, monkeypatch):
    mod = load("hookgw_install")
    source, target = tmp_path / "source", tmp_path / "target"
    roles = {"control": ["ca.pem", "control.pem", "control.key", "storage.key", "human.token", "machine.token", "machine.id", "forward.key", "grant.json"],
             "gateway": ["ca.pem", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key"],
             "upstream": ["ca.pem", "upstream.pem", "upstream.key", "forward.key"], "bundle": ["manifest.json"]}
    for role, names in roles.items():
        (source / role).mkdir(parents=True)
        for name in names:
            (source / role / name).write_text("fixture-" + role + name)
    (target / "control").mkdir(parents=True)
    (target / "control/judge.api-key").write_bytes(b"")
    monkeypatch.setattr(mod.os, "chown", lambda *_: None)
    mod.install(source, target)
    assert (target / "control/judge.api-key").read_bytes() == b""
    (target / "control/judge.api-key").write_text("do-not-overwrite")
    with pytest.raises(SystemExit):
        mod.install(source, target)
    assert (target / "control/judge.api-key").read_text() == "do-not-overwrite"
