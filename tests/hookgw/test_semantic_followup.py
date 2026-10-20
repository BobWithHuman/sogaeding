"""Separate followup proposal, exact approvals, old state preservation; model0."""

import importlib.util
import json
import sqlite3
import subprocess
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_human_approval_programs_are_part_of_the_approved_public_source_binding():
    spec = importlib.util.spec_from_file_location("followup_binding_names", ROOT / "tools/mvp_semantic_followup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {"tools/mvp_confirm.py", "scripts/mvp_confirm.ps1"}.issubset(module.OWN_FILES)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("offline_semantic_followup", ROOT / "tools/mvp_semantic_followup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    b = module.base(ROOT)
    runtime = tmp_path / module.RELATIVE
    for name in ("revisions/host-wait-1", "episodes/events/episode-2", "ledger", "workspace/docs", "config", "host"):
        (runtime / name).mkdir(parents=True, exist_ok=True)
    for name in module.OWN_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixed public test source\n")
    source = tmp_path / "src/app/demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("# fixed application\n")
    (runtime / "workspace/docs/facts.md").write_text("Public synthetic deployment facts.")
    parent = {"revision": "host-wait-1", "image": "sha256:" + "a" * 64,
              "gateway_image": "gateway@sha256:" + "b" * 64,
              "source_documents": {"docs/facts.md": b.sha(runtime / "workspace/docs/facts.md")}}
    b.write_new(runtime / "revisions/host-wait-1/manifest.json", parent)
    monkeypatch.setattr(module, "PARENT_SHA", b.sha(runtime / "revisions/host-wait-1/manifest.json"))
    for index in (1, 2):
        b.write_new(runtime / "episodes" / f"episode-{index}.claim", {"episode": index, "status": "CLAIMED"})
    b.write_new(runtime / "episodes/events/episode-2/finish.json", {"event": "FINISHED", "episode": 2, "revision": "host-wait-1", "outcome": "EXITED", "tree_cleanup": "VERIFIED", "connection_closed": "VERIFIED"})
    b.write_new(runtime / "config/policy.json", b.policy(True))
    path = runtime / "ledger/typesafe-budget.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE jev_attempts(analysis_id TEXT,view TEXT,started REAL,status TEXT,input_reserved INTEGER,usage TEXT)")
        db.execute("CREATE TABLE jev_policy(singleton INTEGER,binding TEXT)")
        db.execute("INSERT INTO jev_policy VALUES(1,?)", (b.canonical({"request_limit": 8, "input_token_limit": 512000}),))
        db.executemany("INSERT INTO jev_attempts VALUES(?,?,?,?,?,?)", [(f"analysis-{i}", "A" if i % 2 == 0 else "B", float(i), "COMPLETED", 64000, None) for i in range(4)])
    calls, active = [], {"value": False}
    monkeypatch.setattr(module, "base", lambda _: b)
    monkeypatch.setattr(b, "verified", lambda *_, **__: parent)
    monkeypatch.setattr(b, "sources", lambda root: {"src/app/demo.py": b.sha(source)})
    monkeypatch.setattr(b, "image_id", lambda _: parent["image"])
    monkeypatch.setattr(b, "key_metadata", lambda _: {"host_body_read": False, "host_hash_read": False})
    monkeypatch.setattr(b, "provider_summary", lambda _: {"requests_attempted": 4, "input_reserved": 256000})
    monkeypatch.setattr(b, "cli_flags", lambda *_: ["ORIGINAL_READONLY_SANDBOX", "ORIGINAL_USER_REVIEWER", "ORIGINAL_HOOKS"])
    monkeypatch.setattr(b, "read_local", lambda *_: {"spec": "MVP-SPEC-5", "decision_policy": module.POLICY if active["value"] else "hookgw-2026-10-16-jev-v2", "judge_mode": "JEV_USER_LIVE", "demo_dispatch": "post_host_approval_v1"})
    monkeypatch.setenv("OPENAI_API_KEY", "FAKE-OFFLINE-ACTOR-KEY-NOT-USED")
    def lifecycle_run(argv, **kwargs):
        calls.append(("actor", argv, kwargs["wall_seconds"]))
        kwargs["event_sink"]({"event": "STARTING", "started_utc": "2026-10-17T00:00:00Z", "wall_seconds": 1800})
        assert kwargs["before_stop"]() is True
        result = {"event": "FINISHED", "started": True, "outcome": "EXITED", "exit_code": 0,
                  "tree_cleanup": "VERIFIED", "connection_closed": "VERIFIED"}
        kwargs["event_sink"](result)
        return result
    lifecycle = types.SimpleNamespace(run=lifecycle_run, utc=lambda: "2026-10-17T00:00:00Z")
    launcher = types.SimpleNamespace(check_conflicts=lambda *_, **__: None, check_manual_requirements=lambda: None)
    def send(host, endpoint, body, **kwargs):
        calls.append((endpoint,))
        return {"connection": "offline-connection"} if endpoint == "/connect" else {"state": "CLOSED"}
    def helper(root, name):
        return {"hookgw_bundle": types.SimpleNamespace(source_files=lambda _: {"src/app/demo.py": source}),
                "hookgw_launch": launcher, "hookgw_mcp_probe": types.SimpleNamespace(probe=lambda *_: {"ready": True, "tool_calls": 0}),
                "hookgw_hook": types.SimpleNamespace(send=send), "mvp_demo_lifecycle": lifecycle}[name]
    monkeypatch.setattr(b, "helper", helper)
    monkeypatch.setattr(b, "command", lambda args, *_, **__: subprocess.CompletedProcess(args, 0, "hooks stable true\n", ""))
    def compose(root, base, manifest, args, timeout=90):
        calls.append(("compose", args))
        if args[0] == "up":
            active["value"] = True
            return ""
        if args[0] == "exec":
            return json.dumps({"manifest": manifest["bundle_sha256"], "files_match": True})
        return "c" * 64
    monkeypatch.setattr(module, "compose", compose)
    original_command = b.command
    def command(args, *values, **kwargs):
        if "inspect" in args:
            return subprocess.CompletedProcess(args, 0, parent["image"] + "\n", "")
        return original_command(args, *values, **kwargs)
    monkeypatch.setattr(b, "docker", lambda _: "docker")
    monkeypatch.setattr(b, "command", command)
    # Gateway inspect needs its own digest; no real Docker process is launched.
    def checked(root, exe=None, model=None, *, activated=False):
        module.verified(root, allow_claimed=activated)
        return {"ready_for_user_start": True}
    module.offline_original_check = module.check
    monkeypatch.setattr(module, "check", checked)
    return module, b, tmp_path, runtime, calls, active


