import asyncio
import json

import httpx
import pytest
from test_siwc_login import budget, completed

from app.benchmark.runtime_budget import StopRun
from app.benchmark.siwc_transport import PlanMeter, completed_stream


def terminal(**changes):
    value = completed()
    value.update(changes)
    return (
        "data: " + json.dumps({"type": "response.completed", "response": value}) + "\n\n"
    ).encode()


@pytest.mark.parametrize("tail", [b"data: [DONE]", b"data: [DONE]\n", b"data: [DONE]\r\n"])
def test_complete_response_with_exact_eof_done_marker_is_not_a_truncated_result(tail):
    detail = {}
    result = asyncio.run(
        completed_stream(
            httpx.Response(200, content=terminal() + tail), maximum=100000, diagnostic=detail
        )
    )
    assert result["status"] == "completed" and detail["trailing_done_ignored"]
    assert detail["terminal_seen"] and detail["model_matches"]


@pytest.mark.parametrize(
    "raw,seen,kind",
    [
        (b"data: [DONE]", False, "DONE_SENTINEL"),
        (b'data: {"type":"response.completed"}', False, "UNFRAMED"),
        (terminal() + b'data: {"secret":"NEVER_LOG"}', True, "UNFRAMED"),
        (terminal(model="WRONG_MODEL"), True, "EMPTY"),
        (terminal(status="in_progress"), True, "EMPTY"),
        (b"", False, "EMPTY"),
    ],
)
def test_missing_completion_or_arbitrary_tail_and_wrong_identity_still_stop(raw, seen, kind):
    detail = {}
    with pytest.raises(StopRun):
        asyncio.run(
            completed_stream(httpx.Response(200, content=raw), maximum=100000, diagnostic=detail)
        )
    assert detail["terminal_seen"] is seen and detail["pending_kind"] == kind
    encoded = json.dumps(detail)
    assert "NEVER_LOG" not in encoded and "WRONG_MODEL" not in encoded
    assert "encrypted_content" not in encoded


def test_diagnostics_are_bound_and_cannot_persist_provider_text(tmp_path, monkeypatch):
    b = budget(tmp_path, monkeypatch)
    meter = PlanMeter(b)
    rid = meter.reserve({"task": "task", "arm": "engine-on", "provider": "environment"}, 10)
    detail = {}
    asyncio.run(
        completed_stream(httpx.Response(200, content=terminal()), maximum=100000, diagnostic=detail)
    )
    meter.observe_stream(rid, detail)
    meter.record(rid, {"input_tokens": 1, "output_tokens": 1})
    with b.db() as db:
        assert (
            json.loads(
                db.execute(
                    "SELECT detail FROM plan_stream_observations WHERE request_id=?", (rid,)
                ).fetchone()[0]
            )
            == detail
        )
    with pytest.raises(StopRun):
        meter.observe_stream(rid, detail)
    with pytest.raises(StopRun):
        meter.observe_stream("unbound", detail)
    with pytest.raises(StopRun):
        meter.observe_stream("unbound", {**detail, "terminal_status": "NEVER_LOG"})


def test_original_shaped_permission_probe_is_one_request_no_action():
    from pathlib import Path

    import siwc_protocol_probe as probe
    from siwc_permission_probe import request_from_official, validate_result

    official = Path(
        "/workspace/artifacts/20261017-dtap-prepare/vendor/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/os-filesystem/main.py"
    )
    wire = request_from_official(official.read_text())
    assert wire["input"][0]["role"] == "developer" and wire["parallel_tool_calls"] is False
    assert "SIMULATOR" in wire["input"][0]["content"] and "tools" not in wire
    sent = []

    def send(request):
        sent.append(request)
        assert json.loads(request.content) == wire
        output = [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"decision":"APPROVED","reasoning":"Public diagnostic only"}',
                    }
                ],
            }
        ]
        return httpx.Response(200, content=terminal(output=output) + b"data: [DONE]")

    result = asyncio.run(
        probe.request_once(
            "PUBLIC-PROBE-ACCESS",
            transport=httpx.MockTransport(send),
            request=wire,
            validate_result=validate_result,
        )
    )
    assert len(sent) == 1 and result["state"] == "COMPLETED"
    assert result["permission_response_validated"] and result["tool_executions"] == 0
    assert result["decision_applied"] is False and result["benchmark_score"] == "NOT_APPLICABLE"
    assert "PUBLIC-PROBE-ACCESS" not in json.dumps(result)
