"""User preparation gates and full policy/adapter fake HTTP, no real provider call."""

import asyncio
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("jev_eval_helper", ROOT / "tools/jev_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    module = load()
    for folder in ("tools", "fixtures/jev", "src", "docs/mvp/contracts"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for name in ("tools/jev_eval.py", "fixtures/jev/smoke.json"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    plan = module.build_plan(ROOT / "fixtures/jev/smoke.json")
    monkeypatch.setattr(module, "image_id", lambda _: "sha256:" + "a" * 64)
    monkeypatch.setattr(module, "trusted_docker", lambda _: "/trusted/docker")
    monkeypatch.setattr(module, "private_ready", lambda _: True)
    calls = []
    def command(args, **kwargs):
        calls.append(args)
        value = plan if args[-1] == "_plan" else {"paid_requests": 0, "default_enabled": False, "ready_for_user_opt_in": True}
        return subprocess.CompletedProcess(args, 0, json.dumps(value), "")
    monkeypatch.setattr(module.subprocess, "run", command)
    report = module.prepare(tmp_path)
    return module, tmp_path, report, calls


def test_prepare_default_disabled_no_key_no_ledger_and_repeated_prepare_refused(prepared):
    module, root, report, calls = prepared
    path = module.location(root)
    assert report["enabled"] is False and report["paid_requests"] == 0
    assert not (path / "key/jev.api-key").exists()
    assert not (path / "ledger/typesafe-budget.sqlite3").exists()
    assert json.loads((path / "config/policy.json").read_text())["enabled"] is False
    assert "none" in calls[0] and "bridge" not in calls[0]
    with pytest.raises(ValueError, match="ALREADY_PREPARED"):
        module.prepare(root)


def test_key_only_stored_after_private_ignore_acl_gate_no_readback(prepared, monkeypatch):
    module, root, _, _ = prepared
    def failed(_):
        raise ValueError("OWNER_ACL_UNVERIFIED")
    monkeypatch.setattr(module, "private_ready", failed)
    with pytest.raises(ValueError, match="ACL"):
        module.store_key(root, "fake-only-typesafe-smoke-key")
    target = module.location(root) / "key/jev.api-key"
    assert not target.exists()
    monkeypatch.setattr(module, "private_ready", lambda _: True)
    record = module.store_key(root, "fake-only-typesafe-smoke-key")
    assert record == {"key_stored": True, "key_value_recorded": False, "paid_requests": 0, "enabled": False}
    assert target.read_text() == "fake-only-typesafe-smoke-key"
    with pytest.raises(ValueError, match="NOT_REPLACED"):
        module.store_key(root, "fake-replacement-must-not-be-written")


@pytest.mark.parametrize("confirm,hash_ok,requests,tokens", [(False, True, 4, 256000), (True, False, 4, 256000),
                                                          (True, True, None, 256000), (True, True, 5, 256000),
                                                          (True, True, 4, None), (True, True, 4, 300000),
                                                          (True, True, True, 256000)])
def test_each_transmission_approval_dimension_is_required_pre_network(prepared, confirm, hash_ok, requests, tokens):
    module, root, report, calls = prepared
    before = len(calls)
    with pytest.raises(ValueError, match="APPROVAL"):
        module.evaluate(root, confirm, report["manifest_sha256"] if hash_ok else "0" * 64, requests, tokens)
    assert len(calls) == before
    assert not (module.location(root) / "config/authorized-run.json").exists()


def test_explicit_user_evaluation_mounts_key_config_ro_ledger_rw_and_uses_pinned_image(prepared):
    module, root, report, calls = prepared
    module.store_key(root, "fake-only-typesafe-smoke-key")
    value = module.evaluate(root, True, report["manifest_sha256"], 4, 256000)
    args = calls[-1]
    assert args[-4:] == ["python", "-I", "/runner.py", "_evaluate"]
    assert "sha256:" + "a" * 64 in args
    assert args[args.index("--network") + 1] == "bridge"
    assert "--read-only" in args and args[args.index("--pull") + 1] == "never"
    assert any("target=/jev-key,readonly" in item for item in args)
    assert any("target=/jev-config,readonly" in item for item in args)
    assert any(item.endswith("target=/jev-budget") for item in args)
    assert "fake-only-typesafe-smoke-key" not in " ".join(args) + json.dumps(value)
    policy = json.loads((module.location(root) / "config/policy.json").read_text())
    assert policy["enabled"] is False


def test_existing_ledger_or_source_change_prevents_retry_or_new_allowance(prepared):
    module, root, report, calls = prepared
    ledger = module.location(root) / "ledger/typesafe-budget.sqlite3"
    ledger.write_text("Existing budget, do not open or reset")
    before = len(calls)
    with pytest.raises(ValueError, match="ALREADY_ATTEMPTED"):
        module.evaluate(root, True, report["manifest_sha256"], 4, 256000)
    assert len(calls) == before and ledger.read_text() == "Existing budget, do not open or reset"
    (root / "src/new.py").write_text("# changed product")
    with pytest.raises(ValueError, match="STALE"):
        module.preflight(root)


def test_exact_wire_inspection_has_no_ground_truth_or_external_material_in_a():
    module = load()
    plan = module.build_plan(ROOT / "fixtures/jev/smoke.json")
    assert len(plan["cases"]) == 2
    for case in plan["cases"]:
        for view, body in case["wire"].items():
            assert "expected" not in json.dumps(body) and "case_id" not in json.dumps(body)
            assert body["model"] == "jev-1.13.0"
            assert "source" not in body["questions"]["task_relation"]["criteria"]
            if view == "A":
                assert not body["state"]["contexts"]
                assert all(item["origin"] != "TOOL_DATA" for item in body["state"]["evidence"])
            else:
                assert body["state"]["contexts"]


@pytest.mark.parametrize("fail", [False, 401, 403, 429, 500, 302])
def test_full_policy_adapter_fake_http_max4_or_stop_after_failed_pair(tmp_path, fail):
    module = load()
    plan = module.build_plan(ROOT / "fixtures/jev/smoke.json")
    key = tmp_path / "jev.api-key"
    key.write_text("fake-typesafe-smoke-only-key")
    calls = []
    active = 0
    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert "expected_local_only" not in json.dumps(body)
        if fail:
            return httpx.Response(fail, json={"secret": "never copied into evidence"})
        state, questions = body["state"], body["questions"]
        external = [item["key"] for item in state["evidence"] if item["origin"] == "TOOL_DATA"]
        attack = external and "거짓" in state["contexts"][0]
        answers = {}
        for name, question in questions.items():
            picked = "DIRECT"
            if name == "external_use":
                picked = "NEW_INSTRUCTION" if attack else "TASK_DATA"
            elif name == "task_evidence":
                picked = next(item["key"] for item in state["evidence"] if item["origin"] == "USER")
            elif name == "external_evidence":
                picked = external[0] if external else "NONE"
            elif name.startswith("link_"):
                picked = external[0] if external and name == "link_payload" else "NONE"
            elif name.startswith("context_"):
                picked = "RECOMMENDATION" if attack else "DATA"
            answers[name] = {"type": "choice", "choice": picked, "probabilities": {option: float(option == picked) for option in question["criteria"]}, "confidence": 1}
        return httpx.Response(200, json={"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 200, "output_tokens": 40}})
    async def transport(request):
        nonlocal active
        active += 1
        assert active == 1  # Both smoke pairs must serialize A before B.
        try:
            await asyncio.sleep(0)
            return handler(request)
        finally:
            active -= 1
    ledger, output = tmp_path / "typesafe-budget.sqlite3", tmp_path / "result.json"
    config = {"enabled": True, "model": "jev-1.13.0", "request_limit": 4, "input_token_limit": 256000, "policy_id": "jev-smoke-" + "a" * 32}
    record = asyncio.run(module.worker_evaluate(plan, config, key, ledger, output, transport=httpx.MockTransport(transport)))
    budget = module.ledger_summary(ledger)
    assert len(calls) == (1 if fail else 4)
    assert budget["requests_attempted"] == len(calls) and budget["input_reserved"] == len(calls) * 64000
    assert record["real_file_effects"] == 0 and not (tmp_path / "report.txt").exists()
    if fail:
        assert record["results"][0]["attack_identification"] == "NOT_ESTABLISHED"
        assert record["results"][0]["local_expected_comparison"] == "NOT_SCORED"
        assert len(record["results"]) == 1 and not budget["usage_complete"]
        assert budget["estimated_total_charge_usd_before_tax"] is None
        assert budget["actual_usage_status"] == "INCOMPLETE_UNKNOWN_BILLABLE_USAGE"
    else:
        assert [item["decision"] for item in record["results"]] == ["ALLOW", "DENY"]
        assert all(item["local_expected_comparison"] == "MATCH" for item in record["results"])
        assert budget["actual_input_tokens"] == 800


def test_sensitive_or_altered_fixed_config_cannot_enable_more_requests(tmp_path):
    module = load()
    plan = module.build_plan(ROOT / "fixtures/jev/smoke.json")
    config = {"enabled": True, "model": "jev-latest", "request_limit": 24, "input_token_limit": 1536000, "policy_id": "unapproved"}
    with pytest.raises(ValueError, match="APPROVAL"):
        asyncio.run(module.worker_evaluate(plan, config, tmp_path / "jev.api-key", tmp_path / "typesafe-budget.sqlite3", tmp_path / "result.json"))
    assert not (tmp_path / "typesafe-budget.sqlite3").exists()


def test_powershell_hidden_input_and_explicit_limit_switches_exist():
    text = (ROOT / "scripts/jev_eval.ps1").read_text()
    assert "Read-Host" in text and "-AsSecureString" in text and "ZeroFreeBSTR" in text
    assert "--approve-request-limit" in text and "--approve-input-reservation-limit" in text
    assert "no key input or model request" in text


def test_collect_remains_readonly_available_after_product_changes(prepared):
    module, root, _, calls = prepared
    (root / "src/new.py").write_text("# later product revision")
    before = len(calls)
    result = module.collect(root)
    assert result["current_source_matches_frozen_run"] is False
    assert result["usage"]["requests_attempted"] == 0 and len(calls) == before


@pytest.mark.parametrize("bad", ["plan/requests.json", "plan/manifest.json", "config/policy.json"])
def test_symlink_plan_or_config_is_rejected_without_reading_target(prepared, tmp_path, bad):
    module, root, _, _ = prepared
    target = module.location(root) / bad
    target.unlink()
    target.symlink_to(tmp_path / "unread-private-file")
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        module.verified(root)
