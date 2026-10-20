"""Response repair reporting and disabled followup proposals, fake files only."""

import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

pytest_plugins = ["test_jev_eval"]


def failed_run(prepared, usage=None):
    module, root, _, calls = prepared
    path = module.location(root)
    with sqlite3.connect(path / "ledger/typesafe-budget.sqlite3") as db:
        db.execute("CREATE TABLE jev_attempts (analysis_id TEXT,view TEXT,status TEXT,input_reserved INTEGER,usage TEXT)")
        db.execute("INSERT INTO jev_attempts VALUES ('S01','A','FAILED',64000,?)", (json.dumps(usage) if usage is not None else None,))
    module.write_new(path / "config/authorized-run.json", {"enabled": True, "request_limit": 4, "input_token_limit": 256000})
    module.write_new(path / "results/result.json", {"results": [{"case_id": "S01", "status": "ANALYSIS_UNAVAILABLE",
        "diagnostics": [{"code": "JEV_RESPONSE_INVALID", "view": "A"}, {"code": "TURN_ANALYSIS_STOPPED", "view": "B"}],
        "local_expected_comparison": "NOT_SCORED", "attack_identification": "NOT_ESTABLISHED"}], "korean_fixture_note": "한국어 합성 연결 시험"})
    return module, root, path, calls


def preserved(path):
    return {item.relative_to(path).as_posix(): item.read_bytes() for item in path.rglob("*") if item.is_file() and item.name != "jev.api-key"}


def test_old_failure_collect_utf8_readonly_partial_status_and_no_success_from_exit(prepared):
    module, root, path, calls = failed_run(prepared)
    before = preserved(path)
    (root / "src/new.py").write_text("# new adapter cannot reuse old manifest")
    captured = len(calls)
    report = module.collect(root)
    assert len(calls) == captured and preserved(path) == before
    assert report["current_source_matches_frozen_run"] is False
    assert report["result"]["korean_fixture_note"] == "한국어 합성 연결 시험"
    summary = report["semantic_summary"]
    assert summary["outcome"] == "ANALYSIS_FAILED_PARTIAL"
    assert (summary["planned_candidates"], summary["scored_candidates"], summary["not_scored_candidates"], summary["not_attempted_candidates"]) == (2, 0, 1, 1)
    assert summary["cases"] == [{"case_id": "S01", "status": "ANALYSIS_UNAVAILABLE", "comparison": "NOT_SCORED", "diagnostic_detail": "UNKNOWN_NOT_RECORDED"}, {"case_id": "S02", "status": "NOT_ATTEMPTED", "comparison": "NOT_SCORED"}]
    assert summary["execution_exit_is_semantic_success"] is False
    assert report["usage"]["requests_attempted"] == 1 and report["usage"]["input_reserved"] == 64000
    assert report["usage"]["estimated_total_charge_usd_before_tax"] is None
    with pytest.raises(ValueError, match="STALE"):
        module.preflight(root)


@pytest.mark.parametrize("usage,known_in,known_out,input_complete,output_complete", [
    ({"input_tokens": 200, "output_tokens": None}, 200, 0, True, False),
    ({"input_tokens": None, "output_tokens": 20}, 0, 20, False, True),
    ({"input_tokens": True, "output_tokens": 20}, 0, 20, False, True),
    ({"input_tokens": -1, "output_tokens": 1000001}, 0, 0, False, False),
    ({"input_tokens": 200, "output_tokens": 20}, 200, 20, True, True),
])
def test_failed_answer_usage_record_is_not_automatically_complete(prepared, usage, known_in, known_out, input_complete, output_complete):
    module, _, path, _ = failed_run(prepared, usage)
    before = preserved(path)
    summary = module.ledger_summary(path / "ledger/typesafe-budget.sqlite3")
    assert (summary["actual_input_tokens"], summary["actual_output_tokens"]) == (known_in, known_out)
    assert summary["input_usage_complete"] is input_complete
    assert summary["output_usage_complete"] is output_complete
    assert summary["usage_complete"] is (input_complete and output_complete)
    assert (summary["estimated_total_charge_usd_before_tax"] is not None) is (input_complete and output_complete)
    assert summary["input_reserved"] == 64000 and preserved(path) == before


def test_followup_disabled_new_plan_accounts_old_failure_without_reading_or_copying_key(prepared, monkeypatch):
    module, root, prior, _ = failed_run(prepared)
    key = prior / "key/jev.api-key"
    key.write_text("fake-key-never-read")
    before = preserved(prior)
    original_read_bytes, original_read_text = Path.read_bytes, Path.read_text
    def guarded_bytes(path):
        if path.name == "jev.api-key":
            pytest.fail("Followup proposals must not read/hash an existing key")
        return original_read_bytes(path)
    def guarded_text(path, *args, **kwargs):
        if path.name == "jev.api-key":
            pytest.fail("Followup proposals must not read an existing key")
        return original_read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_text)
    (root / "src/new.py").write_text("# repaired source")
    record = module.followup_plan(root, "followup-response-repair", True)
    assert preserved(prior) == before
    assert record["created"] == "DISABLED_PROPOSAL_ONLY" and record["new_provider_ledger_created"] is False
    proposal = record["budget_proposal"]
    assert (proposal["prior_requests_attempted"], proposal["prior_input_reserved"]) == (1, 64000)
    assert (proposal["remaining_requests"], proposal["remaining_input_reserved"]) == (3, 192000)
    assert (proposal["additional_requests_needed"], proposal["additional_input_reservation_needed"]) == (1, 64000)
    assert (proposal["proposed_total_requests_including_prior"], proposal["proposed_total_input_reservation_including_prior"]) == (5, 320000)
    assert proposal["prior_failure_reservation_refunded"] is False
    assert not proposal["full_smoke_fits_existing_remainder"] and not proposal["evaluation_supported"]
    assert proposal["prior_actual_charge"] is None
    created = module.followup_location(root, "followup-response-repair")
    assert json.loads((created / "config/policy.json").read_text())["enabled"] is False
    assert not list(created.rglob("*.sqlite3")) and not list(created.rglob("jev.api-key")) and not list(created.rglob("authorized-run.json"))
    with pytest.raises(ValueError, match="ALREADY_EXISTS"):
        module.followup_plan(root, "followup-response-repair", True)


