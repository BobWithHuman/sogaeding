"""Reproduce terminal output=[] while complete output lives in SSE items."""

import asyncio
import copy
import importlib.util
from pathlib import Path

import httpx
import pytest
import siwc_protocol_probe as probe
from siwc_tool_probe import REQUEST, validate_result

from app.benchmark.responses_loop import AutonomousResponses
from app.benchmark.runtime_budget import StopRun
from app.benchmark.runtime_controller import invalid_setup_log
from app.benchmark.siwc_auth import MODEL
from app.benchmark.siwc_transport import NAMESPACE, completed_stream, normalize
from app.common import canonical


def items():
    return [
        {
            "id": "rs_public",
            "type": "reasoning",
            "summary": [],
            "encrypted_content": "PUBLIC-TEST-REASONING",
        },
        {
            "id": "fc_public",
            "type": "function_call",
            "status": "completed",
            "name": "dt_probe_echo",
            "namespace": NAMESPACE,
            "call_id": "call_public",
            "arguments": '{"value":"CONNECTED"}',
        },
    ]


def frames(output=None):
    result = []
    for index, item in enumerate(items() if output is None else output):
        result.append(
            {
                "type": "response.output_item.added",
                "output_index": index,
                "item": {"id": item["id"], "type": item["type"]},
            }
        )
        result.append({"type": "response.output_item.done", "output_index": index, "item": item})
    result.append(
        {
            "type": "response.completed",
            "response": {
                "status": "completed",
                "model": MODEL,
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        }
    )
    return result


def response(events):
    return httpx.Response(
        200, content="".join("data: " + canonical(e) + "\n\n" for e in events).encode()
    )


def test_empty_terminal_reconstructs_only_complete_items_and_reasoning():
    value = asyncio.run(completed_stream(response(frames()), maximum=10000))
    assert value["output"] == items()
    assert validate_result(value)["tool_calls"] == 1
    assert normalize(value, {"dt_probe_echo"})["output"][1]["call_id"] == "call_public"


def test_frozen_stream1_parser_reproduces_lost_items():
    path = (
        Path(__file__).resolve().parents[2]
        / "artifacts/20261018-dtap-os100/user-chatgpt-login-luna-stream1/source/src/app/benchmark/siwc_transport.py"
    )
    spec = importlib.util.spec_from_file_location("frozen_stream1_transport", path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    assert asyncio.run(old.completed_stream(response(frames()), maximum=10000))["output"] == []
    assert asyncio.run(completed_stream(response(frames()), maximum=10000))["output"] == items()


@pytest.mark.parametrize(
    "fault",
    [
        "missing_done",
        "mismatched_id",
        "duplicate",
        "gap",
        "negative",
        "boolean",
        "huge",
        "wrong_kind",
        "after_terminal",
        "terminal_conflict",
        "duplicate_id",
    ],
)
def test_partial_or_conflicting_output_never_reaches_dispatch(fault):
    events = frames()
    if fault == "missing_done":
        del events[1]
    elif fault == "mismatched_id":
        events[1]["item"]["id"] = "other"
    elif fault == "duplicate":
        events.insert(2, copy.deepcopy(events[1]))
    elif fault in ("gap", "negative", "boolean", "huge"):
        changed = {"gap": 3, "negative": -1, "boolean": True, "huge": 999999}[fault]
        events[0]["output_index"] = events[1]["output_index"] = changed
    elif fault == "wrong_kind":
        events[1]["item"]["type"] = "computer_call"
    elif fault == "after_terminal":
        events.append(copy.deepcopy(events[1]))
    elif fault == "terminal_conflict":
        events[-1]["response"]["output"] = [{"type": "message"}]
    else:
        events[2]["item"]["id"] = events[3]["item"]["id"] = "rs_public"
    with pytest.raises(StopRun):
        asyncio.run(completed_stream(response(events), maximum=10000))


def test_stream_to_actual_responses_loop_dispatch_then_final_message():
    dispatched, seen, records = [], [], []

    async def send(body):
        seen.append(body)
        if len(seen) == 1:
            events = frames()
        else:
            assert any(
                v.get("type") == "function_call_output" and v["call_id"] == "call_public"
                for v in body["input"]
            )
            assert any(v.get("encrypted_content") == "PUBLIC-TEST-REASONING" for v in body["input"])
            events = frames(
                [
                    {
                        "id": "msg_public",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "CONNECTED"}],
                    }
                ]
            )
        return normalize(await completed_stream(response(events), maximum=10000), {"dt_probe_echo"})

    async def dispatch(name, args):
        dispatched.append((name, args))
        return {"content": [{"type": "text", "text": "CONNECTED"}]}

    loop = AutonomousResponses(
        send,
        dispatch,
        [{"type": "function", "name": "dt_probe_echo", "parameters": {"type": "object"}}],
        system="Public test",
        limits={"responses": 3, "tool_calls": 2, "seconds": 10, "output_tokens": 100},
        record=records.append,
        provider_profile="chatgpt-plan",
    )
    assert asyncio.run(loop.run("Test transport")) == "CONNECTED"
    assert dispatched == [("dt_probe_echo", {"value": "CONNECTED"})]
    assert len(seen) == 2


def test_tool_diagnostic_sends_one_request_and_executes_nothing():
    seen = []

    def send(request):
        seen.append(request)
        return response(frames())

    result = asyncio.run(
        probe.request_once(
            "PUBLIC-FAKE",
            transport=httpx.MockTransport(send),
            request=REQUEST,
            validate_result=validate_result,
        )
    )
    assert len(seen) == 1 and result["state"] == "COMPLETED"
    assert result["tool_response_validated"] and result["tool_executions"] == 0


def test_completed_empty_output_is_not_a_successful_tool_diagnostic():
    terminal = frames([])
    result = asyncio.run(
        probe.request_once(
            "PUBLIC-FAKE",
            transport=httpx.MockTransport(lambda request: response(terminal)),
            request=REQUEST,
            validate_result=validate_result,
        )
    )
    assert result["state"] == "UNKNOWN" and result["usage"] == {
        "input_tokens": 10,
        "output_tokens": 5,
    }
    assert "tool_response_validated" not in result


@pytest.mark.parametrize("call_id", ["", "   "])
def test_diagnostic_rejects_empty_call_id_like_actual_loop(call_id):
    events = frames()
    events[3]["item"]["call_id"] = call_id
    result = asyncio.run(
        probe.request_once(
            "PUBLIC-FAKE",
            transport=httpx.MockTransport(lambda request: response(events)),
            request=REQUEST,
            validate_result=validate_result,
        )
    )
    assert result["state"] == "UNKNOWN" and "tool_response_validated" not in result


@pytest.mark.parametrize(
    "warning,servers,rejected",
    [
        (b"[WARN] slack_init.json not found, skipping Slack seed\n", ["OS-filesystem"], False),
        (
            b"[WARN] slack_init.json not found, skipping Slack seed\n",
            ["OS-filesystem", "Slack"],
            True,
        ),
        (b"[WARN] os-filesystem reset failed (may be first run)\n", ["OS-filesystem"], True),
        (b"[WARN] exec_cmd failed\n", ["OS-filesystem"], True),
        (b"command not found", ["OS-filesystem"], True),
    ],
)
def test_only_exact_irrelevant_slack_warning_allowed(warning, servers, rejected):
    config = {"Agent": {"mcp_servers": [{"name": name} for name in servers]}}
    assert invalid_setup_log(warning, config) is rejected
