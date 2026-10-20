"""Explicit fake TypeSafe HTTP only; the production OpenAI ledger is never opened."""

import asyncio
import copy
import json
import sqlite3

import httpx
import pytest

from app.pdp.diagnostics import AnalysisFailure
from app.transparent.jev import (
    ENDPOINT,
    MODEL,
    RESERVED_INPUT_TOKENS,
    JevClient,
    JevSettings,
    validate_response,
)

QUESTIONS = {
    "relation": {"type": "choice", "instructions": "How does the candidate relate to the user turn?",
                 "criteria": {"direct": "Directly requested", "unclear": "Unclear"}},
    "instruction": {"type": "noul", "instructions": "Does the supplied span direct execution?"},
}
ANSWER = {"model": MODEL, "answers": {
    "relation": {"type": "choice", "choice": "direct", "probabilities": {"direct": 0.9, "unclear": 0.1}, "confidence": 0.8},
    "instruction": {"type": "noul", "noul": 0.1},
}, "usage": {"input_tokens": 500, "output_tokens": 40}}


@pytest.fixture
def config(tmp_path):
    key = tmp_path / "jev.api-key"
    key.write_text("fake-typesafe-key-for-offline-tests", encoding="ascii")
    return JevSettings(enabled=True, key_path=key, budget_path=tmp_path / "typesafe-budget.sqlite3",
                       request_limit=4, input_token_limit=4 * RESERVED_INPUT_TOKENS,
                       policy_id="offline-fake-policy-1")


def rows(config):
    with sqlite3.connect(config.budget_path) as db:
        return db.execute("SELECT analysis_id,view,status,input_reserved,usage FROM jev_attempts ORDER BY analysis_id,view").fetchall()


@pytest.mark.asyncio
async def test_fake_http_pinned_wire_separate_views_and_preclaim(config, monkeypatch):
    captured = []
    monkeypatch.setenv("HTTPS_PROXY", "https://untrusted.invalid")
    async def handler(request):
        assert len(rows(config)) == len(captured) + 1  # claimed before any outbound bytes
        value = json.loads(request.content)
        assert str(request.url) == ENDPOINT
        assert request.headers["authorization"] == "Bearer fake-typesafe-key-for-offline-tests"
        assert value["model"] == MODEL
        assert "TypeSafe-Danger-Zone-Long-Context" not in request.headers
        captured.append(value)
        return httpx.Response(200, json=copy.deepcopy(ANSWER))
    client = JevClient(config, transport=httpx.MockTransport(handler))
    assert await client.observe("A", {"user": "요약해줘", "ref": "e0"}, QUESTIONS, "fake-pair") == ANSWER["answers"]
    assert await client.observe("B", {"user": "요약해줘", "source": "외부 배포 사실"}, QUESTIONS, "fake-pair") == ANSWER["answers"]
    assert "source" not in captured[0]["state"]
    assert captured[1]["state"]["source"] == "외부 배포 사실"
    assert [r[2] for r in rows(config)] == ["COMPLETED", "COMPLETED"]
    assert sum(r[3] for r in rows(config)) == 128000


@pytest.mark.asyncio
async def test_server_uppercase_option_enums_and_short_evidence_keys(config):
    questions = {
        "relation": {"type": "choice", "instructions": "Choose the relation.",
                     "criteria": {"DIRECT": "Requested", "DATA_DEPENDENT": "Uses external facts", "UNCERTAIN": "Unclear"}},
        "evidence": {"type": "choice", "instructions": "Select supporting evidence.",
                     "criteria": {"e0": "First relevant span", "NONE": "No evidence"}},
    }
    response = {"model": MODEL, "answers": {
        "relation": {"type": "choice", "choice": "DATA_DEPENDENT",
                     "probabilities": {"DIRECT": 0.1, "DATA_DEPENDENT": 0.9, "UNCERTAIN": 0}, "confidence": 0.85},
        "evidence": {"type": "choice", "choice": "e0", "probabilities": {"e0": 1, "NONE": 0}, "confidence": 1},
    }, "usage": {"input_tokens": 10, "output_tokens": 5}}
    client = JevClient(config, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    observed = await client.observe("B", "사실 자료", questions, "upper")
    expected = copy.deepcopy(response["answers"])
    expected["relation"]["confidence"] = pytest.approx(0.85)
    assert observed == expected
    assert observed["relation"]["confidence"] <= response["answers"]["relation"]["confidence"]


@pytest.mark.asyncio
async def test_default_disabled_and_no_approval_limits_never_create_ledger(config):
    count = 0
    def handler(_):
        nonlocal count
        count += 1
        return httpx.Response(200, json=ANSWER)
    candidates = [JevSettings(), JevSettings(enabled=True),
                  JevSettings(**{**config.__dict__, "policy_id": None}),
                  JevSettings(**{**config.__dict__, "model": "jev-latest"}),
                  JevSettings(**{**config.__dict__, "request_limit": True})]
    for settings in candidates:
        with pytest.raises(AnalysisFailure):
            await JevClient(settings, transport=httpx.MockTransport(handler)).observe("A", "data", QUESTIONS, "id")
    assert count == 0 and not config.budget_path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [302, 400, 401, 403, 413, 422, 429, 500, 529])
