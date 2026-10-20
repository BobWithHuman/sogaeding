"""One explicitly approved followup: host gates -> fake Docker -> real fake-HTTP worker."""

import asyncio
import json
import shutil
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_jev_followup import failed_run

pytest_plugins = ["test_jev_eval"]


@pytest.fixture
def executable(prepared, monkeypatch):
    module, root, prior, calls = failed_run(prepared)
    (root / "scripts").mkdir()
    shutil.copyfile(module.ROOT / "scripts/jev_eval.ps1", root / "scripts/jev_eval.ps1")
    (prior / "key/jev.api-key").write_text("fake-only-followup-provider-key")
    monkeypatch.setattr(module, "private_ready", lambda *_: True)
    plan = module.build_plan(module.ROOT / "fixtures/jev/smoke.json")
    provider_calls, commands = [], []
    mode = {"value": "normal"}
    def response(request):
        provider_calls.append(request)
        if mode["value"] == "api_failure":
            return httpx.Response(401, text="PRIVATE_BODY_NEVER_RECORD")
        if mode["value"] == "bad_partial":
            return httpx.Response(200, json={"model": module.MODEL, "answers": {}, "usage": {"input_tokens": 321, "output_tokens": None}})
        wire = json.loads(request.content)
        state, questions = wire["state"], wire["questions"]
        ext = [item["key"] for item in state["evidence"] if item["origin"] == "TOOL_DATA"]
        attack = ext and "거짓" in state["contexts"][0]
        answers = {}
        for name, question in questions.items():
            chosen = "DIRECT"
            if name == "external_use":
                chosen = "NEW_INSTRUCTION" if attack else "TASK_DATA"
            elif name == "task_evidence":
                chosen = next(item["key"] for item in state["evidence"] if item["origin"] == "USER")
            elif name == "external_evidence":
                chosen = ext[0] if ext else "NONE"
            elif name.startswith("link_"):
                chosen = ext[0] if ext and name == "link_payload" else "NONE"
            elif name.startswith("context_"):
                chosen = "RECOMMENDATION" if attack else "DATA"
            answers[name] = {"type": "choice", "choice": chosen, "probabilities": {opt: float(opt == chosen) for opt in question["criteria"]}, "confidence": 1}
        return httpx.Response(200, json={"model": module.MODEL, "answers": answers, "usage": {"input_tokens": 200, "output_tokens": 40}})
    def docker(args, **kwargs):
        commands.append(args)
        if args[-1] == "_plan":
            result = plan
        elif args[-1] == "_preflight":
            result = {"paid_requests": 0, "default_enabled": False, "ready_for_user_opt_in": True, "actual_key_read": False}
        else:
            if mode["value"] == "start_failure":
                raise subprocess.TimeoutExpired("fake-docker", 100)
            target = module.followup_location(root, module.FOLLOWUP_RUN_ID)
            config = json.loads((target / "config/authorized-run.json").read_text())
            result = asyncio.run(module.worker_evaluate(plan, config, prior / "key/jev.api-key", target / "ledger/typesafe-budget.sqlite3", target / "results/result.json", transport=httpx.MockTransport(response)))
        return subprocess.CompletedProcess(args, 0, json.dumps(result), "")
    monkeypatch.setattr(module.subprocess, "run", docker)
    record = module.followup_prepare(root, module.FOLLOWUP_RUN_ID, True)
    approvals = dict(confirm_send=True, manifest_sha256=record["manifest_sha256"], request_limit=4, input_limit=256000,
                     cumulative_requests=5, cumulative_input=320000, additional_requests=1, additional_input=64000)
    return module, root, prior, approvals, provider_calls, commands, mode


def test_selected_run_whole_pipeline_normal_attack_and_parent_preserved(executable):
    module, root, prior, approvals, providers, commands, _ = executable
    before = {p.relative_to(prior).as_posix(): p.read_bytes() for p in prior.rglob("*") if p.is_file()}
    inspection = module.followup_inspect(root, module.FOLLOWUP_RUN_ID)
    assert inspection["manifest_sha256"] == approvals["manifest_sha256"]
    assert "scripts/jev_eval.ps1" in inspection["manifest"]["source_hashes"]
    assert module.followup_preflight(root, module.FOLLOWUP_RUN_ID)["live_authorized"] is False
    record = module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
    assert len(providers) == 4 and record["execution_exit"] == 0
    assert record["semantic_summary"]["outcome"] == "COMPLETE_OBSERVATIONS_MATCH_SMOKE_ONLY"
    assert [row["decision"] for row in record["result"]["result"]["results"]] == ["ALLOW", "DENY"]
    assert record["result"]["usage"]["input_reserved"] == 256000
    assert before == {p.relative_to(prior).as_posix(): p.read_bytes() for p in prior.rglob("*") if p.is_file()}
    actual = commands[-1]
    assert any(str(prior / "key") in arg and "target=/jev-key,readonly" in arg for arg in actual)
    assert not any(str(prior / "ledger") in arg for arg in actual)
    assert "bridge" in actual and "--read-only" in actual
    with pytest.raises(ValueError, match="CLAIMED"):
        module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
    assert len(providers) == 4
    assert module.collect(root)["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"


@pytest.mark.parametrize("field", ["confirm_send", "manifest_sha256", "request_limit", "input_limit", "cumulative_requests", "cumulative_input", "additional_requests", "additional_input"])
def test_exact_run_manifest_and_all_six_caps_required(executable, field):
    module, root, _, approvals, providers, _, _ = executable
    values = {**approvals, field: False if field == "confirm_send" else "0" * 64 if field == "manifest_sha256" else None}
    with pytest.raises(ValueError, match="APPROVAL_REQUIRED"):
        module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **values)
    assert not providers and not (module.followup_location(root, module.FOLLOWUP_RUN_ID) / "execution.claim").exists()


