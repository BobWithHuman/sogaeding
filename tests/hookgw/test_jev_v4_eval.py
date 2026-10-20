"""Fixed V4 runner tests: fake provider only, fresh disposable accounting files."""
import asyncio
import json
import shutil
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_jev_eval import ROOT, load


def files(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file() and p.name != "jev.api-key"}


@pytest.fixture
def v4(tmp_path, monkeypatch):
    module = load()
    paths = set(module.source_hashes(ROOT)) | {f"{module.V4_INPUT}/{name}" for name in module.V4_FIXED_HASHES}
    paths |= {row["path"] for row in json.loads((ROOT / module.V4_INPUT / "candidate-manifest.json").read_text())}
    paths |= {"fixtures/mvp_demo/docs/release.md", "fixtures/mvp_demo/docs/review.md"}
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for relative, count in [(module.RELATIVE, 1), ("artifacts/runtime-jev-followups/" + module.FOLLOWUP_RUN_ID, 4), ("artifacts/runtime-mvp-demo", 8)]:
        base = tmp_path / relative
        (base / "ledger").mkdir(parents=True)
        (base / "plan").mkdir()
        (base / "plan/manifest.json").write_text('{"immutable":"historical fixture"}')
        with sqlite3.connect(base / "ledger/typesafe-budget.sqlite3") as db:
            db.execute("CREATE TABLE jev_attempts (status TEXT,input_reserved INTEGER,usage TEXT)")
            for _ in range(count):
                db.execute("INSERT INTO jev_attempts VALUES (?,64000,?)", ("FAILED" if count == 1 else "COMPLETED", None if count == 1 else json.dumps({"input_tokens": 10, "output_tokens": 2})))
    bundle = tmp_path / "artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/bundle"
    bundle.mkdir(parents=True)
    (bundle / "sample.py").write_text("# preserved bundle")
    (bundle / "manifest.json").write_text(json.dumps([{"path": "sample.py", "sha256": module.sha(bundle / "sample.py")}]))
    (bundle.parent / "manifest.json").write_text('{"frozen":"V3"}')
    key = tmp_path / module.RELATIVE / "key/jev.api-key"
    key.parent.mkdir()
    key.write_text("fake-key-offline-provider-tests")
    plan = module.build_v4_plan(ROOT / module.V4_INPUT, ROOT / "fixtures/mvp_demo")
    mode = {"kind": "normal", "at": 1}
    providers, commands = [], []
    def response(request):
        providers.append(request)
        if len(providers) == mode["at"]:
            if mode["kind"] == "http":
                return httpx.Response(401, text="PRIVATE_PROVIDER_ERROR")
            if mode["kind"] == "shape":
                return httpx.Response(200, json={"model": module.MODEL, "answers": {}, "usage": {"input_tokens": 10, "output_tokens": 2}})
        wire = json.loads(request.content)
        attack = wire["state"]["candidate"]["args"]["path"] == "reports/review.md"
        answers = {}
        for name, question in wire["questions"].items():
            chosen = "WITHIN_TASK" if name == "task_relation" else "ADDED_INSTRUCTION" if attack and name == "basis_payload" else "TASK_DATA" if name == "basis_payload" else "INDEPENDENT" if name.startswith("basis_") else "SUPPORTED" if name.startswith("support_payload_") else "UNRELATED"
            probs = {opt: float(opt == chosen) for opt in question["criteria"]}
            confidence = 1.
            if mode["kind"] == "low" and name == "task_relation":
                probs[chosen] = .8
                probs[next(opt for opt in probs if opt != chosen)] = .2
                confidence = .7
            answers[name] = {"type": "choice", "choice": chosen, "probabilities": probs, "confidence": confidence}
        value = {"model": module.MODEL, "answers": answers, "usage": {"input_tokens": 10, "output_tokens": 2}}
        if len(providers) == mode["at"]:
            if mode["kind"] == "partial":
                value["usage"]["output_tokens"] = None
            elif mode["kind"] == "nullable":
                value["usage"] = {"input_tokens": None, "output_tokens": None}
            elif mode["kind"] == "bad_usage":
                value["usage"]["input_tokens"] = True
            elif mode["kind"] == "missing_usage":
                del value["usage"]
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
            target = module.followup_location(tmp_path, module.V4_RUN_ID)
            config = json.loads((target / "config/authorized-run.json").read_text())
            result = asyncio.run(module.worker_evaluate(plan, config, key, target / "ledger/typesafe-budget.sqlite3", target / "results/result.json", transport=httpx.MockTransport(response)))
        return subprocess.CompletedProcess(args, 0, json.dumps(result), "")
    monkeypatch.setattr(module.subprocess, "run", command)
    prepared = module.followup_prepare(tmp_path, module.V4_RUN_ID, True)
    approvals = dict(confirm_send=True, manifest_sha256=prepared["manifest_sha256"], request_limit=4, input_limit=256000,
                     cumulative_requests=17, cumulative_input=1088000, additional_requests=4, additional_input=256000,
                     demo_cumulative_requests=12, demo_cumulative_input=768000)
    return module, tmp_path, plan, approvals, providers, commands, mode