def approvals(module, b, root):
    return {"confirm_send": True, "manifest_sha256": b.sha(module.target(root, b) / "manifest.json"),
            "additional_starts": 1, "total_start_limit": 3, "requests": 8,
            "input_limit": 512000, "wall_seconds": 1800}


def test_prepare_only_new_public_bundle_no_restart_claim_or_budget_write(prepared):
    module, _b, root, runtime, calls, active = prepared
    old = {p.relative_to(runtime).as_posix(): p.read_bytes() for p in runtime.rglob("*") if p.is_file()}
    report = module.prepare(root)
    assert report["status"] == "PREPARED_NOT_DEPLOYED" and report["actual_model_calls"] == 0
    assert all((runtime / name).read_bytes() == value for name, value in old.items())
    assert not calls and active["value"] is False
    assert not (runtime / "episodes/episode-3.claim").exists()
    assert module.verified(root)[1]["parent"]["provider"]["requests_remaining"] == 4
    with pytest.raises(ValueError, match="EXISTS_PRESERVED"):
        module.prepare(root)


@pytest.mark.parametrize("field", ["confirm_send", "manifest_sha256", "additional_starts", "total_start_limit", "requests", "input_limit", "wall_seconds"])
def test_each_exact_user_approval_required_before_start(prepared, field):
    module, b, root, runtime, calls, _ = prepared
    module.prepare(root)
    values = approvals(module, b, root)
    values[field] = False if field == "confirm_send" else "0" * 64 if field == "manifest_sha256" else None
    with pytest.raises(ValueError):
        module.start(root, "fake-cli", "explicit-actor-model", **values)
    assert not calls and not (runtime / "episodes/episode-3.claim").exists()


@pytest.mark.parametrize("changed", ["source", "human_cli", "document", "parent", "claim", "finish", "ledger", "manifest", "bundle"])
def test_drift_preserves_proposal_and_prevents_start(prepared, changed):
    module, b, root, runtime, calls, _ = prepared
    module.prepare(root)
    values = approvals(module, b, root)
    directory = module.target(root, b)
    if changed == "ledger":
        with sqlite3.connect(runtime / "ledger/typesafe-budget.sqlite3") as db:
            db.execute("UPDATE jev_attempts SET status='UNKNOWN'")
    else:
        path = {"source": root / "src/app/demo.py", "human_cli": root / "tools/mvp_confirm.py", "document": runtime / "workspace/docs/facts.md",
                "parent": runtime / "revisions/host-wait-1/manifest.json", "claim": runtime / "episodes/episode-2.claim",
                "finish": runtime / "episodes/events/episode-2/finish.json", "manifest": directory / "manifest.json",
                "bundle": directory / "bundle/src/app/demo.py"}[changed]
        path.write_text("changed")
    with pytest.raises((ValueError, KeyError)):
        module.start(root, "fake-cli", "explicit-actor-model", **values)
    assert not calls and not (runtime / "episodes/episode-3.claim").exists()


