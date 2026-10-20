"""V5 demo wiring and opt-in boundaries. No model, credentials or real CLI."""
import copy
import importlib.util
import json
import shutil

import pytest
import test_mvp_demo as legacy

PROJECT = legacy.PROJECT


def followup():
    spec = importlib.util.spec_from_file_location("behavior_followup", PROJECT / "tools/mvp_semantic_followup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def legacy_prepared(tmp_path, monkeypatch):
    return legacy.prepared.__wrapped__(tmp_path, monkeypatch)


@pytest.fixture
def behavior(legacy_prepared, monkeypatch):
    b, root, _, calls, old = legacy_prepared
    f = followup()
    for name in ("tools/mvp_semantic_followup.py", "tools/mvp_confirm.py", "scripts/mvp_confirm.ps1", "compose.mvp-demo.behavior-v5-1.yaml"):
        shutil.copyfile(PROJECT / name, root / name)
    original_compose = b.compose
    monkeypatch.setattr(f, "base", lambda _: b)
    parent = {"historical_requests": 21, "historical_input_reserved": 1344000, "historical_cli_starts": 3}
    monkeypatch.setattr(f, "behavior_parent", lambda *_: copy.deepcopy(parent))
    monkeypatch.setattr(f, "behavior_compose", lambda project, base, args, image=None, timeout=60: original_compose(project, args, image, timeout))
    configured = f.behavior_base(root)
    monkeypatch.setattr(f, "behavior_base", lambda _: configured)
    monkeypatch.setattr(b, "read_local", lambda *_, **__: {"spec": "MVP-SPEC-5", "decision_policy": f.BEHAVIOR_POLICY,
        "demo_dispatch": "post_host_approval_v1", "judge_mode": "JEV_USER_LIVE" if json.loads((b.runtime(root) / "config/policy.json").read_text())["enabled"] else "JEV_RULES_ONLY"})
    report = f.behavior_prepare(root)
    return f, b, root, report, parent, calls, old


def test_disabled_revision_uses_existing_launcher_and_preserves_old_runtime(behavior):
    f, b, root, report, _, calls, old = behavior
    assert report["status"] == "DEMO_PREPARED" and report["paid_requests"] == 0
    assert old.read_bytes() == b"PUBLIC-OLD-DB-UNCHANGED"
    assert (root / "artifacts/runtime-mvp-demo/manifest.json").exists()
    directory = b.runtime(root)
    assert directory == root / f.BEHAVIOR_RELATIVE
    assert json.loads((directory / "config/policy.json").read_text()) == {
        "enabled": False, "model": b.MODEL, "request_limit": 4, "input_token_limit": 256000, "policy_id": "mvp-demo-behavior-v5-1"}
    assert not (directory / "ledger/typesafe-budget.sqlite3").exists()
    assert not (directory / "episodes/episode-4.claim").exists()
    profile = json.loads((directory / "host/profile.json").read_text())
    assert profile["control_url"].endswith(":8036") and profile["gateway_url"].endswith(":8046/mcp")
    assert b.verified(root)["limits"] == {"requests": 4, "input_reservation": 256000, "actor_episodes": 1, "episode_seconds": 1800}
    with pytest.raises(ValueError, match="NO_OVERWRITE"):
        f.behavior_prepare(root)
    assert not any("api.typesafe" in str(call) for call in calls)


@pytest.mark.parametrize("change", ["source", "grant", "profile", "document", "parent", "image", "bundle"])
def test_changed_dependency_rejected_before_cli(behavior, monkeypatch, change):
    f, b, root, _, parent, _, _ = behavior
    directory = b.runtime(root)
    paths = {"source": root / "src/app/fake.py", "grant": directory / "control/grant.json", "profile": directory / "host/profile.json",
             "document": directory / "workspace/docs/release.md", "bundle": directory / "bundle/manifest.json"}
    if change in paths:
        paths[change].write_text("modified")
    elif change == "parent":
        parent["historical_requests"] = 22
    else:
        monkeypatch.setattr(b, "image_id", lambda _: "sha256:" + "b" * 64)
    with pytest.raises(ValueError):
        b.verified(root)
    assert not (directory / "episodes/episode-4.claim").exists()


APPROVALS = dict(confirm_send=True, requests=4, input_limit=256000, additional_starts=1, total_starts=4,
                 cumulative_requests=25, cumulative_input=1600000, demo_requests=20, demo_input=1280000, wall_seconds=1800)


@pytest.mark.parametrize("field", list(APPROVALS))
@pytest.mark.parametrize("bad", [None, True, 5.0])
def test_exact_additional_cumulative_limits_required(behavior, monkeypatch, field, bad):
    f, b, root, report, _, _, _ = behavior
    if field == "confirm_send" and bad is True:
        return
    starts = []
    monkeypatch.setattr(b, "start", lambda *args: starts.append(args))
    with pytest.raises(ValueError, match="APPROVALS_REQUIRED"):
        f.behavior_start(root, "fake-codex", "explicit-model", manifest_sha256=report["manifest_sha256"], **{**APPROVALS, field: bad})
    assert not starts


def test_exact_start_reuses_actor_and_refuses_any_consumed_ledger(behavior, monkeypatch):
    f, b, root, report, _, _, _ = behavior
    starts = []
    monkeypatch.setattr(b, "start", lambda *args: starts.append(args) or {"started": False})
    f.behavior_start(root, "fake-codex", "explicit-model", manifest_sha256=report["manifest_sha256"], **APPROVALS)
    assert starts[0][-2:] == (f.BEHAVIOR_REVISION, 1800)
    (b.runtime(root) / "ledger/typesafe-budget.sqlite3").write_bytes(b"interrupted consumed fixture")
    with pytest.raises(ValueError, match="CONSUMED"):
        f.behavior_start(root, "fake-codex", "explicit-model", manifest_sha256=report["manifest_sha256"], **APPROVALS)
    assert len(starts) == 1


@pytest.mark.parametrize("change", ["manifest_float", "config_float"])
def test_nested_limits_and_disabled_config_keep_strict_integer_types(behavior, change):
    _, b, root, _, _, _, _ = behavior
    directory = b.runtime(root)
    path = directory / ("manifest.json" if change == "manifest_float" else "config/policy.json")
    value = json.loads(path.read_text())
    if change == "manifest_float":
        value["limits"]["requests"] = 4.0
    else:
        value["request_limit"] = 4.0
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        b.verified(root)


@pytest.mark.parametrize("profile,expected", [("legacy_v2", "JevPolicy"), ("semantic_confirm_v3", "JevPolicyV3"), ("behavior_v5", "JevPolicyV5")])
def test_server_explicit_profiles_use_standard_client_without_model(tmp_path, monkeypatch, profile, expected):
    from app.transparent import server
    (tmp_path / "grant.json").write_text("{}")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"enabled": False, "model": "jev-1.13.0", "request_limit": None, "input_token_limit": None, "policy_id": None}))
    monkeypatch.setattr(server, "RUNTIME", tmp_path)
    monkeypatch.setattr(server, "secret", lambda _: "fixture")
    monkeypatch.setenv("HOOKGW_PDP", "JEV")
    monkeypatch.setenv("HOOKGW_JEV_PROFILE", profile)
    monkeypatch.setenv("JEV_POLICY_FILE", str(policy))
    class Done(Exception):
        pass
    def capture(*args, **kwargs):
        router = kwargs["policy_router"]
        assert type(router).__name__ == expected
        assert type(router.client).__name__ == "JevClient"
        assert not router.client.settings.authorized()
        raise Done()
    monkeypatch.setattr(server, "Engine", capture)
    with pytest.raises(Done):
        server.main()


def test_viewer_v5_human_and_risk_choices_remain_bounded():
    spec = importlib.util.spec_from_file_location("v5_viewer", PROJECT / "tools/mvp_demo_viewer.py")
    viewer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viewer)
    report = {"mode": "OFFLINE_REPLAY", "episodes": {"claimed": 4, "max": 4}, "history": {"calls": [
        {"tool": "write_file", "target": "reports/normal.md", "decision": "CONFIRM", "state": "OBSERVED", "policy": "hookgw-2026-10-17-jev-v5",
         "confirmation": "HUMAN_APPROVAL_CONSUMED", "payload_excerpt": "<script>alert(1)</script>",
         "policy_trace": {"view_observations": {"B": [{"question": "behavior", "choice": "LEGITIMATE", "effective_confidence": 1., "status": "ACCEPTED"}]}}}]}}
    rendered = viewer.render(report)
    assert "HUMAN_CONFIRMED" in rendered["text"] and "jev-v5" in rendered["text"]
    assert "LEGITIMATE" in rendered["text"] and "4/4" in rendered["text"]
    assert "<script>" not in rendered["html"]
