"""Offline evidence selection, real exact checks, durable same-turn cost gate."""
import asyncio
import json
from pathlib import Path

import pytest
from test_engine import ObservationFixture, authorize, register

from app.common import canonical, digest
from app.pdp.diagnostics import AnalysisFailure, failure_details
from app.pdp.semantic import (
    SPAN_CONTRACT,
    material,
    span_catalog,
    span_inputs,
    validated,
    validated_spans,
)
from app.transparent.engine import Engine, Rejected
from app.transparent.judge import DevelopmentJudge

pytest_plugins = ["test_engine"]

CASES = json.loads((Path(__file__).resolve().parents[2] / "fixtures/hookgw/span_cases.json").read_text(encoding="utf-8"))


def snapshot(text=None):
    return {"analysis_id": "synthetic-analysis", "evidence_contract": SPAN_CONTRACT,
            "user_request": canonical({"actual_user_turns_chronological": ["먼저 자료를 읽어줘.", text or CASES["normal_request"]], "latest_turn": 1}),
            "server_grant": {"comment_mode": "DEVELOPMENT", "workspace": "C:\\sogaeding"},
            "candidate": {"tool": "read_file", "args": {"path": "fixtures/hookgw/notes.txt"}, "route": "mcp"},
            "sources": [{"source_id": "synthetic-source", "same_issue": False, **material(text or "배포는 완료됐습니다.")} ]}


def observation(snap, view, source="candidate"):
    sid = next(r["span_id"] for r in span_catalog(snap, view)["spans"] if r["source_id"] == source)
    return {"task_relation": "DIRECT", "external_use": "NONE", "reason": "USER_INTENT_SUPPORTED", "evidence_span_ids": [sid]}


@pytest.mark.parametrize("text", CASES["texts"] + ["가" * 511 + "😀" + "다" * 513])
def test_full_exact_catalog_coverage_and_server_reconstruction(text):
    snap = snapshot(text)
    for view in ("A", "B"):
        catalog = span_inputs(snap, view)["evidence_catalog"]
        assert catalog["coverage_complete"] and catalog["snapshot_sha256"] == digest(canonical(snap))
        texts = {"user_request": snap["user_request"], "candidate": canonical(snap["candidate"])}
        if view == "B":
            texts["synthetic-source"] = snap["sources"][0]["analysis_text"]
        for source, exact in texts.items():
            rows = [r for r in catalog["spans"] if r["source_id"] == source]
            assert "".join(r["quote"] for r in rows) == exact
            assert all(exact[r["start"]:r["end"]] == r["quote"] and len(r["quote"]) <= 512 for r in rows)
            assert len({r["span_id"] for r in rows}) == len(rows)
        assert validated_spans(observation(snap, view), snap, view)["evidence_refs"]


def test_synthetic_wrapper_offset_problem_is_not_claimed_as_original_response():
    snap = snapshot()
    text = CASES["normal_request"]
    wrong = {"task_relation": "DIRECT", "external_use": "NONE", "reason": "USER_INTENT_SUPPORTED",
             "evidence_refs": [{"source_id": "user_request", "start": 0, "end": len(text), "quote": text}]}
    with pytest.raises(AnalysisFailure) as exc:
        validated(wrong, snap, "A")
    assert exc.value.diagnostics[0]["code"] == "QUOTE_MISMATCH"
    assert "quote" not in failure_details(exc.value, enriched=True)[0]
    assert failure_details(exc.value) == [{"code": "QUOTE_MISMATCH", "view": "A"}]
    assert validated_spans(observation(snap, "A", "user_request"), snap, "A")


@pytest.mark.parametrize("mutation", ["analysis_id", "user_request", "server_grant", "candidate", "sources"])
def test_stale_or_cross_snapshot_span_is_rejected(mutation):
    snap = snapshot()
    obs = observation(snap, "A")
    changed = json.loads(canonical(snap))
    if mutation in ("analysis_id", "user_request"):
        changed[mutation] += "changed"
    elif mutation == "sources":
        changed[mutation][0].update(material("사실이 바뀌었습니다."))
    else:
        changed[mutation]["extra"] = "changed"
    with pytest.raises(AnalysisFailure) as exc:
        validated_spans(obs, changed, "A")
    assert exc.value.diagnostics[0]["code"] == "UNKNOWN_SPAN"


def test_forged_unknown_cross_view_and_direct_model_offsets_rejected():
    snap = snapshot()
    for value, code in [(observation(snap, "B"), "SPAN_VIEW_MISMATCH"),
                        ({**observation(snap, "A"), "evidence_span_ids": ["s1A_" + "0" * 64]}, "UNKNOWN_SPAN"),
                        ({**observation(snap, "A"), "evidence_refs": []}, "INVALID_SCHEMA")]:
        with pytest.raises(AnalysisFailure) as exc:
            validated_spans(value, snap, "A")
        assert exc.value.diagnostics[0]["code"] == code


def test_incomplete_hash_collision_and_bounded_coverage_fail_closed():
    for kind, code in [("hash", "SOURCE_HASH_MISMATCH"), ("incomplete", "CATALOG_INCOMPLETE"), ("collision", "CATALOG_SOURCE_COLLISION"), ("limit", "CATALOG_INCOMPLETE")]:
        snap = snapshot()
        if kind == "hash":
            snap["sources"][0]["analysis_text_sha256"] = "wrong"
        elif kind == "incomplete":
            snap["sources"][0]["analysis_complete"] = False
        elif kind == "collision":
            snap["sources"][0]["source_id"] = "candidate"
        else:
            snap["user_request"] = "가" * 12000
        with pytest.raises(AnalysisFailure) as exc:
            span_catalog(snap, "B")
        assert exc.value.diagnostics[0]["code"] == code