def test_explicit_one_followup_uses_episode3_same_provider_budget_and_no_retry(prepared):
    module, b, root, runtime, calls, _ = prepared
    module.prepare(root)
    values = approvals(module, b, root)
    ledger_before = (runtime / "ledger/typesafe-budget.sqlite3").read_bytes()
    # Fake lifecycle is separate from real-model execution: this verifies gates.
    result = module.start(root, "fake-cli", "explicit-actor-model", **values)
    assert result["episode"] == 3 and result["started"] is True
    assert (runtime / "ledger/typesafe-budget.sqlite3").read_bytes() == ledger_before
    assert (runtime / "episodes/events/episode-3/finish.json").is_file()
    assert len([row for row in calls if row[0] == "actor"]) == 1
    assert ("/demo/close",) in calls
    assert "mcp_servers.with_human.tool_timeout_sec=720" in next(row for row in calls if row[0] == "actor")[1]
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        module.start(root, "fake-cli", "explicit-actor-model", **values)


def test_child_flags_add_only_explicit_tool_wait_to_inherited_controls(prepared):
    module, b, root, _, _, _ = prepared
    assert module.cli_flags(root, b, "actor") == ["ORIGINAL_READONLY_SANDBOX", "ORIGINAL_USER_REVIEWER", "ORIGINAL_HOOKS", "-c", "mcp_servers.with_human.tool_timeout_sec=720"]


def test_actual_check_only_features_metadata_and_keeps_old_service_running(prepared):
    module, _, root, _, calls, active = prepared
    module.prepare(root)
    report = module.offline_original_check(root, "fake-cli", "explicit-actor")
    assert report["status"] == "PREPARED_NOT_DEPLOYED" and report["ready_for_user_start"]
    assert report["running_policy"] == "hookgw-2026-10-16-jev-v2"
    assert not calls and active["value"] is False


def test_activation_failure_consumes_only_explicit_third_claim_without_retry(prepared, monkeypatch):
    module, b, root, runtime, calls, _ = prepared
    module.prepare(root)
    values = approvals(module, b, root)
    before = (runtime / "ledger/typesafe-budget.sqlite3").read_bytes()
    def fail(*_, **__):
        raise ValueError("OFFLINE_FORCED_ACTIVATION_FAILURE")
    monkeypatch.setattr(module, "compose", fail)
    result = module.start(root, "fake-cli", "explicit-actor", **values)
    assert result["started"] is False and result["actor_result"]["outcome"] == "LAUNCH_FAILED"
    assert (runtime / "episodes/episode-3.claim").is_file()
    assert (runtime / "episodes/events/episode-3/finish.json").is_file()
    assert (runtime / "ledger/typesafe-budget.sqlite3").read_bytes() == before
    assert not calls
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        module.start(root, "fake-cli", "explicit-actor", **values)


def test_unverified_old_child_cleanup_blocks_preparation(prepared):
    module, b, root, runtime, calls, _ = prepared
    finish = runtime / "episodes/events/episode-2/finish.json"
    value = json.loads(finish.read_text())
    value["connection_closed"] = "UNVERIFIED"
    finish.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="PREVIOUS_ACTOR_NOT_FINISHED"):
        module.prepare(root)
    assert not calls and not module.target(root, b).exists()


def test_manifest_changed_during_check_rejected_before_claim(prepared, monkeypatch):
    module, b, root, runtime, calls, _ = prepared
    module.prepare(root)
    values = approvals(module, b, root)
    path = module.target(root, b) / "manifest.json"
    def changed(*_, **__):
        value = json.loads(path.read_text())
        value["unapproved_note"] = "changed after user approval"
        path.write_text(json.dumps(value))
        return {"ready_for_user_start": True}
    monkeypatch.setattr(module, "check", changed)
    with pytest.raises(ValueError, match="APPROVAL_BINDING_CHANGED"):
        module.start(root, "fake-cli", "explicit-actor", **values)
    assert not calls and not (runtime / "episodes/episode-3.claim").exists()
