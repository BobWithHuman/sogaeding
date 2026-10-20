"""V5 fixed smoke through the existing evaluator; fake HTTP and disposable DBs."""
import asyncio
import copy
import json
import shutil
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_jev_eval import ROOT, load
from test_jev_v4_eval import files


@pytest.fixture
def v5(tmp_path, monkeypatch):
    module = load()
    for name in module.fixed_source_hashes(ROOT, module.V5_RUN_ID):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for relative, count in [(module.RELATIVE, 1), ("artifacts/runtime-jev-followups/" + module.FOLLOWUP_RUN_ID, 4),
                            ("artifacts/runtime-mvp-demo", 8), ("artifacts/runtime-jev-followups/" + module.V4_RUN_ID, 4)]:
        base = tmp_path / relative
        (base / "ledger").mkdir(parents=True)
        (base / "plan").mkdir(exist_ok=True)
        (base / "plan/manifest.json").write_text('{"historical":"preserve"}')
        with sqlite3.connect(base / "ledger/typesafe-budget.sqlite3") as db:
            db.execute("CREATE TABLE jev_attempts (status TEXT,input_reserved INTEGER,usage TEXT)")
            for _ in range(count):
                db.execute("INSERT INTO jev_attempts VALUES (?,64000,?)", ("FAILED" if count == 1 else "COMPLETED", None if count == 1 else json.dumps({"input_tokens": 10, "output_tokens": 2})))
    bundle = tmp_path / "artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/bundle"
    bundle.mkdir(parents=True)
    (bundle / "sample.py").write_text("# historical bundle")
    (bundle / "manifest.json").write_text(json.dumps([{"path": "sample.py", "sha256": module.sha(bundle / "sample.py") }]))
    (bundle.parent / "manifest.json").write_text('{"frozen":"V3"}')
    key = tmp_path / module.RELATIVE / "key/jev.api-key"
    key.parent.mkdir()
    key.write_text("fake-key-for-offline-v5-only")
    plan = module.build_v5_plan(ROOT / module.V5_ORIGINAL_PLAN)
    providers, commands, mode = [], [], {"kind": "normal", "at": 1}

    def response(request):
        providers.append(request)
        if len(providers) == mode["at"] and mode["kind"] == "http":
            return httpx.Response(401, text="PRIVATE_PROVIDER_ERROR")
        wire = json.loads(request.content)
        attack = wire["state"]["candidate"]["args"]["path"] == "reports/review.md"
        answers = {}
        for name, question in wire["questions"].items():
            chosen = "WITHIN_TASK" if name == "task_relation" else ("EXTERNAL_ADOPTION" if attack else "LEGITIMATE") if name == "behavior" else "UNCERTAIN"
            probs = {opt: float(opt == chosen) for opt in question["criteria"]}
            confidence = 1.
            if mode["kind"] == "low" and name == "behavior":
                probs[chosen] = .8
                probs["UNCERTAIN"] = .2
                confidence = (len(probs) * .8 - 1) / (len(probs) - 1)
            if mode["kind"] == "ref" and len(providers) == mode["at"]:
                chosen = "FORGED_OPTION"
            answers[name] = {"type": "choice", "choice": chosen, "probabilities": probs, "confidence": confidence}
        value = {"model": module.MODEL, "answers": answers, "usage": {"input_tokens": 10, "output_tokens": 2}}
        if len(providers) == mode["at"]:
            if mode["kind"] == "shape":
                value["answers"] = {}
            elif mode["kind"] == "partial":
                value["usage"]["output_tokens"] = None
        return httpx.Response(200, json=value)

    monkeypatch.setattr(module, "trusted_docker", lambda _: "/trusted/docker")
    monkeypatch.setattr(module, "image_id", lambda _: "sha256:" + "a" * 64)
    monkeypatch.setattr(module, "private_ready", lambda *_: True)

    def command(args, **kwargs):
        commands.append(args)
        if args[-1] == "_plan":
            result = plan
        elif args[-1] == "_preflight":
            result = {"paid_requests": 0, "default_enabled": False, "ready_for_user_opt_in": True, "actual_key_read": False}
        else:
            target = module.followup_location(tmp_path, module.V5_RUN_ID)
            config = json.loads((target / "config/authorized-run.json").read_text())
            result = asyncio.run(module.worker_evaluate(plan, config, key, target / "ledger/typesafe-budget.sqlite3", target / "results/result.json", transport=httpx.MockTransport(response)))
        return subprocess.CompletedProcess(args, 0, json.dumps(result), "")

    monkeypatch.setattr(module.subprocess, "run", command)
    prepared = module.followup_prepare(tmp_path, module.V5_RUN_ID, True)
    approvals = dict(confirm_send=True, manifest_sha256=prepared["manifest_sha256"], request_limit=4, input_limit=256000,
                     cumulative_requests=21, cumulative_input=1344000, additional_requests=4, additional_input=256000,
                     demo_cumulative_requests=16, demo_cumulative_input=1024000)
    return module, tmp_path, plan, approvals, providers, commands, mode


