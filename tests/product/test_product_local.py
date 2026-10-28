"""POSIX provisioning boundary; Docker calls are simulated, not Mac claims."""
import base64
import json
import os
import shlex
import stat

import hookgw_launch
import product_local as local
import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX ownership/modes required")


@pytest.fixture
def setup_product(tmp_path, monkeypatch):
    root = tmp_path / "repo with spaces"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    key = tmp_path / "jev.api-key"
    key.write_bytes(b"synthetic-only-not-live")
    key.chmod(0o600)
    product = local.Product(root, "mac-check", home=home)
    calls = []

    def docker(*args, **kwargs):
        calls.append((list(args), kwargs))
        if args[:2] == ("info", "--format"):
            return "linux\n"
        if args[:2] == ("volume", "ls"):
            return "some-unrelated-volume\n"
        if args[:3] == ("network", "ls", "-q"):
            return "existing-network\n"
        if args[:2] == ("network", "inspect"):
            return '[{"IPAM":{"Config":[{"Subnet":"10.253.0.0/24"}]}}]'
        if "export-bundle" in args:
            return json.dumps({name: base64.b64encode(("synthetic-" + name).encode()).decode() for name in local.ROLES})
        if "networks" in args:
            return '{"protected":"10.253.1.0/24","ingress":"10.253.2.0/24"}'
        if args[0] == "compose" and args[-3:] == ("config", "--format", "json"):
            return json.dumps({"services": {"control": {"volumes": [
                {"type": "bind", "source": str(key), "target": "/jev-key/jev.api-key"},
                {"type": "bind", "source": str(product.runtime / "jev-policy.json"), "target": "/jev-config/policy.json"},
                {"type": "volume", "source": "team-runtime", "target": "/runtime", "read_only": True}]}}})
        return ""

    monkeypatch.setattr(product, "docker", docker)
    return product, key, calls


def prepare(setup_product):
    product, key, calls = setup_product
    product.prepare(key, 8230, 8240, 8250)
    return product, key, calls


def test_new_posix_prepare_exports_only_client_roles_and_private_files(setup_product, capsys):
    product, key, calls = prepare(setup_product)
    assert {p.name for p in product.host.iterdir()} == {*local.ROLES, "profile.json"}
    assert stat.S_IMODE(product.client.stat().st_mode) == 0o700
    for path in product.host.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.stat().st_uid == os.getuid()
    settings = product.configuration()
    assert settings["key_file"] == str(key) and settings["control_port"] == 8230
    assert json.loads((product.runtime / "jev-policy.json").read_text())["unlimited"] is True
    profile = json.loads((product.host / "profile.json").read_text())
    assert profile["mcp_only"] is True and profile["engine_workspace"] == "/files"
    assert profile["workspace"] == str(product.root)
    assert key.read_bytes() == b"synthetic-only-not-live"
    output = capsys.readouterr()
    assert "synthetic-" not in output.out + output.err
    export = next((args, kw) for args, kw in calls if "export-bundle" in args)
    assert export[1]["capture"] and "--log-driver" in export[0] and "none" in export[0]
    assert any("/team,readonly" in arg for arg in export[0])


def test_existing_runtime_is_preserved_without_docker_or_rebuild(setup_product):
    product, key, calls = prepare(setup_product)
    original = (product.host / "machine.token").read_bytes()
    calls.clear()
    with pytest.raises(ValueError, match="EXISTING_RUNTIME"):
        product.prepare(key, 8230, 8240, 8250)
    assert calls == [] and (product.host / "machine.token").read_bytes() == original


@pytest.mark.parametrize("kind", ["public", "symlink", "repo", "empty"])
def test_invalid_key_rejected_before_any_docker_call(setup_product, kind):
    product, key, calls = setup_product
    if kind == "public":
        key.chmod(0o644)
    elif kind == "symlink":
        linked = key.with_name("link")
        linked.symlink_to(key)
        key = linked
    elif kind == "repo":
        key = product.root / "secret"
        key.write_bytes(b"synthetic")
        key.chmod(0o600)
    else:
        key.write_bytes(b"")
    with pytest.raises(ValueError):
        product.prepare(key, 8230, 8240, 8250)
    assert calls == []


def test_existing_volume_is_never_replaced_or_removed(setup_product, monkeypatch):
    product, key, _ = setup_product
    calls = []
    def docker(*args, **kwargs):
        calls.append(args)
        return product.volume + "\n"
    monkeypatch.setattr(product, "docker", docker)
    with pytest.raises(ValueError, match="EXISTING_VOLUME"):
        product.prepare(key, 8230, 8240, 8250)
    assert calls == [("volume", "ls", "--format", "{{.Name}}")]


def test_permissions_and_tampered_runtime_binding_fail_closed(setup_product):
    product, _, _ = prepare(setup_product)
    token = product.host / "machine.token"
    token.chmod(0o644)
    with pytest.raises(ValueError, match="PRIVATE_FILE"):
        product.configuration()
    token.chmod(0o600)
    prepared = product.runtime / "prepared.json"
    prepared.write_text('{"volume":"someone-else","root_id":"wrong"}')
    with pytest.raises(ValueError, match="VOLUME_MISMATCH"):
        product.configuration()


def test_parent_symlink_and_writable_parent_are_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="SYMLINK"):
        local.private_parents(link / "new")
    target.chmod(0o777)
    with pytest.raises(ValueError, match="UNSAFE_PARENT"):
        local.private_parents(target / "new")


