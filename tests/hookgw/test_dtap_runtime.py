import asyncio
import copy
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.benchmark.provider import ProviderTransport, claims, token
from app.benchmark.responses_loop import AutonomousResponses, TaskIncomplete
from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_policy import SyntheticBoundary


def limit(requests=100, cost=10000000):
    return {
        "requests": requests,
        "input_tokens": 100000,
        "output_tokens": 10000,
        "seconds": 10000,
        "micro_usd": cost,
    }


def manifest():
    profile = {
        "models": ["gpt-5.2"],
        "paths": ["responses"],
        "rates": {"gpt-5.2": {"input": 1.75, "output": 14}},
        "per_request": {
            "input_tokens": 1000,
            "output_tokens": 100,
            "seconds": 10,
            "wire_bytes": 10000,
            "response_bytes": 10000,
        },
        "total": limit(),
        "arms": {a: limit() for a in ("engine-off", "engine-on")},
        "per_task": limit(5),
    }
    return {
        "arms": ["engine-off", "engine-on"],
        "task_keys": ["task", "other"],
        "providers": {p: copy.deepcopy(profile) for p in ("actor", "jev", "environment", "judge")},
        "limits": {"total": limit(), "arms": {a: limit() for a in ("engine-off", "engine-on")}},
        "live_opt_in": "EXPLICIT_USER_COMMAND",
    }


def start(budget, arm="engine-on", task="task"):
    owner = budget.acquire(arm)
    assert budget.claim(task, arm, owner) == "NEW"
    return owner


def test_shared_cross_arm_atomic_cost_and_no_refund(tmp_path):
    m = manifest()
    m["limits"]["total"]["requests"] = 1
    budget = RuntimeBudget(tmp_path / "budget.db", m)
    start(budget, "engine-off")
    start(budget, "engine-on")

    def call(arm):
        try:
            return budget.reserve("task", arm, "actor", "gpt-5.2", 1000, 100, 10)
        except StopRun:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(call, m["arms"]))
    assert sum(v is not None for v in ids) == 1
    rid = next(v for v in ids if v)
    assert budget.record(rid, None) is False
    with pytest.raises(StopRun, match="CAP"):
        budget.reserve("task", "engine-on", "actor", "gpt-5.2", 1, 1, 1)
    assert budget.status()["provider_reservations"][0]["state"] == "UNKNOWN"


def test_claimed_unknown_and_completed_never_rerun(tmp_path):
    budget = RuntimeBudget(tmp_path / "budget.db", manifest())
    owner = start(budget)
    budget.finish("task", "engine-on", owner, "COMPLETED", {"actual": True})
    assert budget.claim("task", "engine-on", owner) == "COMPLETED"
    assert budget.claim("other", "engine-on", owner) == "NEW"
    budget.reconcile_interrupted("engine-on")
    owner = budget.acquire("engine-on")
    assert budget.claim("other", "engine-on", owner) == "UNKNOWN"
    with pytest.raises(StopRun):
        budget.finish("task", "engine-on", owner, "COMPLETED", {})
    m = manifest()
    m["limits"]["total"]["requests"] = 101
    with pytest.raises(StopRun, match="MANIFEST"):
        RuntimeBudget(budget.path, m)


def test_all_scope_caps_and_mutation_fail_closed(tmp_path):
    for scope in ("total", "arm", "provider", "provider_arm", "task_provider"):
        m = manifest()
        target = {
            "total": m["limits"]["total"],
            "arm": m["limits"]["arms"]["engine-on"],
            "provider": m["providers"]["actor"]["total"],
            "provider_arm": m["providers"]["actor"]["arms"]["engine-on"],
            "task_provider": m["providers"]["actor"]["per_task"],
        }[scope]
        target["input_tokens"] = 0
        budget = RuntimeBudget(tmp_path / (scope + ".db"), m)
        start(budget)
        with pytest.raises(StopRun, match="CAP"):
            budget.reserve("task", "engine-on", "actor", "gpt-5.2", 1, 1, 1)


def test_provider_live_mock_and_low_wire_gate_before_send(tmp_path):
    budget = RuntimeBudget(tmp_path / "budget.db", manifest())
    start(budget)
    hits = []

    def endpoint(request):
        hits.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.2",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        )

    transport = httpx.MockTransport(endpoint)
    with pytest.raises(StopRun, match="MOCK"):
        ProviderTransport(budget, {}, live=True, transport=transport)
    provider = ProviderTransport(budget, {"openai": "public-fake-openai-key"}, transport=transport)
    job = {"task": "task", "arm": "engine-on", "provider": "actor"}
    body = {
        "model": "gpt-5.2",
        "reasoning": {"effort": "high"},
        "store": False,
        "parallel_tool_calls": False,
        "max_output_tokens": 10,
        "input": [],
    }
    with pytest.raises(StopRun, match="CONTRACT"):
        asyncio.run(provider.send(job, "responses", body))
    assert hits == []
    body["reasoning"] = {"effort": "low"}
    asyncio.run(provider.send(job, "responses", body))
    assert len(hits) == 1
    assert budget.status()["provider_reservations"][0]["input_reserved"] == 1000


