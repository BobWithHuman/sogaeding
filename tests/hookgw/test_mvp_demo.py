"""Demo helper fixture boundaries. No actual key, provider, CLI model or Docker."""
import importlib.util
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("test_mvp_demo_helper", PROJECT / "tools/mvp_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    module = load()
    root = tmp_path / "project"
    root.mkdir()
    for name in ("tools", "src/app", "docs/mvp/contracts", "fixtures/mvp_demo", "scripts", "agentgateway"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for name in ("prepare_tls", "hookgw_launch", "hookgw_hook", "hookgw_mcp", "hookgw_mcp_probe", "hookgw_bundle", "jev_eval", "mvp_demo", "mvp_demo_lifecycle", "mvp_demo_hook", "mvp_demo_mcp"):
        shutil.copyfile(PROJECT / "tools" / (name + ".py"), root / "tools" / (name + ".py"))
    shutil.copyfile(PROJECT / "scripts/mvp_demo.ps1", root / "scripts/mvp_demo.ps1")
    shutil.copyfile(PROJECT / "compose.mvp-demo.yaml", root / "compose.mvp-demo.yaml")
    shutil.copyfile(PROJECT / "compose.mvp-demo.host-wait-1.yaml", root / "compose.mvp-demo.host-wait-1.yaml")
    shutil.copyfile(PROJECT / "agentgateway/config.yaml", root / "agentgateway/config.yaml")
    shutil.copytree(PROJECT / "fixtures/mvp_demo", root / "fixtures/mvp_demo", dirs_exist_ok=True)
    (root / "src/app/fake.py").write_text("# public fake frozen product\n")
    (root / "src/app/transparent").mkdir()
    (root / "src/app/transparent/jev_policy.py").write_text("# fixture\n")
    (root / "docs/mvp/contracts/spec5.json").write_text("{}")
    key = root / "artifacts/runtime-jev-eval/key/jev.api-key"
    key.parent.mkdir(parents=True)
    key.write_text("PUBLIC-FAKE-ROLE-KEY")
    old = root / "artifacts/runtime-jev-eval/old.sqlite3"
    old.write_bytes(b"PUBLIC-OLD-DB-UNCHANGED")
    calls = []
    real_helper = module.helper

    def helper(project, name):
        if name == "jev_eval":
            return SimpleNamespace(private_ready=lambda _: True, image_id=lambda _: "sha256:" + "a"*64,
                                   trusted_docker=lambda _: "/trusted/docker", protect=lambda *_: None,
                                   ledger_summary=lambda _: {"attempts": 1, "input_reserved": 64000})
        if name == "hookgw_mcp_probe":
            return SimpleNamespace(probe=lambda *_: {"ready": True, "connection_cleanup": "REMOVED_UNBOUND_CONNECTION"})
        return real_helper(project, name)

    def command(args, timeout=30, env=None):
        calls.append(args)
        if "inspect" in args:
            return SimpleNamespace(returncode=0, stdout="sha256:" + ("b"*64 if "b"*64 in args else "a"*64), stderr="")
        if "run" in args:
            pki = module.runtime(root) / "pki"
            pki.mkdir()
            for name in ("ca.pem", "control.pem", "control.key", "storage.key", "human.token", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key", "upstream.pem", "upstream.key"):
                (pki / name).write_text("PUBLIC-FAKE-CREDENTIAL-" + name)
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    def compose(_, args, image=None, timeout=60):
        calls.append(args)
        if args[:2] == ["ps", "-q"]:
            return "b"*64 if args[-1] == "agentgateway" else "a"*64
        if args[:3] == ["exec", "-T", "upstream"] and "GROUP BY" in args[-1]:
            return json.dumps({"attempts": 0, "observed": 0, "unknown": 0, "receipt": "NOT_ATOMIC_FILE_RECEIPT"})
        if args[:2] == ["exec", "-T"]:
            return json.dumps({"manifest": module.sha(module.runtime(root) / "bundle/manifest.json"), "files_match": True})
        return ""

    monkeypatch.setattr(module, "helper", helper)
    monkeypatch.setattr(module, "command", command)
    monkeypatch.setattr(module, "compose", compose)
    monkeypatch.setattr(module, "read_local", lambda *_, **__: {"spec": "MVP-SPEC-5", "decision_policy": "hookgw-2026-10-16-jev-v2", "demo_dispatch": "post_host_approval_v1", "judge_mode": "JEV_USER_LIVE" if json.loads((module.runtime(root)/"config/policy.json").read_text())["enabled"] else "JEV_RULES_ONLY"})
    module.GATEWAY = "fixture-agentgateway@sha256:" + "b"*64
    report = module.prepare(root)
    return module, root, report, calls, old


def test_prepare_disabled_separate_mounts_and_no_old_mutation(prepared):
    module, root, report, calls, old = prepared
    target = module.runtime(root)
    assert report["paid_requests"] == 0
    assert json.loads((target / "config/policy.json").read_text())["enabled"] is False
    assert not list((target / "ledger").iterdir())
    assert not list((target / "episodes").iterdir())
    assert old.read_bytes() == b"PUBLIC-OLD-DB-UNCHANGED"
    assert json.loads((target / "control/grant.json").read_text())["demo_scope"] == "SYNTHETIC_REGISTERED_MCP"
    assert "--network" in calls[0] and calls[0][calls[0].index("--network") + 1] == "none"
    assert (target / "upstream/upstream.pem").exists()
    assert module.inspect_demo(root)["manifest_sha256"] == report["manifest_sha256"]
    with pytest.raises(ValueError, match="EXISTS_PRESERVED"):
        module.prepare(root)


@pytest.mark.parametrize("field", ["confirm_send", "manifest_sha256", "requests", "input_reservation", "actor_episodes"])
def test_each_live_approval_required_before_actor_or_policy_change(prepared, field):
    module, root, report, _, _ = prepared
    values = dict(confirm_send=True, manifest_sha256=report["manifest_sha256"], requests=8, input_reservation=512000, actor_episodes=2)
    values[field] = None
    with pytest.raises(ValueError):
        module.start(root, "fake-cli", "fake-model", **values)
    assert module.episode_count(root) == 0
    assert json.loads((module.runtime(root)/"config/policy.json").read_text())["enabled"] is False


@pytest.mark.parametrize("field,value", [("requests", True), ("requests", 9), ("input_reservation", 512001), ("actor_episodes", 3)])
def test_wrong_limits_rejected(prepared, field, value):
    module, root, report, _, _ = prepared
    values = dict(confirm_send=True, manifest_sha256=report["manifest_sha256"], requests=8, input_reservation=512000, actor_episodes=2)
    values[field] = value
    with pytest.raises(ValueError):
        module.start(root, "fake-cli", "fake-model", **values)


def test_check_model0_no_actor_and_source_drift_fails(prepared):
    module, root, _, _, _ = prepared
    assert module.check(root, cli=False)["ready"]
    (root / "scripts/mvp_demo.ps1").write_text("# changed\n")
    with pytest.raises(ValueError, match="DRIFT"):
        module.check(root, cli=False)
    assert module.episode_count(root) == 0


def test_two_atomic_episode_claims_only_and_timeout_retains(prepared):
    module, root, report, _, _ = prepared
    def attempt(_):
        try:
            return module.claim_episode(root, report["manifest_sha256"], "public-fake-model")
        except ValueError:
            return "DENIED"
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(attempt, range(8)))
    assert sorted(v for v in values if isinstance(v, int)) == [1, 2]
    assert values.count("DENIED") == 6
    assert module.episode_count(root) == 2


def test_start_fake_cli_only_after_all_gates_and_inherited_terminal(prepared, monkeypatch):
    module, root, report, calls, old = prepared
    target = module.runtime(root)
    original_helper = module.helper
    launcher = SimpleNamespace(overrides=lambda *_: ["HOOKS"], api_overrides=lambda _: ["API"], manual_review_overrides=lambda: ["USER_REVIEW"])
    def helper(project, name):
        if name == "hookgw_launch":
            return launcher
        if name == "hookgw_hook":
            return SimpleNamespace(send=lambda *_: {"connection": "PUBLIC-FAKE-CONNECTION"})
        if name == "mvp_demo_lifecycle":
            return SimpleNamespace(utc=lambda: "2026-10-16T00:00:00+00:00", run=run)
        return original_helper(project, name)
    monkeypatch.setattr(module, "helper", helper)
    monkeypatch.setattr(module, "check", lambda *_: {"ready": True})
    monkeypatch.setattr(module, "wait_health", lambda *_: None)
    executions = []
    def run(argv, **kwargs):
        executions.append((argv, kwargs))
        kwargs["event_sink"]({"event": "STARTING", "started_utc": "2026-10-16T00:00:00+00:00", "wall_seconds": kwargs["wall_seconds"]})
        result = {"event": "FINISHED", "outcome": "EXITED", "exit_code": 0, "started": True, "tree_cleanup": "VERIFIED", "connection_closed": "NOT_APPLICABLE"}
        kwargs["event_sink"](result)
        return result
    value = module.start(root, "fake-cli", "fake-model", True, report["manifest_sha256"], 8, 512000, 2)
    assert value["started"] and value["episode"] == 1
    argv, options = executions[0]
    assert argv == ["fake-cli", "HOOKS", "API", "-c", "project_doc_max_bytes=0", "USER_REVIEW"]
    assert options["cwd"] == target / "workspace" and options["wall_seconds"] == 180
    assert "stdout" not in options and "stderr" not in options and "capture_output" not in options
    assert options["env"]["WITH_HUMAN_CONNECTION"] == "PUBLIC-FAKE-CONNECTION"
    assert old.read_bytes() == b"PUBLIC-OLD-DB-UNCHANGED"
    assert any("--force-recreate" in args for args in calls)


def test_history_readonly_endpoint_file_effect_and_no_attack_inference(prepared, monkeypatch):
    module, root, _, _, _ = prepared
    target = module.runtime(root)
    report_file = target / "workspace/reports/normal.md"
    report_file.write_text("Public synthetic summary\n", encoding="utf-8")
    seen = []
    def read(host, endpoint, human=False):
        seen.append((endpoint, human))
        return {"calls": [], "scope": "REGISTERED_SYNTHETIC_MCP_ONLY"}
    monkeypatch.setattr(module, "read_local", read)
    value = module.history(root)
    assert seen == [("/demo/history", True)]
    assert value["effects"][0]["sha256"] == module.sha(report_file)
    assert value["effects"][1]["exists"] is False
    assert value["upstream"]["attempts"] == 0
    assert "NO_ATTEMPT_IS_NOT_PASS" in value["attack_status"]
    assert not list((target / "ledger").iterdir())


def test_symlink_effect_or_source_rejected_before_read(prepared, tmp_path):
    module, root, _, _, _ = prepared
    secret = tmp_path / "outside-public-fake-key"
    secret.write_text("PUBLIC-CANARY")
    effect = module.runtime(root) / "workspace/reports/normal.md"
    try:
        effect.symlink_to(secret)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        module.effects(root)
    source = root / "tools/jev_eval.py"
    source.unlink()
    source.symlink_to(secret)
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        module.sources(root)


def test_compose_role_mounts_no_old_database_or_openai_judge():
    text = (PROJECT / "compose.mvp-demo.yaml").read_text()
    assert "runtime-jev-eval/key:/jev-key:ro" in text
    assert "runtime-mvp-demo/ledger:/jev-budget" in text
    assert "runtime-hookgw" not in text and "legacy-budget" not in text
    assert "OPENAI_API_KEY" not in text
    assert "127.0.0.1:8034:8030" in text and "127.0.0.1:8044:8040" in text
    assert "pull_policy: never" in text


def test_unlisted_bundle_shadow_and_old_policy_health_rejected(prepared, monkeypatch):
    module, root, _, _, _ = prepared
    extra = module.runtime(root) / "bundle/json.py"
    extra.write_text("# forbidden unlisted shadow\n")
    with pytest.raises(ValueError, match="BUNDLE_INVALID"):
        module.verified(root)
    extra.unlink()
    monkeypatch.setattr(module, "read_local", lambda *_: {"spec": "MVP-SPEC-5", "judge_mode": "JEV_RULES_ONLY", "decision_policy": "hookgw-2026-10-16-jev-v1"})
    report = module.check(root, cli=False)
    assert not report["ready"] and "DEMO_HEALTH_INVALID" in report["issues"]


def test_wrong_actual_container_image_rejected(prepared, monkeypatch):
    module, root, _, _, _ = prepared
    monkeypatch.setattr(module, "command", lambda *_: SimpleNamespace(returncode=0, stdout="sha256:" + "c"*64, stderr=""))
    report = module.check(root, cli=False)
    assert not report["ready"] and "DEMO_CONTAINER_IMAGE_UNVERIFIED" in report["issues"]


def test_metadata_key_never_opened_and_failed_activation_retains_claim(prepared, monkeypatch):
    module, root, report, _, _ = prepared
    key = root / "artifacts/runtime-jev-eval/key/jev.api-key"
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        if path == key:
            raise AssertionError("No key body read authorized")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    assert module.key_metadata(root)["host_body_read"] is False
    monkeypatch.setattr(module, "check", lambda *_: {"ready": True})
    def unavailable(*_args, **_kwargs):
        raise ValueError("DEMO_COMPOSE_FAILED")
    monkeypatch.setattr(module, "compose", unavailable)
    result = module.start(root, "fake-cli", "fake-model", True, report["manifest_sha256"], 8, 512000, 2)
    assert result["actor_result"]["outcome"] == "LAUNCH_FAILED" and result["started"] is False
    assert module.episode_count(root) == 1
    assert not list((module.runtime(root) / "ledger").iterdir())


def prepare_revision(prepared, monkeypatch):
    module, root, report, _, _ = prepared
    module.claim_episode(root, report["manifest_sha256"], "public-fake-model")
    monkeypatch.setattr(module, "PARENT_SHA", report["manifest_sha256"])
    return module.revise(root, "host-wait-1", True)


def test_revision_preserves_parent_budget_claims_and_fixed_single_slot(prepared, monkeypatch):
    module, root, report, _, old = prepared
    parent = (module.runtime(root)/"manifest.json").read_bytes()
    result = prepare_revision(prepared, monkeypatch)
    assert result["remaining_episode_claims"] == 1 and result["paid_requests"] == 0
    assert (module.runtime(root)/"manifest.json").read_bytes() == parent
    assert (module.revision_path(root)/"parent-manifest.json").read_bytes() == parent
    assert old.read_bytes() == b"PUBLIC-OLD-DB-UNCHANGED" and not list((module.runtime(root)/"ledger").iterdir())
    assert module.verified(root)["limits"]["episode_seconds"] == 1800
    assert module.check(root, cli=False)["ready"]
    assert module.actor_events(root)[0]["outcome"] == "EXIT_STATUS_UNKNOWN"
    assert "started" not in module.actor_events(root)[0]
    assert report["manifest_sha256"] != result["manifest_sha256"]
    with pytest.raises(ValueError, match="EXISTS_PRESERVED"):
        module.revise(root, "host-wait-1", True)
    with pytest.raises(ValueError, match="EXPLICIT"):
        module.revise(root, "unassigned", True)


@pytest.mark.parametrize("revision,wall", [(None, None), ("host-wait-1", None), (None, 1800), ("host-wait-1", 180), ("host-wait-1", True), ("host-wait-1", 1801)])
def test_new_wall_requires_exact_user_opt_in(prepared, monkeypatch, revision, wall):
    module, root, _, _, _ = prepared
    report = prepare_revision(prepared, monkeypatch)
    with pytest.raises(ValueError, match="EXPLICIT_WALL"):
        module.start(root, "fake-cli", "fake-model", True, report["manifest_sha256"], 8, 512000, 2, revision, wall)
    assert module.episode_count(root) == 1


def test_revision_parent_claim_tamper_and_old_manifest_replay_fail_closed(prepared, monkeypatch):
    module, root, report, _, _ = prepared
    new = prepare_revision(prepared, monkeypatch)
    with pytest.raises(ValueError, match="EXACT_MANIFEST"):
        module.start(root, "fake-cli", "fake-model", True, report["manifest_sha256"], 8, 512000, 2, "host-wait-1", 1800)
    assert new["manifest_sha256"] != report["manifest_sha256"]
    (module.runtime(root)/"episodes/episode-1.claim").write_text("{}")
    with pytest.raises(ValueError, match="PARENT_CHANGED"):
        module.verified(root)


def test_actor_events_are_append_only_and_starting_without_finish_is_unknown(prepared):
    module, root, report, _, _ = prepared
    module.claim_episode(root, report["manifest_sha256"], "public-fake-model")
    sink = module.actor_sink(root, 1, None, report["manifest_sha256"])
    sink({"event": "STARTING", "started_utc": "2026-10-16T00:00:00+00:00", "wall_seconds": 180})
    rows = module.actor_events(root)
    assert rows[-1]["outcome"] == "EXIT_STATUS_UNKNOWN" and "started" not in rows[-1]
    with pytest.raises(FileExistsError):
        sink({"event": "STARTING"})
    sink({"event": "FINISHED", "outcome": "TIMEOUT", "exit_code": None, "started": True, "tree_cleanup": "VERIFIED"})
    assert module.actor_events(root)[-1]["outcome"] == "TIMEOUT"
    with pytest.raises(FileExistsError):
        sink({"event": "FINISHED"})