def test_exact_original_snapshots_standard_client_wire_order_and_typed_result(v5, monkeypatch):
    from app.transparent.jev import JevClient
    module, root, plan, approvals, providers, commands, _ = v5
    prior = json.loads((ROOT / module.V5_ORIGINAL_PLAN).read_text())
    assert [c["snapshot"] for c in plan["cases"]] == [c["snapshot"] for c in prior["cases"]]
    observed_classes = []
    observe = JevClient.observe

    async def spy(self, *args):
        observed_classes.append(type(self))
        return await observe(self, *args)

    monkeypatch.setattr(JevClient, "observe", spy)
    parent_before = module.v4_parent_binding(root, module.V5_RUN_ID)
    assert parent_before["historical_requests"] == 17 and parent_before["historical_input_reserved"] == 1088000
    report = module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert observed_classes == [JevClient] * 4
    assert [r.content for r in providers] == [module.canonical(c["wire"][v]).encode() for c in plan["cases"] for v in ("A", "B")]
    for case in plan["cases"]:
        assert not case["wire"]["A"]["state"].get("contexts")
        for wire in case["wire"].values():
            assert "expected_local_only" not in module.canonical(wire) and "case_id" not in module.canonical(wire)
            assert "raw_sha256" not in module.canonical(wire) and "text_sha256" not in module.canonical(wire)
    rows = report["result"]["result"]["results"]
    assert [r["decision"] for r in rows] == ["ALLOW", "DENY"]
    b = rows[1]["policy_trace"]["decision_attribution"]["B"]
    assert b["validated_input_sources"] and not b["semantic_support_refs"]
    assert b["causal_explanation"] == "NOT_ESTABLISHED"
    assert rows[1]["policy_trace"]["view_observations"]["B"][0]["effective_confidence"] == 1.
    assert report["result"]["usage"]["input_reserved"] == 256000
    assert report["result"]["usage"]["actual_input_tokens"] == 40
    assert module.v4_parent_binding(root, module.V5_RUN_ID) == parent_before
    assert any("target=/jev-key,readonly" in a for a in commands[-1])
    target = module.followup_location(root, module.V5_RUN_ID)
    before = files(target)
    assert module.followup_collect(root, module.V5_RUN_ID)["semantic_summary"]["outcome"] == "COMPLETE_OBSERVATIONS_MATCH_SMOKE_ONLY"
    assert files(target) == before
    with pytest.raises(ValueError, match="CLAIMED"):
        module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert len(providers) == 4, json.dumps(report, ensure_ascii=False)


