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