@pytest.mark.parametrize("changed", ["source", "wrapper", "wire", "image", "parent"])
def test_changed_bindings_prevent_any_followup_provider_request(executable, monkeypatch, changed):
    module, root, prior, approvals, providers, _, _ = executable
    target = module.followup_location(root, module.FOLLOWUP_RUN_ID)
    if changed == "source":
        (root / "src/changed.py").write_text("# changed")
    elif changed == "wrapper":
        (root / "scripts/jev_eval.ps1").write_text("# changed")
    elif changed == "wire":
        (target / "plan/requests.json").write_text("{}")
    elif changed == "image":
        monkeypatch.setattr(module, "image_id", lambda _: "sha256:" + "b" * 64)
    else:
        with sqlite3.connect(prior / "ledger/typesafe-budget.sqlite3") as db:
            db.execute("UPDATE jev_attempts SET status='CANCELLED'")
    with pytest.raises(ValueError):
        module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
    assert not providers


@pytest.mark.parametrize("mode", ["api_failure", "bad_partial"])
def test_failure_collect_has_safe_diagnostics_partial_usage_and_no_retry(executable, mode):
    module, root, _, approvals, providers, _, state = executable
    state["value"] = mode
    report = module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
    assert len(providers) == 1 and "PRIVATE_" not in json.dumps(report)
    assert report["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"
    assert report["semantic_summary"]["not_attempted_candidates"] == 1
    assert report["result"]["usage"]["input_reserved"] == 64000
    if mode == "bad_partial":
        assert report["result"]["usage"]["actual_input_tokens"] == 321
        assert report["result"]["usage"]["estimated_total_charge_usd_before_tax"] is None


def test_atomic_competing_execution_and_interrupted_claim_are_not_retried(executable):
    module, root, _, approvals, providers, commands, state = executable
    state["value"] = "start_failure"
    def execute(_):
        try:
            module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
            return "unexpected"
        except (ValueError, FileExistsError, subprocess.TimeoutExpired):
            return "stopped"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(execute, range(2))) == ["stopped", "stopped"]
    target = module.followup_location(root, module.FOLLOWUP_RUN_ID)
    assert (target / "execution.claim").is_file() and not providers
    assert sum(command[-1] == "_evaluate" for command in commands) == 1
    collected = module.followup_collect(root, module.FOLLOWUP_RUN_ID)
    assert collected["execution_status"] == "ATTEMPT_CLAIMED_OR_INTERRUPTED"
    assert collected["provider_attempts_status"] == "UNKNOWN_RECONCILIATION_REQUIRED"
    assert collected["semantic_summary"]["outcome"] == "EXECUTION_STATUS_UNKNOWN"
    with pytest.raises(ValueError, match="CLAIMED"):
        module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)


def test_fixed_slot_only_and_disabled_proposal_cannot_be_promoted(prepared, monkeypatch):
    module, root, prior, _ = failed_run(prepared)
    (root / "scripts").mkdir()
    shutil.copyfile(module.ROOT / "scripts/jev_eval.ps1", root / "scripts/jev_eval.ps1")
    monkeypatch.setattr(module, "private_ready", lambda *_: True)
    with pytest.raises(ValueError, match="SINGLE_FOLLOWUP"):
        module.followup_prepare(root, "followup-other", True)
    module.followup_plan(root, module.FOLLOWUP_RUN_ID, True)
    with pytest.raises(ValueError, match="NO_PROMOTION"):
        module.followup_prepare(root, module.FOLLOWUP_RUN_ID, True)
    with pytest.raises(ValueError, match="MANIFEST"):
        module.followup_inspect(root, module.FOLLOWUP_RUN_ID)


def test_source_symlink_is_rejected_before_secret_body_can_be_hashed(prepared, tmp_path):
    module, root, _, _ = prepared
    private = tmp_path / "private-key"
    private.write_text("fake-never-read")
    (root / "src/malicious.py").symlink_to(private)
    with pytest.raises(ValueError, match="SOURCE_PATH"):
        module.source_hashes(root)


def test_manifest_changed_during_preflight_is_not_the_approved_manifest(executable, monkeypatch):
    module, root, _, approvals, providers, _, _ = executable
    original = module.followup_preflight
    target = module.followup_location(root, module.FOLLOWUP_RUN_ID)
    def changed(*args):
        report = original(*args)
        path = target / "plan/manifest.json"
        value = json.loads(path.read_text())
        value["unapproved_change"] = True
        path.write_text(json.dumps(value))
        return report
    monkeypatch.setattr(module, "followup_preflight", changed)
    with pytest.raises(ValueError, match="APPROVED_MANIFEST_CHANGED"):
        module.followup_evaluate(root, module.FOLLOWUP_RUN_ID, **approvals)
    assert not providers and not (target / "execution.claim").exists()
