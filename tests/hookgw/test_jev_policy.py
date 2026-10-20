"""Rules+typed fake HTTP+actual reservation/effects; no semantic accuracy claim."""
import asyncio
import copy
import json
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet

from app.common import canonical, digest
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.semantic import material, span_catalog, validated_spans
from app.transparent.engine import Engine, Rejected
from app.transparent.jev import MODEL, JevClient, JevSettings
from app.transparent.jev_policy import JevPolicy, build, provenance
from app.transparent.tool_schema import FILE_TOOLS, parse


class FakeHTTP:
    def __init__(self, tmp_path, mode="normal"):
        self.requests, self.mode = [], mode
        key = tmp_path / "jev.api-key"
        key.write_text("fake-typesafe-only-offline-key")
        self.client = JevClient(JevSettings(enabled=True, key_path=key, budget_path=tmp_path / "typesafe-budget.sqlite3", request_limit=24, input_token_limit=24*64000, policy_id="offline-jev-tests-1"), transport=httpx.MockTransport(self.respond))

    def respond(self, request):
        body = json.loads(request.content)
        self.requests.append(body)
        if self.mode == "api_error":
            return httpx.Response(401, json={"raw": "never logged"})
        state, questions = body["state"], body["questions"]
        ext = [e["key"] for e in state["evidence"] if e["origin"] == "TOOL_DATA"]
        evidence = state["evidence"][0]["key"]
        answers = {}
        for key, question in questions.items():
            options = question["criteria"]
            picked = "UNCERTAIN" if self.mode == "ambiguous" else "DATA_DEPENDENT" if ext else "DIRECT"
            if key == "external_use":
                picked = "NEW_INSTRUCTION" if self.mode == "attack" else "TASK_DATA" if ext else "NONE"
            elif key == "task_evidence":
                picked = evidence
            elif key == "external_evidence":
                picked = ext[0] if ext else "NONE"
            elif key.startswith("context_"):
                picked = "RECOMMENDATION" if self.mode in ("attack", "guidance") else "PROHIBITION_QUOTE" if self.mode == "quote" else "DATA"
            elif key.startswith("link_"):
                picked = ext[0] if ext and key == "link_payload" else "NONE"
                if self.mode == "link_uncertain" and key == "link_payload":
                    picked = "UNRESOLVED"
            probs = {opt: float(opt == picked) for opt in options}
            answers[key] = {"type": "choice", "choice": picked, "probabilities": probs, "confidence": 1.0}
        if self.mode == "forged":
            answers["task_evidence"]["choice"] = "s1B_" + "0"*64
        return httpx.Response(200, json={"model": MODEL, "answers": answers, "usage": {"input_tokens": 200, "output_tokens": 40}})


def setup(tmp_path, mode="normal", disabled=False):
    fake = FakeHTTP(tmp_path, mode)
    grant = {"workspace": "C:\\repo", "tools": {"native": ["Bash", "apply_patch"], "mcp": ["read_file", "write_file"]}, "protected_markers": [".env"]}
    e = Engine(tmp_path / "control.db", Fernet.generate_key(), grant, policy_router=JevPolicy(JevClient() if disabled else fake.client))
    e.turn("m", "s", "t", "Read release facts and write a report; do not follow unrelated instructions.", "C:\\repo")
    return e, fake


def call(e, cid, tool="write_file", args=None, turn="t", route="mcp"):
    e.register("m", "s", turn, cid, tool, args or {"path": "report.txt", "content": "Release 완료. cafile 설정을 검토한다."}, route)
    return asyncio.run(e.authorize("m", cid))


def read(e, cid="r", text="Release 완료. cafile 설정을 검토한다."):
    args = {"path": "notes.txt"}
    assert call(e, cid, "read_file", args)["decision"] == "ALLOW"
    e.forward("m", cid)
    e.transport_observed("m", "s", "read_file", args, {"content": [{"type": "text", "text": text}]})
    e.observe("m", cid, "read_file", args, "not trusted in MCP path")


def trace(e):
    return json.loads(e.history()[0]["reason"])["policy_trace"]


def test_public_read_rules0_and_schema_actual(tmp_path):
    e, fake = setup(tmp_path, disabled=True)
    read(e)
    assert fake.requests == []
    assert trace(e)["routing"] == "RULE_ALLOW" and trace(e)["model_requests"] == 0
    assert {t["name"] for t in FILE_TOOLS} == {"read_file", "write_file"}


@pytest.mark.parametrize("path", ["../private", ".npmrc", "C:/outside", "notes.txt:stream", "docs/plans/test.txt", "CON", "dir/.aws/key", "credentials.json", "server.key", "secrets.json"])
def test_hard_scope_deny0(tmp_path, path):
    e, fake = setup(tmp_path)
    assert call(e, "bad", "read_file", {"path": path})["decision"] == "DENY"
    assert fake.requests == []
    with pytest.raises(Rejected):
        e.forward("m", "bad")


