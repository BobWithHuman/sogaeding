"""New-clone sharing boundaries, independent of local keys and old artifacts."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_export_copies_source_but_not_runtime_credentials_or_host_cache(tmp_path):
    exporter = module("repository_export")
    for name in (
        "src/app/code.py",
        "src/app/local.token",
        "artifacts/key.txt",
        ".env",
        ".env.example",
        "%SystemDrive%/Cache.db",
        "README.md",
        "tools/helper.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic material")
    target = tmp_path / "artifacts/export/source"
    result = exporter.export(tmp_path, target)
    assert result["files"] == 4
    assert (target / "src/app/code.py").exists()
    assert (target / ".env.example").exists()
    assert not (target / "src/app/local.token").exists()
    assert not (target / "artifacts").exists()
    assert not (target / "%SystemDrive%").exists()
    with pytest.raises(ValueError, match="NEW_EXPORT"):
        exporter.export(tmp_path, target)


def test_secret_finding_returns_path_and_category_without_secret(tmp_path):
    exporter = module("repository_export")
    path = tmp_path / "src/credential.py"
    path.parent.mkdir()
    secret = "sk-proj-" + "Z" * 40
    path.write_text(secret)
    with pytest.raises(ValueError, match="CREDENTIAL_PATTERNS") as caught:
        exporter.inventory(tmp_path)
    assert "src/credential.py" in str(caught.value)
    assert secret not in str(caught.value)
    assert not (tmp_path / "artifacts/export").exists()


def test_new_runtime_never_overwrites_keys_or_accepts_path_traversal(tmp_path):
    runtime = module("team_runtime")
    existing = tmp_path / "artifacts/team-dev/used"
    existing.mkdir(parents=True)
    (existing / "do-not-touch").write_bytes(b"old-state")
    with pytest.raises(ValueError, match="PRESERVE_EXISTING"):
        runtime.prepare(tmp_path, "used")
    with pytest.raises(ValueError, match="INVALID_RUNTIME_NAME"):
        runtime.prepare(tmp_path, "../outside")
    assert (existing / "do-not-touch").read_bytes() == b"old-state"


def test_team_compose_keeps_provider_disabled_and_mounts_only_isolated_files():
    import yaml

    config = yaml.safe_load((ROOT / "compose.team.yaml").read_text())
    services = config["services"]
    env = services["control"]["environment"]
    assert env["HOOKGW_PDP"] == "JEV" and env["HOOKGW_JEV_PROFILE"] == "current_candidate_1"
    assert env["JEV_POLICY_FILE"] == "/not-mounted/policy.json"
    assert config["volumes"]["team-runtime"]["external"] is True
    assert "SOGAEDING_TEAM_VOLUME" in config["volumes"]["team-runtime"]["name"]
    assert not any(
        "jev-key" in str(value) or "runtime-mvp-demo" in str(value) for value in services.values()
    )
    assert any(
        isinstance(value, dict)
        and value.get("target") == "/files"
        and value.get("volume", {}).get("subpath", "").endswith("/workspace")
        for value in services["upstream"]["volumes"]
    )
    assert "./:/files" not in str(services["upstream"]["volumes"])
    assert services["gateway"]["ports"][0].startswith("127.0.0.1:")


def test_explicit_subnets_avoid_broad_and_narrow_existing_networks():
    runtime = module("team_runtime")
    before = [{"IPAM": {"Config": [{"Subnet": "10.253.0.0/23"}, {"Subnet": "172.18.0.0/16"}]}}]
    assert runtime.network_pair(before) == {
        "protected": "10.253.2.0/24",
        "ingress": "10.253.3.0/24",
    }
    assert len(before) == 1
    with pytest.raises(ValueError, match="PRESERVE_EXISTING"):
        runtime.network_pair([{"IPAM": {"Config": [{"Subnet": "10.0.0.0/8"}]}}])