def test_private_writer_never_overwrites_existing_file(tmp_path):
    path = tmp_path / "credential"
    local.write_private(path, b"first")
    with pytest.raises(FileExistsError):
        local.write_private(path, b"second")
    assert path.read_bytes() == b"first"


def test_compose_reuses_one_config_and_keeps_volume_on_down(setup_product, monkeypatch):
    product, _, calls = prepare(setup_product)
    monkeypatch.setenv("SOGAEDING_TEAM_VOLUME", "wrong-inherited-volume")
    monkeypatch.setenv("SOGAEDING_TEAM_IMAGE", "wrong-inherited-image")
    calls.clear()
    product.compose("up")
    compose_args, kwargs = calls[-1]
    assert compose_args == ["compose", "--project-directory", product.root, "-p", product.project,
                            "-f", "-", "up", "-d", "control", "upstream", "gateway"]
    assert kwargs["env"]["SOGAEDING_TEAM_VOLUME"] == product.volume
    assert kwargs["env"]["SOGAEDING_TEAM_IMAGE"] == local.IMAGE
    assert kwargs["env"]["SOGAEDING_PROTECTED_SUBNET"] == "10.253.1.0/24"
    config = json.loads(kwargs["input_text"])
    mounts = config["services"]["control"]["volumes"]
    assert [m["target"] for m in mounts] == ["/jev-key", "/jev-config", "/runtime"]
    assert all(m["read_only"] for m in mounts)
    assert mounts[0]["volume"]["subpath"].endswith("/control-provider")
    assert "synthetic-only" not in kwargs["input_text"]
    product.compose("dashboard")
    assert calls[-1][0][-4:] == ["up", "-d", "--no-deps", "dashboard"]
    product.compose("down")
    assert calls[-1][0][-3:] == ["--profile", "dashboard", "down"]
    assert all("--volumes" not in args and "-v" not in args for args, _ in calls)


def test_dashboard_check_needs_no_codex_but_start_uses_existing_connector(setup_product, monkeypatch):
    product, _, _ = prepare(setup_product)
    runs = []
    monkeypatch.setattr(product, "run", lambda args, **kw: runs.append(args))
    monkeypatch.setattr(local.shutil, "which", lambda _: None)
    product.connect("check", engine_only=True)
    assert len(runs) == 1 and runs[0][-3:] == ["check", "--host", str(product.host)]
    with pytest.raises(ValueError, match="INSTALLED_CODEX_REQUIRED"):
        product.connect("check")
    executable = product.client / "codex"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o700)
    # Docker's isolated /tmp is noexec; this test inspects dispatch, not a CLI.
    access = os.access
    monkeypatch.setattr(local.os, "access", lambda path, mode: True if path == executable else access(path, mode))
    runs.clear()
    product.connect("check", str(executable))
    assert runs[0][3] == "cli-check" and runs[1][3] == "check"
    product.connect("start", str(executable))
    assert runs[-1][3] == "start" and "--exe" in runs[-1]
    assert "--dangerously-bypass-approvals-and-sandbox" not in str(runs)


def test_macos_location_and_port_validation(setup_product, monkeypatch):
    product, key, calls = setup_product
    monkeypatch.setattr(local.sys, "platform", "darwin")
    other = local.Product(product.root, "another", home=product.client.parents[4])
    assert "/Library/Application Support/WithHuman/Codex/" in str(other.client)
    with pytest.raises(ValueError, match="DISTINCT_PORTS"):
        product.prepare(key, 8130, 8130, 8150)
    assert not calls


def test_posix_hook_commands_preserve_spaces_quotes_and_shell_metacharacters(tmp_path):
    root = tmp_path / "repo $USER `id` 'quote'"
    host = tmp_path / "Application Support" / "host"
    python = "/opt/python with space/bin/python3"
    flags = hookgw_launch.overrides(root, host, python)
    hook = next(arg for arg in flags if arg.startswith("hooks.UserPromptSubmit="))
    # Parse the actual TOML inline table emitted to Codex.
    import tomllib
    values = tomllib.loads(hook)
    command = values["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert shlex.split(command) == [python, "-I", str(root / "tools/hookgw_hook.py"), str(host)]


def test_provider_stdin_import_is_private_and_cannot_replace_existing(tmp_path, monkeypatch, capsys):
    import io
    payload = json.dumps({"key": base64.b64encode(b"synthetic-secret").decode(), "policy": {"unlimited": True}})
    monkeypatch.setattr(local.sys, "stdin", io.StringIO(payload))
    local.install_provider(tmp_path)
    folder = tmp_path / "control-provider"
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((folder / "jev.api-key").stat().st_mode) == 0o600
    assert (folder / "jev.api-key").read_bytes() == b"synthetic-secret"
    monkeypatch.setattr(local.sys, "stdin", io.StringIO(payload))
    with pytest.raises(FileExistsError):
        local.install_provider(tmp_path)
    assert "synthetic-secret" not in capsys.readouterr().out


def test_changed_external_key_cannot_silently_keep_stale_provider_copy(setup_product):
    product, key, _ = prepare(setup_product)
    key.write_bytes(b"different-synthetic-key")
    with pytest.raises(ValueError, match="EXTERNAL_KEY_CHANGED"):
        product.environment(product.configuration())


def test_provider_mount_adapter_refuses_changed_base_contract():
    with pytest.raises(ValueError, match="COMPOSE_PROVIDER_MOUNT_CONTRACT_CHANGED"):
        local.provider_mounts({"services": {"control": {"volumes": []}}}, "local")