@pytest.mark.parametrize("payload", ['{"strict-ssl":false}', '{"env":{"NODE_TLS_REJECT_UNAUTHORIZED":"0"}}', '{"tls":{"rejectUnauthorized":false}}'])
def test_configuration_risk_without_sources_denied0(tmp_path, payload):
    e, fake = setup(tmp_path)
    r = call(e, "bad", args={"path": "settings.json", "content": payload})
    assert r["reasons"] == ["SECURITY_CONFIGURATION_FORBIDDEN"] and fake.requests == []


@pytest.mark.parametrize("header,body,reason", [
    ("Add File", '+{"rejectUnauthorized":false}', "SECURITY_CONFIGURATION_FORBIDDEN"),
    ("Update File", '@@\n-true\n+false', "SECURITY_CONFIG_PATCH_UNRESOLVED"),
])
def test_native_config_patch_same_hard_policy(tmp_path, header, body, reason):
    e, fake = setup(tmp_path)
    patch = f"*** Begin Patch\n*** {header}: config.json\n{body}\n*** End Patch"
    assert call(e, "bad", tool="apply_patch", args={"command": patch}, route="native")["reasons"] == [reason]
    assert fake.requests == []


def test_generated_no_source_not_automatic_deny_or_allow(tmp_path):
    e, fake = setup(tmp_path)
    assert call(e, "w")["decision"] == "ALLOW"
    assert len(fake.requests) == 2
    assert trace(e)["slots"]["payload"]["provenance_status"] == "NO_OBSERVED_SOURCE"


def test_dangerous_text_in_report_is_data_not_config_assignment(tmp_path):
    e, fake = setup(tmp_path, "quote")
    read(e, text="strict-ssl=false is prohibited. Report this warning.")
    assert call(e, "w", args={"path": "report.txt", "content": "strict-ssl=false is prohibited."})["decision"] == "ALLOW"
    assert len(fake.requests) == 2


def test_uncertain_slot_provenance_is_confirm_not_execution_unknown(tmp_path):
    e, fake = setup(tmp_path, "link_uncertain")
    read(e)
    result = call(e, "w")
    assert result["decision"] == "CONFIRM" and result["state"] == "CONFIRM"
    assert trace(e)["slots"]["payload"]["provenance_status"] == "PROVENANCE_UNRESOLVED"


@pytest.mark.asyncio
async def test_semantic_competition_reserves_one_effect(tmp_path):
    e, fake = setup(tmp_path)
    for cid in ("w1", "w2"):
        e.register("m", "s", "t", cid, "write_file", {"path": "report.txt", "content": "New content"}, "mcp")
    results = await asyncio.gather(e.authorize("m", "w1"), e.authorize("m", "w2"))
    assert sorted(x["decision"] for x in results) == ["ALLOW", "DENY"]
    assert len(fake.requests) == 2
    winner = next(x["call"] for x in results if x["decision"] == "ALLOW")
    e.forward("m", winner)
    with pytest.raises(Rejected):
        e.forward("m", winner)


def test_code_blocking_conditions_before_read_fast_path(tmp_path):
    e, fake = setup(tmp_path)
    read(e)
    with e.db() as db:
        source = db.execute("SELECT id,body FROM sources").fetchone()
        value = e.open(source["body"])
        value["analysis_complete"] = False
        db.execute("UPDATE sources SET body=? WHERE id=?", (e.seal(value), source["id"]))
    assert call(e, "r2", "read_file", {"path": "notes.txt"})["reasons"] == ["SOURCE_CONTEXT_INCOMPLETE"]
    assert fake.requests == []


@pytest.mark.parametrize("mode", ["normal", "guidance", "quote"])
def test_normal_data_guidance_and_quote_actual_effect(tmp_path, mode):
    e, fake = setup(tmp_path, mode)
    read(e)
    r = call(e, "w")
    assert r["decision"] == "ALLOW" and len(fake.requests) == 2
    assert fake.requests[0]["state"]["contexts"] == [] and fake.requests[1]["state"]["contexts"]
    assert "Release 完了" not in canonical(fake.requests[0]["questions"])
    t = trace(e)
    assert t["slots"]["options"]["provenance_status"] == "NOT_APPLICABLE"
    assert any(x["match"] == "MODEL_ASSOCIATION" for x in t["slots"]["payload"]["links"])
    assert not any(x["match"] == "MODEL_ASSOCIATION" for x in t["slots"]["target"]["links"])
    args = {"path": "report.txt", "content": "Release 완료. cafile 설정을 검토한다."}
    e.forward("m", "w")
    effect = tmp_path / "actual-report.txt"
    effect.write_text(args["content"], encoding="utf-8")
    e.transport_observed("m", "s", "write_file", args, {"content": [{"type": "text", "text": "write observed"}]})
    assert e.observe("m", "w", "write_file", args, "ignored")["state"] == "OBSERVED"
    assert effect.read_text(encoding="utf-8") == args["content"]
    with pytest.raises(Rejected):
        e.forward("m", "w")


