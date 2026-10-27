import asyncio

import pytest

from app.pdp.diagnostics import AnalysisFailure
from app.transparent.engine import Rejected
from app.transparent.gate_policy import POLICY, RULE
from app.transparent.jev_config import DEFAULT_PROFILE, make_policy
from app.transparent.jev_core_v5p1 import JevPolicyCurrent
from app.transparent.jev_gate6 import JevPolicyGate6


def candidate(engine, *, path="reports/draft.md", content="Requested draft."):
    engine.turn("m", "s", "t", "Write the draft to reports/draft.md.", "/files")
    return engine.register("m", "s", "t", "write", "write_file",
                           {"path": path, "content": content}, "mcp")


def test_default_is_common_gate6_and_old_policy_is_explicit(observer):
    assert DEFAULT_PROFILE == "gate-6"
    assert type(make_policy(observer)) is JevPolicyGate6
    assert make_policy(observer).policy == POLICY
    assert type(make_policy(observer, "current_candidate_1")) is JevPolicyCurrent


@pytest.mark.parametrize("confidence,expected",[(.499999,"ASK"),(.5,"ALLOW"),(.8,"ALLOW")])
def test_normal_candidate_keeps_positive50_and_raw_observations(engine, observer, confidence, expected):
    observer.b_confidence=confidence
    candidate(engine)
    assert asyncio.run(engine.authorize("m","write"))["decision"] == expected
    with engine.db() as db:
        context=engine.read_reason(db.execute("SELECT reason FROM calls WHERE id='write'").fetchone()[0])
    assert context["policy_trace"]["decision_rule_version"] == RULE
    assert context["policy_trace"]["risk_threshold"] == .9


@pytest.mark.parametrize("kind,a,b,ac,bc,expected",[
    ("SENSITIVE_RESOURCE_REQUIRES_CONSENT","WITHIN_TASK","LEGITIMATE",1.,.8,"ASK"),
    ("OUTSIDE_TASK_CAPABILITY_REQUIRES_CONSENT","WITHIN_TASK","LEGITIMATE",.5,.5,"ASK"),
    ("SENSITIVE_RESOURCE_REQUIRES_CONSENT","WITHIN_TASK","LEGITIMATE",.499,.8,"DENY"),
    ("SENSITIVE_RESOURCE_REQUIRES_CONSENT","WITHIN_TASK","UNCERTAIN",1.,.8,"DENY"),
    ("SENSITIVE_RESOURCE_REQUIRES_CONSENT","OUTSIDE_TASK","LEGITIMATE",.6,.8,"DENY"),
    ("PRIVATE_MUTATION_REQUIRES_CONSENT","WITHIN_TASK","LEGITIMATE",.6,.8,"ALLOW"),
    ("PRIVATE_MUTATION_REQUIRES_CONSENT","WITHIN_TASK","LEGITIMATE",.499,.8,"ASK"),
    ("PRIVATE_MUTATION_REQUIRES_CONSENT","WITHIN_TASK","EXTERNAL_ADOPTION",1.,.6,"DENY"),
])
def test_product_gate6_held_cases(engine_factory,observer,kind,a,b,ac,bc,expected):
    engine=engine_factory({"reports/draft.md":[kind]})
    observer.a,observer.b=a,b
    observer.a_confidence,observer.b_confidence=ac,bc
    candidate(engine)
    result=asyncio.run(engine.authorize("m","write"))
    assert result["decision"] == expected
    assert len(observer.calls)==2
    if expected != "ALLOW":
        with pytest.raises(Rejected):
            engine.forward("m","write")
    if expected == "DENY":
        with pytest.raises(Rejected):
            engine.approval("m","write",True)


def test_risk_hold_answer_is_exact_and_single_use(engine_factory):
    engine=engine_factory({"reports/draft.md":["SENSITIVE_RESOURCE_REQUIRES_CONSENT"]})
    engine.connect('m','synthetic-connection')
    engine.connection('synthetic-connection','s')
    candidate(engine)
    assert asyncio.run(engine.authorize("m","write",ask_connection='synthetic-connection'))["decision"] == "ASK"
    with pytest.raises(Rejected):
        engine.approval('m','write',True)
    ask=engine.pending_ask('m','s','synthetic-connection','write_file',{'path':'reports/draft.md','content':'Requested draft.'})['ask']
    engine.ask_presented('m','synthetic-connection',ask['ask_id'],ask['nonce'])
    assert asyncio.run(engine.answer_ask('m','synthetic-connection',ask['ask_id'],ask['nonce'],'YES'))['decision']=='ALLOW'
    engine.forward("m","write")
    with pytest.raises(Rejected):
        engine.forward("m","write")
    with engine.db() as db:
        assert db.execute("SELECT consumed FROM asks").fetchone()[0] == 1


@pytest.mark.parametrize("path",["../outside.txt",".env","secret.key"])
def test_server_rules_cannot_relax_secret_path_or_bad_schema(engine,observer,path):
    candidate(engine,path=path)
    result=asyncio.run(engine.authorize("m","write"))
    assert result["decision"] == "DENY" and observer.calls == []
    with pytest.raises(Rejected):
        engine.forward("m","write")


def test_unknown_consent_rule_fails_closed(engine_factory,observer):
    engine=engine_factory({"reports/draft.md":["EXTERNAL_APPROVAL_CLAIM"]})
    candidate(engine)
    result=asyncio.run(engine.authorize("m","write"))
    assert result["decision"] == "DENY" and observer.calls == []


def test_risk_hold_read_does_not_take_public_read_shortcut(engine_factory,observer):
    engine=engine_factory({"docs/private.md":["SENSITIVE_RESOURCE_REQUIRES_CONSENT"]})
    engine.turn("m","s","t","Read the requested document.","/files")
    engine.register("m","s","t","read","read_file",{"path":"docs/private.md"},"mcp")
    assert asyncio.run(engine.authorize("m","read"))["decision"] == "ASK"
    assert len(observer.calls)==2


def test_source_tamper_is_rejected_before_semantic_call(engine,observer):
    # A directly called policy must validate the complete snapshot, too.
    from app.common import canonical
    from app.pdp.semantic import material
    source={"source_id":"x","call_id":"r","same_issue":False,**material("Facts.")}
    source["analysis_text"]="Changed facts."
    value={"analysis_id":"x","user_request":canonical({"actual_user_turns_chronological":["Write a draft."],"latest_turn":0}),
           "candidate":{"tool":"write_file","route":"mcp","args":{"path":"reports/draft.md","content":"Draft."}},
           "sources":[source],"server_grant":{**engine.grant,"comment_mode":"DEVELOPMENT"},
           "observation_context":{"actual_turns":["Write a draft."],"current_turn":0,"source_events":[
               {"source_id":"x","call_id":"r","turn_index":0,"route":"mcp","tool":"read_file","target":"docs/input.md","result_role":"READ_RESULT"}]}}
    with pytest.raises(AnalysisFailure):
        asyncio.run(make_policy(observer).evaluate(value))
    assert observer.calls == []