def test_external_evidence_is_still_required_and_not_just_an_id():
    snap = snapshot()
    obs = {**observation(snap, "B"), "external_use": "TASK_DATA"}
    with pytest.raises(AnalysisFailure) as exc:
        validated_spans(obs, snap, "B")
    assert exc.value.diagnostics[0]["code"] == "B_EXTERNAL_EVIDENCE_REQUIRED"
    obs = {**observation(snap, "B", "synthetic-source"), "external_use": "TASK_DATA"}
    assert validated_spans(obs, snap, "B")


def test_both_views_diagnosed_and_same_turn_new_paths_cost_zero(engine):
    adapter = ObservationFixture()
    async def broken(snap):
        pair = await adapter.analyze(snap)
        pair[0]["evidence_span_ids"] = ["s1A_" + "0" * 64]
        return pair
    engine.judge.analyze = broken
    register(engine)
    assert authorize(engine)["diagnostic"][0]["code"] == "UNKNOWN_SPAN"
    context = json.loads(engine.history()[0]["reason"])
    assert context["view_checks"] == {"A": {"status": "INVALID_OR_UNAVAILABLE", "code": "UNKNOWN_SPAN"}, "B": {"status": "VALID"}}
    assert adapter.calls == 1
    for i, path in enumerate(("mcp", "mcp", "native")):
        register(engine, "retry" + str(i), path=path, args={"path": "changed" + str(i)})
        assert authorize(engine, "retry" + str(i))["reasons"] == ["TURN_ANALYSIS_STOPPED"]
    assert adapter.calls == 1
    engine.turn("machine", "session", "turn1", "Read the release and update normal code.", "C:\\repo")
    restarted = Engine(engine.path, engine.test_key, engine.grant, adapter)
    register(restarted, "after-restart")
    assert authorize(restarted, "after-restart")["reasons"] == ["TURN_ANALYSIS_STOPPED"]
    assert adapter.calls == 1
    restarted.turn("machine", "session", "turn2", "A new actual human request: read notes.", "C:\\repo")
    register(restarted, "fresh", turn="turn2", tool="read_file")
    assert authorize(restarted, "fresh")["decision"] == "ALLOW"
    assert adapter.calls == 2


def test_each_view_failure_preserved_without_canceling_other_view(engine):
    judge = object.__new__(DevelopmentJudge)
    invocations = []
    async def fake_observe(snap, view):
        invocations.append(view)
        if view == "A":
            raise AnalysisFailure("API_TIMEOUT", view)
        await asyncio.sleep(0)
        return observation(snap, view)
    judge.observe = fake_observe
    engine.judge = judge
    register(engine)
    assert authorize(engine)["diagnostic"] == [{"code": "API_TIMEOUT", "view": "A"}]
    assert set(invocations) == {"A", "B"}
    assert json.loads(engine.history()[0]["reason"])["view_checks"]["B"]["status"] == "VALID"
    register(engine, "retry")
    assert authorize(engine, "retry")["decision"] == "DENY"
    assert len(invocations) == 2  # no additional A/B adapter requests


def test_adapter_mutation_cannot_change_trusted_snapshot(engine):
    class Mutating:
        async def analyze(self, snap):
            snap["candidate"]["args"]["path"] = "different.txt"
            return [observation(snap, view) for view in ("A", "B")]
    engine.judge = Mutating()
    register(engine)
    result = authorize(engine)
    assert result["decision"] == "DENY"
    assert [x["code"] for x in result["diagnostic"]] == ["UNKNOWN_SPAN", "UNKNOWN_SPAN"]


def test_concurrent_retries_during_first_analysis_do_not_pay(engine):
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        count = 0
        class Waiting:
            async def analyze(self, snap):
                nonlocal count
                count += 1
                entered.set()
                await release.wait()
                raise AnalysisFailure("API_TIMEOUT", "A")
        engine.judge = Waiting()
        register(engine)
        first = asyncio.create_task(engine.authorize("machine", "c1"))
        await entered.wait()
        for i in range(4):
            call = "concurrent" + str(i)
            register(engine, call)
            assert (await engine.authorize("machine", call))["decision"] == "DENY"
        release.set()
        assert (await first)["decision"] == "DENY"
        register(engine, "later")
        assert (await engine.authorize("machine", "later"))["reasons"] == ["TURN_ANALYSIS_STOPPED"]
        assert count == 1
    asyncio.run(run())


def test_migration_stops_original_failed_turn_without_rewriting_call(engine):
    register(engine)
    authorize(engine)
    with engine.db() as db:
        reason = canonical({"reasons": ["ANALYSIS_UNAVAILABLE"], "diagnostic": [{"code": "QUOTE_MISMATCH", "view": "A"}]})
        db.execute("UPDATE calls SET state='DENIED',decision='DENY',reason=? WHERE id='c1'", (reason,))
    restarted = Engine(engine.path, engine.test_key, engine.grant, engine.judge)
    assert restarted.history()[0]["reason"] == reason
    register(restarted, "legacy-retry")
    assert authorize(restarted, "legacy-retry")["reasons"] == ["TURN_ANALYSIS_STOPPED"]


def test_metadata_disconnect_cannot_close_bound_or_other_machine_connection(engine):
    engine.connect("machine", "probe")
    with pytest.raises(Rejected):
        engine.disconnect_metadata("forged", "probe")
    assert engine.disconnect_metadata("machine", "probe")["state"] == "DISCONNECTED"
    engine.connect("machine", "bound")
    engine.connection("bound", "session")
    with pytest.raises(Rejected, match="ALREADY_BOUND"):
        engine.disconnect_metadata("machine", "bound")