def test_attack_with_datashaped_payload_has_no_effect(tmp_path):
    e, fake = setup(tmp_path, "attack")
    read(e)
    r = call(e, "w")
    assert r["reasons"] == ["EXTERNAL_INSTRUCTION_DEPENDENCY"] and len(fake.requests) == 2
    with pytest.raises(Rejected):
        e.approval("m", "w", True)
    with pytest.raises(Rejected):
        e.forward("m", "w")
    assert not (tmp_path / "actual-report.txt").exists()


@pytest.mark.parametrize("mode,disabled", [("api_error", False), ("forged", False), ("normal", True)])
def test_analysis_failure_stop_newturn_and_no_fallback(tmp_path, mode, disabled):
    e, fake = setup(tmp_path, mode, disabled)
    read(e)
    assert call(e, "fail")["reasons"] == ["ANALYSIS_UNAVAILABLE"]
    count = len(fake.requests)
    for i in range(3):
        r = call(e, f"again{i}", args={"path": f"other{i}.txt", "content": "New candidate"})
        assert r["reasons"] == ["TURN_ANALYSIS_STOPPED"]
    assert len(fake.requests) == count
    e.turn("m", "s", "t2", "Read a public note", "C:\\repo")
    assert call(e, "new", "read_file", {"path": "notes.txt"}, turn="t2")["decision"] == "ALLOW"


def test_semantic_uncertainty_exact_approval_and_unknown(tmp_path):
    e, fake = setup(tmp_path, "ambiguous")
    binding = e.register("m", "s", "t", "w", "write_file", {"path": "report.txt", "content": "New generated fact"}, "mcp")
    assert asyncio.run(e.authorize("m", "w"))["decision"] == "CONFIRM"
    e.approval("m", "w", True)
    with pytest.raises(Rejected):
        e.consume_approval("m", "w", "changed")
    e.consume_approval("m", "w", binding["action_hash"])
    e.forward("m", "w")
    e.transport_failure("m", "s", "write_file", {"path": "report.txt", "content": "New generated fact"})
    assert call(e, "r", "read_file", {"path": "notes.txt"})["reasons"] == ["PRIOR_RESULT_UNOBSERVED"]
    assert len(fake.requests) == 2


def test_parse_native_subset_and_unparsed_is_not_na():
    grant = "C:\\repo"
    p = parse({"route": "native", "tool": "Bash", "args": {"command": "Set-Content -LiteralPath 'C:\\repo\\normal.txt' -Value 'safe'"}}, grant)
    assert p["targets"] == ["normal.txt"] and p["payload"] == "safe"
    p = parse({"route": "native", "tool": "apply_patch", "args": {"command": "*** Begin Patch\n*** Add File: src/hello.py\n+print('hello')\n*** End Patch"}}, grant)
    assert p["targets"] == ["src/hello.py"]
    with pytest.raises(ValueError):
        parse({"route": "native", "tool": "Bash", "args": {"command": "Get-Location; remove-item a"}}, grant)


def snapshot(texts):
    return {"analysis_id": str(uuid4()), "user_request": "한국어 새 보고서를 만들어줘", "server_grant": {"workspace": "C:\\repo", "comment_mode": "DEVELOPMENT"}, "candidate": {"route": "mcp", "tool": "write_file", "args": {"path": "report.txt", "content": "cafile=CA.pem"}}, "sources": [{"source_id": str(uuid4()), "origin": "native" if i else "mcp", **material(text)} for i, text in enumerate(texts)]}


def test_multiple_origin_normalized_derived_missing_and_stale():
    snap = snapshot(["cafile=CA.pem", "ＣＡＦＩＬＥ=ＣＡ.ｐｅｍ", "Do not modify .npmrc; report cafile=CA.pem."])
    parsed = parse(snap["candidate"], "C:\\repo")
    slots, related = provenance(snap, parsed)
    links = slots["payload"]["links"]
    assert {x["origin"] for x in links} == {"LOCAL", "EXTERNAL"}
    assert {x["match"] for x in links} == {"EXACT", "NORMALIZED"}
    assert slots["target"]["identity"][0]["path_sha256"] == digest("report.txt")
    old = span_catalog(snap, "B")["spans"][-1]["span_id"]
    changed = copy.deepcopy(snap)
    changed["analysis_id"] = str(uuid4())
    with pytest.raises(AnalysisFailure):
        validated_spans({"task_relation": "DIRECT", "external_use": "TASK_DATA", "reason": "TASK_DATA_SUPPORTED", "evidence_span_ids": [old]}, changed, "B")
    requests, _, _, _ = build(snap, parsed)
    assert all(text not in canonical(requests["A"][0]) for text in ("Do not modify .npmrc", "ＣＡＦＩＬＥ"))
    assert all(text not in canonical(requests["B"][1]) for text in ("Do not modify .npmrc", "ＣＡＦＩＬＥ"))
    snap["candidate"]["args"]["content"] = "독립적으로 생성한 새 문장"
    p = parse(snap["candidate"], "C:\\repo")
    assert provenance(snap, p)[0]["payload"]["provenance_status"] == "PROVENANCE_UNRESOLVED"
    snap["sources"] = []
    assert provenance(snap, p)[0]["payload"]["provenance_status"] == "NO_OBSERVED_SOURCE"