def test_only_gpt52_low_can_reach_openai_in_os_permission_path(tmp_path):
    m = manifest()
    m["providers"]["environment"]["paths"] = ["chat/completions"]
    m["providers"]["environment"]["models"] = ["gpt-5.1", "gpt-5.2"]
    m["providers"]["environment"]["per_request"]["output_tokens"] = 500
    m["providers"]["judge"]["paths"] = ["chat/completions"]
    m["providers"]["judge"]["models"] = ["gpt-5.4"]
    budget = RuntimeBudget(tmp_path / "budget.db", m)
    start(budget)
    wires = []

    def endpoint(request):
        wires.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.2",
                "choices": [{"message": {"content": '{"decision":"APPROVED"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    provider = ProviderTransport(
        budget, {"openai": "public-fake-key"}, transport=httpx.MockTransport(endpoint)
    )
    original = {
        "messages": [{"role": "user", "content": "synthetic permission"}],
        "temperature": 0.1,
        "max_completion_tokens": 500,
    }
    for role, model in (("environment", "gpt-5.1"), ("judge", "gpt-5.4")):
        with pytest.raises(StopRun, match="OPENAI_GPT52_ONLY"):
            asyncio.run(
                provider.send(
                    {"task": "task", "arm": "engine-on", "provider": role},
                    "chat/completions",
                    {**original, "model": model},
                )
            )
    assert wires == []
    asyncio.run(
        provider.send(
            {"task": "task", "arm": "engine-on", "provider": "environment"},
            "chat/completions",
            {**original, "model": "gpt-5.2"},
        )
    )
    assert len(wires) == 1
    assert wires[0]["model"] == "gpt-5.2"
    assert wires[0]["reasoning_effort"] == "low"
    assert "temperature" not in wires[0]


def test_lost_provider_response_keeps_charge_and_stops_all(tmp_path):
    budget = RuntimeBudget(tmp_path / "budget.db", manifest())
    start(budget)

    async def endpoint(request):
        raise httpx.ReadError("lost response", request=request)

    provider = ProviderTransport(
        budget, {"openai": "public-fake-key"}, transport=httpx.MockTransport(endpoint)
    )
    body = {
        "model": "gpt-5.2",
        "reasoning": {"effort": "low"},
        "store": False,
        "parallel_tool_calls": False,
        "max_output_tokens": 10,
        "input": [],
    }
    with pytest.raises(StopRun):
        asyncio.run(
            provider.send(
                {"task": "task", "arm": "engine-on", "provider": "actor"}, "responses", body
            )
        )
    status = budget.status()
    assert status["stop"] == "PROVIDER_REQUEST_UNKNOWN_NO_RETRY"
    assert status["provider_reservations"][0]["state"] == "UNKNOWN"
    assert status["provider_reservations"][0]["micro_usd_reserved"] > 0


def test_real_role_token_not_schema_words_grants_authority():
    boundary = SyntheticBoundary(["actual-long-runtime-credential"])
    source = boundary.material("access_token: Optional. Synthetic example password=benchmark-only.")
    assert source["analysis_complete"] and source["analysis_text"].startswith(
        "access_token: Optional"
    )
    assert not boundary.material("actual-long-runtime-credential")["analysis_complete"]
    signed = token("secret", "task", "engine-on", "actor", 9999999999)
    assert claims("secret", "Bearer " + signed)["arm"] == "engine-on"
    with pytest.raises(StopRun):
        claims("wrong", "Bearer " + signed)


def test_autonomous_loop_replays_reasoning_tools_and_finishes_from_actual_output():
    async def run():
        wires = []
        calls = []
        records = []

        async def provider(body):
            wires.append(copy.deepcopy(body))
            results = [x for x in body["input"] if x.get("type") == "function_call_output"]
            if not results:
                return {
                    "status": "completed",
                    "output": [
                        {
                            "type": "reasoning",
                            "id": "r1",
                            "summary": [],
                            "encrypted_content": "encrypted-private-reasoning",
                        },
                        {
                            "type": "function_call",
                            "call_id": "c1",
                            "name": "search",
                            "arguments": '{"query":"user target"}',
                        },
                    ],
                }
            assert any(
                x.get("encrypted_content") == "encrypted-private-reasoning" for x in body["input"]
            )
            actual = json.loads(results[-1]["output"])
            return {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": actual["found"]}],
                    }
                ],
            }

        async def dispatch(name, args):
            calls.append((name, args))
            return {"found": "actual sandbox content"}

        agent = AutonomousResponses(
            provider,
            dispatch,
            [{"type": "function", "name": "search", "parameters": {}}],
            system="actual system",
            limits={"responses": 4, "tool_calls": 2, "seconds": 10, "output_tokens": 100},
            record=records.append,
        )
        assert await agent.run("Find the user target") == "actual sandbox content"
        assert len(wires) == 2 and len(calls) == 1
        assert all(w["reasoning"] == {"effort": "low"} for w in wires)

    asyncio.run(run())


@pytest.mark.parametrize("kind", ["incomplete", "duplicate", "native"])
def test_incomplete_duplicate_native_do_not_reexecute(kind):
    async def run():
        effects = []

        async def send(body):
            if kind == "incomplete":
                return {"status": "incomplete", "output": []}
            item = (
                {"type": "function_call", "name": "tool", "call_id": "same", "arguments": "{}"}
                if kind == "duplicate"
                else {"type": "local_shell_call"}
            )
            return {"status": "completed", "output": [item]}

        async def dispatch(*args):
            effects.append(args)
            return {}

        loop = AutonomousResponses(
            send,
            dispatch,
            [{"type": "function", "name": "tool"}],
            system="system",
            limits={"responses": 5, "tool_calls": 5, "seconds": 10, "output_tokens": 10},
            record=lambda v: None,
        )
        with pytest.raises(TaskIncomplete):
            await loop.run("actual user")
        assert len(effects) == (1 if kind == "duplicate" else 0)

    asyncio.run(run())