@pytest.mark.parametrize("name", ["../outside", "followup-../../escape", "C:/outside", "followup-x/child", "followup-.x", "followup-x:stream", "FOLLOWUP-X", ""])
def test_arbitrary_followup_paths_are_rejected_preparation0(prepared, name):
    module, root, _, calls = prepared
    before = len(calls)
    with pytest.raises(ValueError, match="RUN_ID_REJECTED"):
        module.followup_plan(root, name, True)
    assert len(calls) == before
    assert not (root / "artifacts/runtime-jev-followups").exists()


def test_followup_explicit_gate_symlink_and_same_id_concurrency_preserve_old_run(prepared, tmp_path):
    module, root, prior, _ = failed_run(prepared)
    before = preserved(prior)
    with pytest.raises(ValueError, match="CONFIRMATION"):
        module.followup_plan(root, "followup-safe")
    base = root / "artifacts/runtime-jev-followups"
    outside = tmp_path / "outside"
    outside.mkdir()
    base.symlink_to(outside)
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        module.followup_plan(root, "followup-safe", True)
    assert list(outside.iterdir()) == []
    base.unlink()
    def propose(_):
        try:
            return module.followup_plan(root, "followup-concurrent", True)["created"]
        except (ValueError, FileExistsError):
            return "REJECTED"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(propose, range(2)))
    assert outcomes.count("DISABLED_PROPOSAL_ONLY") == 1
    assert outcomes.count("REJECTED") == 1
    assert preserved(prior) == before


def test_budget_concurrent_writer_snapshot_never_grants_new_authority(prepared):
    module, root, path, _ = failed_run(prepared)
    ledger = path / "ledger/typesafe-budget.sqlite3"
    with sqlite3.connect(ledger) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO jev_attempts VALUES ('S02','A','STARTED',64000,NULL)")
        record = module.followup_plan(root, "followup-during-reservation", True)
        proposal = record["budget_proposal"]
        assert proposal["prior_requests_attempted"] == 1  # consistent committed snapshot
        assert proposal["budget_snapshot_is_not_reservation"] is True and proposal["evaluation_supported"] is False
    assert module.ledger_summary(ledger)["requests_attempted"] == 2


def test_powershell_followup_mode_stays_separate_from_evaluation():
    text = (Path(__file__).resolve().parents[2] / "scripts/jev_eval.ps1").read_text(encoding="utf-8")
    assert "-Mode 'followup-plan'" not in text  # Never auto-invoked.
    assert "--confirm-new-plan" in text and "no budget or transmission is authorized" in text


@pytest.mark.parametrize("usage,complete", [({"input_tokens": 321, "output_tokens": 40}, True),
                                           ({"input_tokens": 321, "output_tokens": None}, False)])
def test_worker_keeps_enriched_failure_and_independent_usage_after_bad_answer(tmp_path, usage, complete):
    from test_jev_eval import ROOT, load
    module = load()
    plan = module.build_plan(ROOT / "fixtures/jev/smoke.json")
    key = tmp_path / "jev.api-key"
    key.write_text("fake-typesafe-response-helper-key")
    calls = []
    def invalid(request):
        calls.append(request)
        return httpx.Response(200, json={"model": module.MODEL, "answers": {"PRIVATE_DYNAMIC_KEY": {"private": "PRIVATE_RESPONSE_BODY"}}, "usage": usage})
    ledger = tmp_path / "typesafe-budget.sqlite3"
    config = {"enabled": True, "model": module.MODEL, "request_limit": 4, "input_token_limit": 256000, "policy_id": "jev-smoke-" + "a" * 32}
    record = asyncio.run(module.worker_evaluate(plan, config, key, ledger, tmp_path / "result.json", transport=httpx.MockTransport(invalid)))
    assert len(calls) == 1 and "PRIVATE_" not in json.dumps(record)
    diagnostic = record["results"][0]["diagnostics"][0]
    assert diagnostic["response_stage"] == "QUESTIONS"
    assert diagnostic["http_status"] == 200 and diagnostic["content_type"] == "JSON"
    assert diagnostic["usage_status"] == ("VALID" if complete else "PARTIAL")
    assert record["semantic_summary"]["outcome"] == "ANALYSIS_FAILED_PARTIAL"
    summary = module.ledger_summary(ledger)
    assert summary["usage_complete"] is complete and summary["actual_input_tokens"] == 321
    assert summary["input_reserved"] == 64000
    if not complete:
        assert summary["estimated_total_charge_usd_before_tax"] is None