def test_v4_exact_pipeline_order_typed_results_accounting_collect_and_parent_preserved(v4):
    module, root, plan, approvals, providers, commands, _ = v4
    parent_before = module.v4_parent_binding(root)
    target = module.followup_location(root, module.V4_RUN_ID)
    assert not (target / "ledger/typesafe-budget.sqlite3").exists()
    assert not (target / "config/authorized-run.json").exists()
    assert module.followup_preflight(root, module.V4_RUN_ID)["ready_for_user_opt_in"]
    report = module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
    assert len(providers) == 4, json.dumps(report, ensure_ascii=False)
    assert [r.content for r in providers] == [module.canonical(case["wire"][view]).encode() for case in plan["cases"] for view in ("A", "B")]
    assert [r["decision"] for r in report["result"]["result"]["results"]] == ["ALLOW", "DENY"]
    assert report["semantic_summary"]["outcome"] == "COMPLETE_OBSERVATIONS_MATCH_SMOKE_ONLY"
    assert report["result"]["usage"]["requests_attempted"] == 4
    assert report["result"]["usage"]["input_reserved"] == 256000
    assert module.v4_parent_binding(root) == parent_before
    trace = report["result"]["result"]["results"][0]["policy_trace"]
    assert trace["view_observations"]["B"][0]["provider_confidence"] == 1.
    assert trace["view_observations"]["B"][0]["computed_confidence"] == 1.
    assert report["result"]["result"]["results"][0]["view_checks"]["B"]["exact_source_refs"]
    assert any("target=/jev-key,readonly" in a for a in commands[-1])
    assert not any("target=/jev-budget,readonly" in a for a in commands[-1])
    before = files(target)
    module.followup_collect(root, module.V4_RUN_ID)
    assert files(target) == before
    with pytest.raises(ValueError, match="CLAIMED"):
        module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
    assert len(providers) == 4


@pytest.mark.parametrize("kind", ["http", "shape", "partial", "nullable", "bad_usage", "missing_usage"])
@pytest.mark.parametrize("at", [1, 2, 3, 4])
def test_first_failure_stops_remaining_views_cases_and_never_refunds(v4, kind, at):
    module, root, _, approvals, providers, _, mode = v4
    mode.update(kind=kind, at=at)
    report = module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
    assert len(providers) == at
    assert report["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"
    assert report["result"]["usage"]["input_reserved"] == at * 64000
    assert "PRIVATE_" not in json.dumps(report)
    if kind in ("partial", "nullable", "bad_usage", "missing_usage"):
        assert report["result"]["usage"]["usage_complete"] is False
    assert not report["execution_exit_is_semantic_success"]


def test_valid_low_confidence_is_scored_confirm_without_extra_correction_calls(v4):
    module, root, _, approvals, providers, _, mode = v4
    mode["kind"] = "low"
    report = module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
    assert len(providers) == 4
    assert report["result"]["result"]["results"][0]["decision"] == "CONFIRM"
    assert report["semantic_summary"]["outcome"] == "COMPLETE_OBSERVATIONS_WITH_MISMATCH"


@pytest.mark.parametrize("change", ["source", "wire", "manifest", "parent", "bundle", "image", "proposal"])
def test_changed_dependency_refuses_before_claim_and_collect_remains_readonly(v4, monkeypatch, change):
    module, root, _, approvals, providers, _, _ = v4
    target = module.followup_location(root, module.V4_RUN_ID)
    if change == "source":
        (root / "src/changed.py").write_text("# changed")
    elif change == "wire":
        (target / "plan/requests.json").write_text("{}")
    elif change == "manifest":
        value = json.loads((target / "plan/manifest.json").read_text())
        value["additional_request_limit"] = 9
        (target / "plan/manifest.json").write_text(json.dumps(value))
    elif change == "parent":
        with sqlite3.connect(root / "artifacts/runtime-mvp-demo/ledger/typesafe-budget.sqlite3") as db:
            db.execute("UPDATE jev_attempts SET status='FAILED'")
    elif change == "bundle":
        (root / "artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/bundle/sample.py").write_text("# changed")
    elif change == "image":
        monkeypatch.setattr(module, "image_id", lambda _: "sha256:" + "b" * 64)
    else:
        (root / module.V4_INPUT / "proposal-normal-A.json").write_text("{}")
    with pytest.raises(ValueError):
        module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
    assert providers == [] and not (target / "execution.claim").exists()
    if change not in ("wire", "manifest"):
        before = files(target)
        assert module.followup_collect(root, module.V4_RUN_ID)["execution_status"] == "NOT_STARTED"
        assert files(target) == before


@pytest.mark.parametrize("field", ["confirm_send", "manifest_sha256", "request_limit", "input_limit", "cumulative_requests", "cumulative_input", "additional_requests", "additional_input", "demo_cumulative_requests", "demo_cumulative_input"])
def test_each_approval_dimension_required(v4, field):
    module, root, _, approvals, providers, _, _ = v4
    with pytest.raises(ValueError, match="APPROVAL_REQUIRED"):
        module.followup_evaluate(root, module.V4_RUN_ID, **{**approvals, field: None})
    assert not providers


def test_single_prepared_slot_and_atomic_competing_evaluate(v4):
    module, root, _, approvals, providers, commands, _ = v4
    with pytest.raises(ValueError, match="NO_PROMOTION"):
        module.followup_prepare(root, module.V4_RUN_ID, True)
    def attempt(_):
        try:
            module.followup_evaluate(root, module.V4_RUN_ID, **approvals)
            return "winner"
        except (ValueError, FileExistsError):
            return "stopped"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["stopped", "winner"]
    assert len(providers) == 4 and sum(c[-1] == "_evaluate" for c in commands) == 1


def test_bundle_manifest_cannot_hash_outside_bundle_files(v4, monkeypatch):
    module, root, _, _, _, _, _ = v4
    bundle = root / "artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/bundle"
    (bundle / "manifest.json").write_text(json.dumps([{"path": "../../../../runtime-jev-eval/key/jev.api-key", "sha256": "0" * 64}]))
    original, hashed = module.checked_sha, []
    def checked(root, path):
        hashed.append(path)
        return original(root, path)
    monkeypatch.setattr(module, "checked_sha", checked)
    with pytest.raises(ValueError, match="BUNDLE_CHANGED"):
        module.v4_parent_binding(root)
    assert not any(path.name == "jev.api-key" for path in hashed)
