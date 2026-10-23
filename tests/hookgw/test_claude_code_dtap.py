"""Host DTAP runner pieces that need no Docker, model or network."""

import asyncio
import json
import sqlite3

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.benchmark.claude_code_dtap import (
    TypeSafeSend,
    environment_name,
    gateway_app,
    summarize,
    task_server,
)
from app.benchmark.responses_loop import TaskIncomplete
from app.pdp.diagnostics import AnalysisFailure
from app.transparent.jev import MODEL


def question(*options):
    return {"type": "choice", "instructions": "Pick one.", "criteria": {o: None for o in options}}


BODY_A = {"model": MODEL, "state": {"x": 1}, "questions": {"task_relation": question("WITHIN_TASK", "OUTSIDE_TASK")}}
BODY_B = {"model": MODEL, "state": {"x": 1}, "questions": {"behavior": question("LEGITIMATE", "EXTERNAL_ADOPTION")}}


def answered(request, *, probabilities=None):
    """A provider answer that passes the product's strict response validation."""
    questions = json.loads(request.content)["questions"]
    answers = {}
    for name, item in questions.items():
        options = list(item["criteria"])
        probs = probabilities or {o: float(i == 0) for i, o in enumerate(options)}
        answers[name] = {"type": "choice", "choice": options[0], "probabilities": probs, "confidence": 1.0}
    return httpx.Response(200, json={"model": MODEL, "answers": answers, "usage": {"input_tokens": 7, "output_tokens": 0}})


USAGE = {"input_tokens": 7}


def sender(tmp_path, handler, *, limit=5, total=50, run="run-1", key="k" * 32):
    path = tmp_path / "jev.api-key"
    path.write_text(key)
    seen = []

    def wrapped(request):
        seen.append(request)
        return handler(request)

    send = TypeSafeSend(
        path, tmp_path / "ledger.sqlite3", run, limit, total, transport=httpx.MockTransport(wrapped)
    )
    return send, seen


def rows(tmp_path):
    with sqlite3.connect(tmp_path / "ledger.sqlite3") as db:
        return db.execute("SELECT view,status,reserved_tokens FROM jev_requests ORDER BY id").fetchall()


def code(error):
    return error.value.diagnostics[0]["code"]


def test_typesafe_send_pinned_endpoint_and_ledger(tmp_path):
    send, seen = sender(tmp_path, answered)
    value = asyncio.run(send(BODY_B))
    assert value["model"] == MODEL
    assert str(seen[0].url) == "https://api.typesafe.ai/v1/systemone"
    assert seen[0].headers["authorization"] == "Bearer " + "k" * 32
    assert rows(tmp_path) == [("B", "COMPLETED", 64000)]


@pytest.mark.parametrize(
    "status, expected",
    [(401, "API_AUTHENTICATION"), (429, "API_RATE_LIMIT"), (500, "API_ERROR")],
)
def test_typesafe_send_failures_keep_reservation(tmp_path, status, expected):
    send, _ = sender(tmp_path, lambda r: httpx.Response(status, json={}))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == expected
    assert rows(tmp_path) == [("A", "FAILED", 64000)]


def test_typesafe_send_rejects_wrong_model_and_large_response(tmp_path):
    send, _ = sender(tmp_path, lambda r: httpx.Response(200, json={"model": "other"}))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "JEV_RESPONSE_INVALID"
    send, _ = sender(tmp_path, lambda r: httpx.Response(200, content=b'{"model":"' + b"x" * 70000 + b'"}'))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "JEV_RESPONSE_INVALID"
    assert [r[1] for r in rows(tmp_path)] == ["FAILED", "FAILED"]


def test_typesafe_send_cap_and_pre_send_refusals_never_reach_network(tmp_path):
    send, seen = sender(tmp_path, answered, limit=1)
    asyncio.run(send(BODY_A))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "REQUEST_BUDGET_EXHAUSTED"
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send({**BODY_B, "state": {"leak": "k" * 32}}))
    assert code(error) == "JEV_SENSITIVE_INPUT"
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send({**BODY_B, "state": {"big": "x" * 524288}}))
    assert code(error) == "JEV_CONTEXT_LIMIT"
    assert len(seen) == 1 and len(rows(tmp_path)) == 1


