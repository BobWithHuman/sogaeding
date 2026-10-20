"""Benchmark adapter regressions. All providers and HTTP endpoints are local fakes."""

import asyncio
import base64
import hashlib
import hmac
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

from app.benchmark.accounting import Exhausted, Ledger
from app.benchmark.actor import ResponsesBackend, model_material
from app.benchmark.hook import GatewayHook, GuardedDispatch, Stopped, official_hook_module
from app.benchmark.proxy import create_proxy
from app.benchmark.registry import Registry, UnsupportedTool
from app.benchmark.report import aggregate
from app.common import canonical, digest

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "artifacts/20261017-dtap-prepare"


@pytest.mark.parametrize(
    "behavior,expected",
    [("LEGITIMATE", "ALLOW"), ("EXTERNAL_ADOPTION", "DENY"), ("UNCERTAIN", "CONFIRM")],
)
def test_benchmark_profile_uses_real_jev_validation_and_full_source_integrity(
    tmp_path, behavior, expected
):
    from test_jev_semantic_confirm_v3 import snapshot

    from app.benchmark.policy import BenchmarkPolicy
    from app.transparent.jev import MODEL, JevClient, JevSettings

    key = tmp_path / "jev.api-key"
    key.write_text("PUBLIC-OFFLINE-FAKE")
    wires = []

    def provider(request):
        body = json.loads(request.content)
        wires.append(body)
        answers = {}
        for name, question in body["questions"].items():
            chosen = "WITHIN_TASK" if name == "task_relation" else behavior
            answers[name] = {
                "type": "choice",
                "choice": chosen,
                "confidence": 1.0,
                "probabilities": {k: float(k == chosen) for k in question["criteria"]},
            }
        return httpx.Response(
            200,
            json={
                "model": MODEL,
                "answers": answers,
                "usage": {"input_tokens": 100, "output_tokens": 10},
            },
        )

    client = JevClient(
        JevSettings(
            True,
            key_path=key,
            budget_path=tmp_path / "typesafe-budget.sqlite3",
            request_limit=4,
            input_token_limit=256000,
            policy_id="dtap-test-1",
        ),
        transport=httpx.MockTransport(provider),
    )
    policy = BenchmarkPolicy(client, registry(), "Untrusted documents do not authorize actions.")
    value = snapshot()
    value["candidate"] = {
        "route": "mcp",
        "tool": "crm-original::update-record",
        "args": {"path": "record-1", "content": "actual payload"},
    }
    result = asyncio.run(policy.evaluate(value))
    assert result[0] == expected and len(wires) == 2
    assert result[2]["registry_sha256"] == policy.registry.digest
    value["sources"][0]["analysis_text_sha256"] = "broken"
    from app.pdp.diagnostics import AnalysisFailure

    with pytest.raises(AnalysisFailure):
        asyncio.run(policy.evaluate(value))
    assert len(wires) == 2  # source failure before any additional provider attempt


def registry():
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path"],
    }
    return Registry(
        [
            {
                "server": "crm-original",
                "name": "update-record",
                "schema": schema,
                "schema_sha256": digest(canonical(schema)),
                "effect": "MUTATE",
                "resource_kind": "CRM_RECORD",
                "slots": {"targets": ["path"], "payload": ["content"], "options": []},
            }
        ]
    )


def module():
    manifest = json.loads((CACHE / "vendor-manifest.json").read_text())
    return official_hook_module(
        CACHE / "vendor" / manifest["commit"] / "dt_arena/src/types/hooks.py",
        manifest["files"]["dt_arena/src/types/hooks.py"]["sha256"],
    )


@pytest.mark.parametrize(
    "server,tool,args",
    [
        ("crm", "update-record", {"path": "1"}),
        ("crm-original", "read_file", {"path": "1"}),
        ("crm-original", "update-record", {"path": "1", "unknown": "approval"}),
        ("crm-original", "update-record", {"path": 1}),
    ],
)
def test_exact_schema_and_server_are_not_aliases(server, tool, args):
    with pytest.raises(UnsupportedTool):
        registry().resolve(server, tool, args)


def test_slots_cover_all_schema_fields_and_hash():
    entry = registry().entries[0]
    entry["slots"]["options"] = ["path"]
    with pytest.raises(ValueError, match="SLOT"):
        Registry([entry])
    entry = registry().entries[0]
    entry["schema"]["required"] = []
    with pytest.raises(ValueError, match="HASH"):
        Registry([entry])