async def test_error_no_retry_no_refund_no_body_leak(config, status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"location": "https://untrusted.invalid"}, text="PRIVATE_RESPONSE_DO_NOT_RECORD")
    client = JevClient(config, transport=httpx.MockTransport(handler))
    with pytest.raises(AnalysisFailure) as error:
        await client.observe("A", "data", QUESTIONS, "id")
    assert "PRIVATE" not in str(error.value) and len(calls) == 1
    assert rows(config)[0][2:4] == ("FAILED", RESERVED_INPUT_TOKENS)
    with pytest.raises(AnalysisFailure):
        await client.observe("A", "data", QUESTIONS, "id")
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(model="jev-1.14.0"),
    lambda v: v.update(extra="unexpected"),
    lambda v: v["answers"].pop("instruction"),
    lambda v: v["answers"].update(unrequested={"type": "noul", "noul": 1}),
    lambda v: v["answers"]["instruction"].update(confidence=1),
    lambda v: v["answers"]["instruction"].update(noul=True),
    lambda v: v["answers"]["instruction"].update(noul=float("nan")),
    lambda v: v["answers"]["instruction"].update(noul=float("inf")),
    lambda v: v["answers"]["instruction"].update(noul=-1),
    lambda v: v["answers"]["instruction"].update(noul=10 ** 1000),
    lambda v: v["answers"]["relation"].update(type="score"),
    lambda v: v["answers"]["relation"].update(choice="unclear"),
    lambda v: v["answers"]["relation"].update(confidence=0.99),
    lambda v: v["answers"]["relation"]["probabilities"].update(direct=0.8),
    lambda v: v["answers"]["relation"]["probabilities"].update(forged=0),
    lambda v: v["usage"].update(input_tokens=True),
    lambda v: v["usage"].update(input_tokens=64001),
    lambda v: v["usage"].update(output_tokens=-1),
    lambda v: v["usage"].update(output_tokens=1000001),
])
def test_strict_typed_numeric_response(mutation):
    value = copy.deepcopy(ANSWER)
    mutation(value)
    with pytest.raises(ValueError):
        validate_response(value, QUESTIONS)


@pytest.mark.asyncio
@pytest.mark.parametrize("body,ctype", [(b'{"model":1,"model":2}', "application/json"),
                                       (b'{"bad":NaN}', "application/json"),
                                       (b'x' * 65537, "application/json"),
                                       (b'{}', "text/html")])
async def test_invalid_bounded_wire(config, body, ctype):
    client = JevClient(config, transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body, headers={"content-type": ctype})))
    with pytest.raises(AnalysisFailure):
        await client.observe("A", "data", QUESTIONS, "id")
    assert rows(config)[0][2] == "FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["DEMO_SECRET_DO_NOT_SEND", "x" * 24576,
                                    {"password": "private"}, "fake-typesafe-key-for-offline-tests"])
async def test_sensitive_and_oversize_input_preclaim(config, state):
    def never(_):
        pytest.fail("No outbound request expected")
    with pytest.raises(AnalysisFailure):
        await JevClient(config, transport=httpx.MockTransport(never)).observe("A", state, QUESTIONS, "id")
    assert not config.budget_path.exists()


@pytest.mark.asyncio
async def test_policy_binding_and_exhausted_budget_no_renewal(config):
    settings = JevSettings(**{**config.__dict__, "request_limit": 1})
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=ANSWER)
    client = JevClient(settings, transport=httpx.MockTransport(handler))
    await client.observe("A", "data", QUESTIONS, "first")
    for changed in [settings, config, JevSettings(**{**settings.__dict__, "policy_id": "another"})]:
        with pytest.raises(AnalysisFailure):
            await JevClient(changed, transport=httpx.MockTransport(handler)).observe("A", "data", QUESTIONS, "second")
    assert len(calls) == 1 and len(rows(config)) == 1