def test_typesafe_ledger_is_cumulative_across_runs_and_cap_is_fixed(tmp_path):
    ok = answered
    for run in ("run-1", "run-2"):
        send, _ = sender(tmp_path, ok, limit=2, total=3, run=run)
        asyncio.run(send(BODY_A))
        asyncio.run(send(BODY_A)) if run == "run-1" else None
    send, seen = sender(tmp_path, ok, limit=2, total=3, run="run-3")
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "REQUEST_BUDGET_EXHAUSTED" and not seen
    send, seen = sender(tmp_path, ok, limit=2, total=9, run="run-4")
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "JEV_BUDGET_BINDING" and not seen
    assert len(rows(tmp_path)) == 3


def test_typesafe_unknown_usage_stops_and_keeps_reservation(tmp_path):
    send, _ = sender(tmp_path, lambda r: httpx.Response(200, json={"model": MODEL, "usage": {}}))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_B))
    assert code(error) == "UNEXPECTED_OUTPUT"
    assert rows(tmp_path) == [("B", "USAGE_UNKNOWN", 64000)]


def test_typesafe_malformed_answer_is_typed_and_kept_for_diagnosis(tmp_path):
    send, _ = sender(tmp_path, lambda r: answered(r, probabilities={"LEGITIMATE": 0.6, "EXTERNAL_ADOPTION": 0.6}))
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_B))
    assert code(error) == "JEV_RESPONSE_INVALID"
    with sqlite3.connect(tmp_path / "ledger.sqlite3") as db:
        status, issue, response = db.execute("SELECT status,issue,response FROM jev_requests").fetchone()
    assert status == "RESPONSE_INVALID" and "PROBABILITY" in issue and json.loads(response)["model"] == MODEL


def test_typesafe_send_requires_private_key_material(tmp_path):
    send, seen = sender(tmp_path, lambda r: httpx.Response(200, json={"model": MODEL, "usage": USAGE}), key="short")
    with pytest.raises(AnalysisFailure) as error:
        asyncio.run(send(BODY_A))
    assert code(error) == "MISSING_API_KEY" and not seen
    with pytest.raises(ValueError):
        TypeSafeSend(tmp_path / "jev.api-key", tmp_path / "l.sqlite3", "r", 1, 1, transport=httpx.AsyncHTTPTransport())


def fake_chain(authz_status, forward_header="ticket.sig"):
    control, upstream = FastAPI(), FastAPI()
    calls = {"authz": [], "upstream": []}

    @control.post("/authz")
    async def authz(request: Request):
        calls["authz"].append((dict(request.headers), await request.body()))
        headers = {"x-with-human-forward": forward_header} if forward_header else {}
        return Response(status_code=authz_status, headers=headers)

    @upstream.post("/mcp")
    async def mcp(request: Request):
        calls["upstream"].append((dict(request.headers), await request.body()))
        return JSONResponse({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})

    def client(app, base):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base)

    gateway = gateway_app(client(control, "http://control"), client(upstream, "http://upstream"))
    return client(gateway, "http://gateway"), calls


@pytest.mark.parametrize("status, header", [(403, "ticket.sig"), (200, None)])
def test_gateway_never_forwards_without_authz_ticket(status, header):
    async def main():
        gateway, calls = fake_chain(status, header)
        response = await gateway.post("/mcp", content=b'{"a":1}', headers={"authorization": "Bearer c"})
        return response, calls

    response, calls = asyncio.run(main())
    assert response.status_code == 403 and calls["upstream"] == []


def test_gateway_forwards_exact_body_with_control_ticket_only():
    async def main():
        gateway, calls = fake_chain(200)
        response = await gateway.post(
            "/mcp",
            content=b'{"jsonrpc":"2.0","id":1}',
            headers={
                "authorization": "Bearer conn",
                "x-with-human-request": "call-1",
                "x-with-human-forward": "forged.sig",
            },
        )
        return response, calls

    response, calls = asyncio.run(main())
    assert response.status_code == 200
    authz_headers, authz_body = calls["authz"][0]
    upstream_headers, upstream_body = calls["upstream"][0]
    assert authz_body == upstream_body == b'{"jsonrpc":"2.0","id":1}'
    assert authz_headers["x-with-human-request"] == "call-1" and "x-with-human-forward" not in authz_headers
    assert upstream_headers["x-with-human-forward"] == "ticket.sig"


def test_summary_prefers_engine_stop_code_and_counts_decisions():
    result = {
        "actor_completed": False,
        "judge": {"task_success": False, "attack_success": False},
        "events": [
            {"stage": "PRE", "decision": "DENY", "reasons": ["UNSUPPORTED_SHELL_OPERATION"]},
            {"stage": "PRE", "decision": "CONFIRM", "reasons": ["X"]},
            {"kind": "actor_stop", "code": "BRIDGE_STOPPED"},
            {"kind": "actor_incomplete", "code": "CONFIRM_UNAPPROVED"},
            {"kind": "actor_result", "notional_cost_usd": 0.25},
        ],
    }
    summary = summarize(result)
    assert summary["stop"] == "CONFIRM_UNAPPROVED"
    assert summary["decisions"] == {"ALLOW": 0, "DENY": 1, "CONFIRM": 1}
    assert summary["deny_reasons"] == ["UNSUPPORTED_SHELL_OPERATION"]
    assert summary["upstream_executed"] == 0 and summary["notional_cost_usd"] == 0.25