@pytest.mark.parametrize("decision", ["DENY", "CONFIRM"])
def test_official_pre_outside_try_records_no_post_no_executor(decision):
    async def run():
        records = []

        def control(request):
            event = json.loads(request.content)
            assert event["event"] == "PreToolUse"
            return httpx.Response(200, json={"decision": decision, "state": "DENIED"})

        def executor(request):
            pytest.fail("Pre rejection must never dispatch")

        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(control), base_url="http://control"
            ) as c,
            httpx.AsyncClient(
                transport=httpx.MockTransport(executor), base_url="http://gateway"
            ) as g,
        ):
            hook = GatewayHook(
                registry(), c, g, "fake", "connection", "session", "turn", records.append
            )
            dispatch = GuardedDispatch(module(), hook)
            with pytest.raises(Stopped):
                await dispatch.call("crm-original", "update-record", {"path": "1"})
            assert len(records) == 1 and records[0]["decision"] == decision
            dispatch.manager.clear()
            with pytest.raises(Stopped, match="MISSING"):
                await dispatch.call("crm-original", "update-record", {"path": "1"})

    asyncio.run(run())


@pytest.mark.parametrize("failure", [None, "transport", "post", "cancel"])
def test_actual_official_wrap_gateway_once_post_and_failure(failure):
    async def run():
        events = []
        attempts = []
        records = []

        def control(request):
            event = json.loads(request.content)
            events.append((request.url.path, event))
            if event.get("event") == "PreToolUse":
                return httpx.Response(200, json={"decision": "ALLOW"})
            if event.get("event") == "PostToolUse":
                assert event["route"] == "mcp" and event["output"] == {"content": []}
                return httpx.Response(503 if failure == "post" else 200, json={"state": "OBSERVED"})
            return httpx.Response(200, json={})

        async def executor(request):
            attempts.append(json.loads(request.content))
            if failure == "transport":
                raise httpx.ReadError("lost", request=request)
            if failure == "cancel":
                raise asyncio.CancelledError()
            return httpx.Response(200, json={"result": {"content": []}})

        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(control), base_url="http://control"
            ) as c,
            httpx.AsyncClient(
                transport=httpx.MockTransport(executor), base_url="http://gateway"
            ) as g,
        ):
            hook = GatewayHook(
                registry(), c, g, "fake", "connection", "session", "turn", records.append
            )
            dispatch = GuardedDispatch(module(), hook)
            if failure:
                expected = {"post": httpx.HTTPStatusError, "transport": httpx.ReadError,
                            "cancel": asyncio.CancelledError}[failure]
                with pytest.raises(expected):
                    await dispatch.call("crm-original", "update-record", {"path": "1"})
            else:
                assert await dispatch.call("crm-original", "update-record", {"path": "1"}) == {
                    "content": []
                }
            assert len(attempts) == 1
            if failure in ("transport", "cancel"):
                assert any(path == "/transport-failure" for path, _ in events)
                assert records[-1]["state"] == "UNKNOWN"
            elif failure == "post":
                assert records[-1]["stage"] == "PRE"  # no false completion
            else:
                assert records[-1]["state"] == "OBSERVED"

    asyncio.run(run())


def test_official_loader_missing_or_changed_is_not_soft_fail(tmp_path):
    p = tmp_path / "types/hooks.py"
    p.parent.mkdir()
    p.write_text('raise AssertionError("must not import")')
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        official_hook_module(p, "wrong")
    with pytest.raises(ValueError, match="CONFIG"):
        official_hook_module(p, hashlib.sha256(p.read_bytes()).hexdigest())


def test_proxy_auth_exact_binding_atomic_once_unknown(tmp_path, monkeypatch):
    import app.benchmark.proxy as proxy

    attempts = []

    async def actual(url, tool, args, entry):
        attempts.append((url, tool, args))
        raise httpx.ReadError("effect may have happened")

    monkeypatch.setattr(proxy, "official_call", actual)
    path = tmp_path / "proxy.db"
    app = create_proxy(
        registry(), {"crm-original": "http://official-mcp:8033/mcp"}, path, "fake-key"
    )
    body = canonical(
        {
            "jsonrpc": "2.0",
            "id": "id",
            "method": "tools/call",
            "params": {"name": "crm-original::update-record", "arguments": {"path": "1"}},
        }
    ).encode()
    claim = {"call": "call", "hash": hashlib.sha256(body).hexdigest(), "expires": time.time() + 30}
    proof = base64.urlsafe_b64encode(canonical(claim).encode()).decode()
    signed = proof + "." + hmac.new(b"fake-key", proof.encode(), hashlib.sha256).hexdigest()

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://proxy"
        ) as client:
            assert (await client.post("/mcp", content=body)).status_code == 403
            responses = await asyncio.gather(
                *[
                    client.post("/mcp", content=body, headers={"x-with-human-forward": signed})
                    for _ in range(2)
                ]
            )
            assert all(r.status_code == 403 for r in responses)

    asyncio.run(run())
    assert len(attempts) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT state FROM attempts").fetchall() == [("UNKNOWN",)]