@pytest.mark.parametrize("kind", ["http", "shape", "partial", "ref"])
@pytest.mark.parametrize("at", [1, 2, 3, 4])
def test_first_error_stops_no_extra_request_or_refund(v5, kind, at):
    module, root, _, approvals, providers, _, mode = v5
    mode.update(kind=kind, at=at)
    report = module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert len(providers) == at
    assert report["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"
    assert report["result"]["usage"]["input_reserved"] == at * 64000
    assert "PRIVATE_" not in json.dumps(report)
    if kind == "partial":
        assert not report["result"]["usage"]["usage_complete"]


def test_low_behavior_remains_confirm_no_repair_calls(v5):
    module, root, _, approvals, providers, _, mode = v5
    mode["kind"] = "low"
    result = module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert len(providers) == 4, json.dumps(result, ensure_ascii=False)
    assert [r["decision"] for r in result["result"]["result"]["results"]] == ["CONFIRM", "CONFIRM"]


@pytest.mark.parametrize("field", ["confirm_send", "manifest_sha256", "request_limit", "input_limit", "cumulative_requests", "cumulative_input", "additional_requests", "additional_input", "demo_cumulative_requests", "demo_cumulative_input"])
def test_every_approval_dimension_required(v5, field):
    module, root, _, approvals, providers, _, _ = v5
    with pytest.raises(ValueError, match="APPROVAL_REQUIRED"):
        module.followup_evaluate(root, module.V5_RUN_ID, **{**approvals, field: None})
    assert not providers


@pytest.mark.parametrize("change", ["source", "candidate", "original", "wire", "parent", "image"])
def test_changed_binding_rejected_and_historical_collect_honest(v5, monkeypatch, change):
    module, root, _, approvals, providers, _, _ = v5
    target = module.followup_location(root, module.V5_RUN_ID)
    if change == "source":
        (root / "src/changed.py").write_text("# new source")
    elif change == "candidate":
        (root / "src/app/transparent/jev_decision_v5.py").write_text("# altered")
    elif change == "original":
        (root / module.V5_ORIGINAL_PLAN).write_text("{}")
    elif change == "wire":
        (target / "plan/requests.json").write_text("{}")
    elif change == "parent":
        with sqlite3.connect(root / "artifacts/runtime-jev-followups/followup-auto-v4/ledger/typesafe-budget.sqlite3") as db:
            db.execute("UPDATE jev_attempts SET status='FAILED'")
    else:
        monkeypatch.setattr(module, "image_id", lambda _: "sha256:" + "b" * 64)
    with pytest.raises(ValueError):
        module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert not providers and not (target / "execution.claim").exists()
    if change in ("source", "candidate", "original"):
        assert module.followup_collect(root, module.V5_RUN_ID)["current_source_matches_frozen_run"] is False


@pytest.mark.parametrize("change", ["snapshot", "wire"])
def test_worker_tampered_input_before_key_or_ledger(v5, change):
    module, root, plan, _, providers, _, _ = v5
    plan = copy.deepcopy(plan)
    if change == "snapshot":
        plan["cases"][0]["snapshot"]["sources"][0]["analysis_text_sha256"] = "0" * 64
    else:
        plan["cases"][0]["wire"]["B"]["state"]["evidence"][0]["key"] = "forged"
    config = {"enabled": True, "model": module.MODEL, "request_limit": 4, "input_token_limit": 256000, "policy_id": "jev-smoke-" + "a" * 32}
    target = module.followup_location(root, module.V5_RUN_ID)
    with pytest.raises(ValueError):
        asyncio.run(module.worker_evaluate(plan, config, root / "unread-key", target / "ledger/typesafe-budget.sqlite3", target / "results/result.json"))
    assert not providers and not (target / "ledger/typesafe-budget.sqlite3").exists()


def test_standard_sensitive_guard_blocks_fake_key_in_exact_wire(v5):
    module, root, _, approvals, providers, _, _ = v5
    # A long synthetic path already in the frozen payload is a valid fake key.
    # The standard guard must still reject it before any HTTP request.
    (root / module.RELATIVE / "key/jev.api-key").write_text("reports/normal.md")
    report = module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
    assert not providers
    assert report["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"


def test_disabled_preflight_one_slot_competing_claim_and_interrupted_collect(v5):
    module, root, _, approvals, providers, _, _ = v5
    target = module.followup_location(root, module.V5_RUN_ID)
    assert module.followup_preflight(root, module.V5_RUN_ID)["live_authorized"] is False
    assert not (target / "config/authorized-run.json").exists() and not (target / "ledger/typesafe-budget.sqlite3").exists()
    with pytest.raises(ValueError, match="NO_PROMOTION"):
        module.followup_prepare(root, module.V5_RUN_ID, True)
    def attempt(_):
        try:
            module.followup_evaluate(root, module.V5_RUN_ID, **approvals)
            return "winner"
        except (ValueError, FileExistsError):
            return "stopped"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["stopped", "winner"]
    assert len(providers) == 4
    (target / "results/result.json").unlink()
    report = module.followup_collect(root, module.V5_RUN_ID)
    assert report["semantic_summary"]["outcome"] == "EXECUTION_STATUS_UNKNOWN"
    assert report["automatic_retry_allowed"] is False
