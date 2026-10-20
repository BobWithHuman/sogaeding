import json
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, AuthenticationError
from test_decisions import FakeJudge, call, read, session

from app.common import SafeError, canonical
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.judge import OpenAIJudge
from app.pdp.semantic import inputs, validated


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,code,view", [
    ("schema", "INVALID_SCHEMA", "B"), ("source", "UNKNOWN_SOURCE", "B"),
    ("bounds", "QUOTE_BOUNDS", "B"), ("quote", "QUOTE_MISMATCH", "B"),
    ("same_issue", "B_SAME_ISSUE_REQUIRED", "B"),
    ("a_source", "A_EXTERNAL_SOURCE", "A"), ("a_use", "A_EXTERNAL_USE", "A"),
    ("b_external", "B_EXTERNAL_EVIDENCE_REQUIRED", "B"),
    ("no_refs", "EVIDENCE_REQUIRED", "A"),
])
async def test_validation_failure_diagnostics_preserve_deny_and_zero_execution(repo, failure, code, view):
    s = session(repo)
    read(repo, s)

    class BadJudge(FakeJudge):
        async def analyze(self, snapshot):
            a, b = await super().analyze(snapshot)
            if failure == "schema":
                b["raw_error"] = "must-not-be-persisted"
            elif failure == "source":
                b["evidence_refs"][0]["source_id"] = "forged-id"
            elif failure == "bounds":
                b["evidence_refs"][0]["end"] = 999999
            elif failure == "quote":
                b["evidence_refs"][0]["quote"] = "wrong quote must-not-be-persisted"
            elif failure == "same_issue":
                b["external_use"] = "NONE"
                b["evidence_refs"] = a["evidence_refs"]
            elif failure == "a_source":
                a["evidence_refs"] = b["evidence_refs"]
            elif failure == "a_use":
                a["external_use"] = "TASK_DATA"
            elif failure == "b_external":
                b["evidence_refs"] = a["evidence_refs"]
            else:
                a["evidence_refs"] = []
            return a, b

    value = call(s)
    result = await repo.check_async(value, BadJudge())
    assert result["decision"] == "DENY" and result["reason_codes"] == ["ANALYSIS_UNAVAILABLE"]
    assert result["approval_id"] is None
    with pytest.raises(SafeError):
        repo.reserve(result["call_id"], {key: value[key] for key in ("tool_name", "backend_id", "args")})
    report = repo.analysis_diagnostics(s["session_id"])
    assert report["analyses"][0]["diagnostics"] == [{"code": code, "view": view}]
    assert "must-not-be-persisted" not in canonical(report) + canonical(repo.timeline(s["session_id"]))
    with repo.tx() as db:
        assert db.execute("SELECT count(*) FROM executions e JOIN calls c ON c.id=e.call_id WHERE c.session_id=? AND c.tool_name='post_issue_comment'", (s["session_id"],)).fetchone()[0] == 0


@pytest.mark.asyncio
async def test_legacy_details_not_invented_and_lease_reason_is_preserved(repo):
    s = session(repo)
    read(repo, s)
    value = call(s)
    _, snapshot = repo.prepare_check(value, "fake-only")
    with repo.tx() as db:
        db.execute("UPDATE analyses SET lease_until=0 WHERE id=?", (snapshot["analysis_id"],))
    result = repo.finish_analysis(snapshot)
    assert result["reason_codes"] == ["ANALYSIS_UNAVAILABLE"]
    assert repo.analysis_diagnostics(s["session_id"])["analyses"][0]["diagnostics"][0]["code"] == "LEASE_EXPIRED"
    with repo.tx() as db:
        saved = {"decision": "DENY", "reason_codes": ["ANALYSIS_UNAVAILABLE"], "evidence_refs": []}
        db.execute("UPDATE analyses SET result_cipher=? WHERE id=?", (repo.encrypt(canonical(saved)), snapshot["analysis_id"]))
    assert repo.analysis_diagnostics(s["session_id"])["analyses"][0]["diagnostics"][0]["code"] == "DETAIL_NOT_RECORDED"


def test_unicode_copyable_spans_and_explicit_candidate_text(repo):
    s = session(repo)
    read(repo, s, text="배포😀 현황\r\n배포가 완료되었습니다.")
    _, snapshot = repo.prepare_check(call(s), "fake-only")
    a, b = inputs(snapshot, "A"), inputs(snapshot, "B")
    assert "sources" not in a and "sources" in b
    assert a["evidence_texts"]["candidate"] == canonical(snapshot["candidate"])
    for ref in b["sources"][0]["evidence_spans"]:
        observation = {"task_relation": "DATA_DEPENDENT", "external_use": "TASK_DATA",
                       "reason": "TASK_DATA_SUPPORTED", "evidence_refs": [ref]}
        assert validated(observation, snapshot, "B") == observation


def test_short_line_reference_helpers_are_bounded_without_truncating_source(repo):
    s = session(repo)
    source_text = "a\n" * 4096
    read(repo, s, text=source_text)
    _, snapshot = repo.prepare_check(call(s), "fake-only")
    value = inputs(snapshot, "B")
    assert value["sources"][0]["analysis_text"] == source_text
    assert len(value["sources"][0]["evidence_spans"]) == 8
    assert len(canonical(value).encode()) < 131072


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,code", [("timeout", "API_TIMEOUT"), ("auth", "API_AUTHENTICATION"),
                                           ("refusal", "MODEL_REFUSAL"), ("json", "INVALID_JSON")])
async def test_actual_adapter_with_offline_sdk_spy(tmp_path, monkeypatch, failure, code):
    import app.pdp.judge as module
    captured = []

    class Client:
        def __init__(self, **kwargs):
            captured.append(kwargs)
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def create(self, **kwargs):
            captured.append(kwargs)
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            if failure == "timeout":
                raise APITimeoutError(request=request)
            if failure == "auth":
                raise AuthenticationError("private-api-error", response=httpx.Response(401, request=request), body=None)
            content = SimpleNamespace(type="refusal" if failure == "refusal" else "output_text")
            return SimpleNamespace(status="completed", usage=None, output_text="invalid-private-text",
                                   output=[SimpleNamespace(type="message", content=[content])])

    monkeypatch.setattr(module, "AsyncOpenAI", Client)
    monkeypatch.setattr(module, "secret_file", lambda label: "fake-key-for-offline-spy")
    judge = OpenAIJudge(tmp_path / "budget.sqlite3")
    snapshot = {"analysis_id": "offline-analysis", "user_request": "요약", "server_grant": {}, "candidate": {}}
    with pytest.raises(AnalysisFailure) as caught:
        await judge.observe(snapshot, "A")
    assert caught.value.diagnostics == [{"code": code, "view": "A"}]
    assert captured[0]["base_url"] == "https://api.openai.com/v1" and captured[0]["max_retries"] == 0
    assert captured[1]["tools"] == [] and captured[1]["store"] is False and captured[1]["max_output_tokens"] == 2048
    assert judge.budget_summary()["requests_attempted"] == 1
    assert "private" not in json.dumps(judge.usage)


def test_usage_read_preserves_existing_twelve_attempts_and_budget(tmp_path):
    judge = OpenAIJudge(tmp_path / "budget.sqlite3")
    for index in range(12):
        judge.claim(str(index), "A")
    assert judge.budget_summary()["remaining"] == 12
    assert judge.budget_summary()["remaining"] == 12
    for index in range(12, 24):
        judge.claim(str(index), "B")
    with pytest.raises(AnalysisFailure):
        judge.claim("over-budget", "B")
    assert judge.budget_summary()["requests_attempted"] == 24