@pytest.mark.asyncio
async def test_foreign_existing_ledger_rejected(config):
    with sqlite3.connect(config.budget_path) as db:
        db.execute("CREATE TABLE attempts (id INTEGER)")
        db.execute("INSERT INTO attempts VALUES (22)")
    with pytest.raises(AnalysisFailure):
        await JevClient(config, transport=httpx.MockTransport(lambda _: pytest.fail("No HTTP"))).observe("A", "data", QUESTIONS, "id")
    with sqlite3.connect(config.budget_path) as db:
        assert db.execute("SELECT * FROM attempts").fetchall() == [(22,)]
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("attempts",)]


@pytest.mark.asyncio
async def test_timeout_no_refund(config):
    def handler(request):
        raise httpx.ReadTimeout("PRIVATE", request=request)
    with pytest.raises(AnalysisFailure):
        await JevClient(config, transport=httpx.MockTransport(handler)).observe("A", "data", QUESTIONS, "id")
    assert rows(config)[0][2:4] == ("FAILED", RESERVED_INPUT_TOKENS)


@pytest.mark.asyncio
async def test_fixed_http_transport_tls_proxy_retry_deadline(config, monkeypatch):
    from app.transparent import jev
    constructed, deadlines = [], []
    original_wait = asyncio.wait_for
    def transport(**kwargs):
        constructed.append(kwargs)
        def handler(request):
            assert set(request.extensions["timeout"].values()) == {15}
            return httpx.Response(200, json=ANSWER)
        return httpx.MockTransport(handler)
    async def bounded(awaitable, timeout):
        deadlines.append(timeout)
        return await original_wait(awaitable, timeout)
    monkeypatch.setattr(jev.httpx, "AsyncHTTPTransport", transport)
    monkeypatch.setattr(jev.asyncio, "wait_for", bounded)
    await JevClient(config).observe("A", "data", QUESTIONS, "id")
    assert constructed == [{"verify": True, "retries": 0, "trust_env": False}]
    assert deadlines == [20]


@pytest.mark.asyncio
async def test_cancelled_attempt_not_refunded(config):
    entered, pending = asyncio.Event(), asyncio.Event()
    async def handler(_):
        entered.set()
        await pending.wait()
    client = JevClient(config, transport=httpx.MockTransport(handler))
    task = asyncio.create_task(client.observe("A", "data", QUESTIONS, "id"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert rows(config)[0][2:4] == ("CANCELLED", RESERVED_INPUT_TOKENS)


@pytest.mark.asyncio
async def test_atomic_request_limit_parallel_candidates(config):
    configured = JevSettings(**{**config.__dict__, "request_limit": 1})
    calls = []
    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=ANSWER)
    client = JevClient(configured, transport=httpx.MockTransport(handler))
    outcomes = await asyncio.gather(client.observe("A", "data", QUESTIONS, "first"),
                                    client.observe("B", "data", QUESTIONS, "second"), return_exceptions=True)
    assert sum(isinstance(item, AnalysisFailure) for item in outcomes) == 1
    assert len(calls) == 1 and len(rows(config)) == 1


def test_schema_and_offline_fixture_response_agree():
    from pathlib import Path

    from jsonschema import Draft202012Validator
    document = json.loads((Path(__file__).resolve().parents[2] / "docs/mvp/contracts/jev_observation.schema.json").read_text())
    Draft202012Validator.check_schema(document)
    assert Draft202012Validator(document).is_valid(ANSWER)


@pytest.mark.asyncio
async def test_invalid_or_unparseable_question_input_no_claim(config):
    for questions in [{}, {"q": {"type": "choice", "instructions": "pick", "criteria": {"one": "only"}}},
                      {"q": {"type": "noul", "instructions": "q", "extra": "raw"}},
                      {"q": {"type": "generation", "instructions": "q"}}]:
        with pytest.raises(AnalysisFailure):
            await JevClient(config).observe("A", "data", questions, "id")
    assert not config.budget_path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["a" * 64, {"deep": "f" * 64}, '{"password":"private"}'])
async def test_hashlike_raw_secrets_not_globally_whitelisted(config, state):
    with pytest.raises(AnalysisFailure):
        await JevClient(config).observe("A", state, QUESTIONS, "id")
    assert not config.budget_path.exists()