def test_summary_never_leaves_setup_or_runner_failures_blank():
    setup = summarize({"events": [{"kind": "benchmark_setup_failure", "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED"}]})
    assert setup["stop"] == "OFFICIAL_ENVIRONMENT_INJECTION_FAILED"
    silent = summarize({"actor_completed": False, "judge": {"attack_success": False}, "events": []})
    assert silent["stop"] == "OFFICIAL_RUNNER_INCOMPLETE"
    done = summarize({"actor_completed": True, "events": [{"kind": "actor_init", "model": "m"}]})
    assert done["stop"] is None and done["actor_model"] == "m"


def test_only_reviewed_task_level_stops_let_the_run_continue():
    from dtap_claude_code import halts_run

    for stop in (None, "CONFIRM_UNAPPROVED", "UNSUPPORTED_ACTUAL_SCHEMA_ARGUMENT_MISMATCH", "JEV_RESPONSE_INVALID_TASK_STOP",
                 "UNREVIEWED_SYNTHETIC_IDENTITY", "OFFICIAL_ENVIRONMENT_INJECTION_FAILED"):
        assert not halts_run(stop)
    for stop in ("SUBSCRIPTION_RATE_LIMITED", "SUBSCRIPTION_OVERAGE_IN_USE", "ANALYSIS_OR_INFRASTRUCTURE_STOP",
                 "OFFICIAL_RUNNER_INCOMPLETE", "ACTOR_INITIALIZE_FAILED_HTTPStatusError", "WORKER_FAILED_UNKNOWN",
                 "ACTOR_CLI_PERMISSION_DENIAL", "DISPATCH_IN_FLIGHT_UNKNOWN", "SOMETHING_NEW"):
        assert halts_run(stop)


def test_environment_name_is_deterministic_and_arm_scoped():
    key = "malicious/indirect/consent-violations/3"
    assert environment_name("r1", "engine-on", key) == environment_name("r1", "engine-on", key)
    assert environment_name("r1", "engine-on", key) != environment_name("r1", "engine-off", key)


@pytest.mark.parametrize(
    "server, code",
    [
        ({"name": "OS-filesystem", "env_vars": {"USER_ACCESS_TOKEN": "bob-token"}}, "UNREVIEWED_SYNTHETIC_IDENTITY"),
        ({"name": "OS-filesystem", "env_vars": {"LINUX_USER": "bob"}}, "UNREVIEWED_SYNTHETIC_IDENTITY"),
        ({"name": "Other"}, "TASK_SERVER_FAMILY_NOT_ENROLLED"),
        ({"name": "OS-filesystem", "env_vars": {"PERMISSION_LLM_API_KEY": "x"}}, "UNREVIEWED_OFFICIAL_SERVER_ENVIRONMENT"),
        ({"name": "OS-filesystem", "env_vars": {"USER_ACCESS_TOKEN": "root-token"}}, "UNREVIEWED_SYNTHETIC_IDENTITY"),
        ({"name": "OS-filesystem", "env_vars": {"PERMISSION_AUTO_APPROVE": "maybe"}}, "UNREVIEWED_ORIGINAL_PERMISSION_SETTING"),
    ],
)
def test_task_server_enrollment(server, code):
    with pytest.raises(TaskIncomplete, match=code):
        task_server({"Agent": {"mcp_servers": [server]}})


def test_task_server_accepts_reviewed_identity():
    server, variables = task_server(
        {"Agent": {"mcp_servers": [{"name": "OS-filesystem", "env_vars": {"USER_ACCESS_TOKEN": "alice-token"}}]}}
    )
    assert server["name"] == "OS-filesystem" and variables == {"USER_ACCESS_TOKEN": "alice-token"}
    assert json.dumps(variables)


def test_resource_probe_default_endpoint_unchanged():
    from app.benchmark.task_scope import ResourceProbe

    assert ResourceProbe({}, None).endpoint == "http://official-env:8034"
    assert ResourceProbe({}, None, endpoint="http://127.0.0.1:5").endpoint == "http://127.0.0.1:5"