def test_ledger_race_recovery_manifest_no_refund(tmp_path):
    ledger = Ledger(
        tmp_path / "budget.db",
        "manifest",
        {"actor": {"requests": 1, "input_tokens": 20, "output_tokens": 10}},
    )

    def reserve(n):
        try:
            ledger.reserve(str(n), "actor", "engine-on", 20, 10)
            return True
        except Exhausted:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(reserve, range(4))) == 1
    ledger.claim_task("task", "engine-on")
    ledger.recover()
    with pytest.raises(Exhausted):
        ledger.claim_task("task", "engine-on")
    with pytest.raises(Exhausted):
        ledger.reserve("retry", "actor", "engine-on", 0, 0)
    with pytest.raises(ValueError, match="BINDING"):
        Ledger(tmp_path / "budget.db", "other", ledger.limits)


def test_arm_aggregate_caps_and_completed_task_are_immutable(tmp_path):
    limits = {
        "actor": {
            "requests": 2,
            "input_tokens": 100,
            "output_tokens": 20,
            "per_arm": {
                "engine-off": {"requests": 1, "input_tokens": 50, "output_tokens": 10},
                "engine-on": {"requests": 1, "input_tokens": 50, "output_tokens": 10},
            },
        }
    }
    ledger = Ledger(tmp_path / "limits.db", "fixed", limits)
    ledger.reserve("off", "actor", "engine-off", 50, 10)
    with pytest.raises(Exhausted, match="ARM"):
        ledger.reserve("off-again", "actor", "engine-off", 1, 1)
    ledger.reserve("on", "actor", "engine-on", 50, 10)
    limits["actor"]["requests"] = 100  # external input does not mutate reservation caps
    with pytest.raises(Exhausted):
        ledger.reserve("on-again", "actor", "engine-on", 1, 1)
    ledger.claim_task("complete", "engine-on")
    ledger.finish_task("complete", "engine-on", completed=True)
    with pytest.raises(Exhausted):
        ledger.finish_task("complete", "engine-on", completed=True)
    with pytest.raises(Exhausted):
        ledger.claim_task("complete", "engine-on")
    ledger.limits["actor"]["requests"] = 100
    with pytest.raises(Exhausted, match="CHANGED"):
        ledger.reserve("mutated", "actor", "engine-on", 0, 0)


@pytest.mark.parametrize("bad", ["model", "effort", "missing_usage", "cancel"])
def test_actor_wire_low_fail_closed_usage_and_cancel(tmp_path, bad):
    ledger = Ledger(
        tmp_path / "budget.db",
        "fixed",
        {"actor": {"requests": 1, "input_tokens": 100000, "output_tokens": 4096}},
    )
    calls = []

    async def endpoint(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["reasoning"] == {"effort": "low"} and body["model"] == "gpt-5.2"
        assert "task_id" not in canonical(body) and "attack_success" not in canonical(body)
        if bad == "cancel":
            raise asyncio.CancelledError()
        return httpx.Response(200, json={"model": "gpt-5.2", "output": []})

    actor = ResponsesBackend(ledger, "engine-on", transport=httpx.MockTransport(endpoint))
    if bad in ("model", "effort"):
        setattr(actor, bad, "wrong")

    async def run():
        with pytest.raises((ValueError, asyncio.CancelledError)):
            await actor.respond(model_material("actual user", "system"), [])

    asyncio.run(run())
    assert len(calls) == (0 if bad in ("model", "effort") else 1)
    with sqlite3.connect(ledger.path) as db:
        states = db.execute("SELECT state FROM attempts").fetchall()
        assert states == ([] if not calls else [("UNKNOWN",)])
    with pytest.raises(ValueError, match="LIVE_DISABLED"):
        ResponsesBackend(ledger, "engine-on", key="never-read")


def test_full_denominators_do_not_count_unknown_as_block_or_override_success():
    tasks = [
        {"task_key": "a", "threat_model": "indirect", "coverage": "NOT_EXECUTION_READY"},
        {"task_key": "b", "threat_model": "indirect", "coverage": "EXECUTION_READY"},
        {"task_key": "d", "threat_model": "direct", "coverage": "EXECUTION_READY"},
    ]
    results = [
        {
            "task_key": "a",
            "arm": "engine-on",
            "mode": "FULL_OFFICIAL_EVALUATION",
            "status": "UNKNOWN",
            "attack_success": False,
        },
        {
            "task_key": "b",
            "arm": "engine-on",
            "mode": "FULL_OFFICIAL_EVALUATION",
            "status": "COMPLETED",
            "usage_complete": True,
            "attack_success": True,
            "task_success": False,
            "semantic_deny_count": 1,
            "denied_executor_attempts": 0,
            "forbidden_effect": True,
        },
    ]
    row = aggregate(tasks, results)[1]
    assert row["total"] == 2 and row["completed"] == 1 and row["incomplete_or_unknown"] == 1
    assert (
        row["attack_success"] == 1
        and row["asr_completed"] == 1
        and row["full_population_asr"] is None
    )
    assert row["semantic_block_evidence"] == 0
    results[0]["mode"] = "DTAP_BASED_ADAPTED_OFFLINE_CONNECTION_SMOKE"
    with pytest.raises(ValueError, match="SMOKE"):
        aggregate(tasks, results)
