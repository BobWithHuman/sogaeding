import asyncio
import json

import httpx
import pytest
import siwc_protocol_probe as probe

from app.benchmark.siwc_auth import MODEL
from app.common import canonical


@pytest.mark.parametrize(
    "kind",
    [
        "sse",
        "headerless_sse",
        "headerless_json",
        "json",
        "html",
        "error",
        "partial",
        "redirect",
        "timeout",
    ],
)
def test_one_request_only_and_no_secret_in_report(kind):
    seen = []
    terminal = {
        "type": "response.completed",
        "response": {
            "status": "completed",
            "model": MODEL,
            "output": [],
            "usage": {"input_tokens": 5, "output_tokens": 1},
        },
    }

    def send(request):
        seen.append(request)
        assert json.loads(request.content) == probe.REQUEST
        assert request.headers["accept"] == "text/event-stream"
        if kind == "timeout":
            raise httpx.ReadTimeout("DO-NOT-LOG-TOKEN", request=request)
        status, media, text = (
            200,
            "Text/Event-Stream ; charset=utf-8",
            "data: " + canonical(terminal) + "\n\n",
        )
        if kind == "json":
            media, text = (
                "application/json",
                canonical({"object": "response", "secret": "DO-NOT-LOG-TOKEN"}),
            )
        if kind == "headerless_sse":
            media = ""
        if kind == "headerless_json":
            media, text = "", canonical(terminal["response"])
        if kind == "html":
            media, text = "text/html", "<html>DO-NOT-LOG-TOKEN</html>"
        if kind == "error":
            status, media, text = (
                400,
                "application/json",
                canonical(
                    {
                        "error": {
                            "code": "unsupported_parameter",
                            "param": "stream",
                            "message": "DO-NOT-LOG-TOKEN",
                        }
                    }
                ),
            )
        if kind == "partial":
            text = 'data: {"type":"response.output_text.delta","delta":"DO-NOT-LOG-TOKEN"}\n\n'
        if kind == "redirect":
            status, media, text = 302, "text/html", "DO-NOT-LOG-TOKEN"
        return httpx.Response(
            status,
            headers={"content-type": media, "location": "https://invalid.example"},
            text=text,
        )

    result = asyncio.run(
        probe.request_once("PUBLIC-FAKE-PLAN", transport=httpx.MockTransport(send))
    )
    assert len(seen) == 1
    assert "DO-NOT-LOG-TOKEN" not in canonical(result)
    assert result["state"] == ("COMPLETED" if kind in ("sse", "headerless_sse") else "UNKNOWN")
    if kind == "error":
        assert result["structured_error_code"] == "unsupported_parameter"


def test_claim_cannot_be_reused(tmp_path):
    probe.claim(tmp_path)
    with pytest.raises(FileExistsError):
        probe.claim(tmp_path)


def test_unexpected_error_values_are_never_copied():
    value = probe.safe_body_summary(
        b'{"error":{"code":"DO-NOT-LOG-TOKEN","param":"DO-NOT-LOG-TOKEN","message":"DO-NOT-LOG-TOKEN"}}'
    )
    assert "DO-NOT-LOG-TOKEN" not in canonical(value)
    assert value["structured_error_code"] == "OTHER"


@pytest.mark.parametrize(
    "error,expected",
    [
        (PermissionError("DO-NOT-LOG-TOKEN"), "FILE_PERMISSION"),
        (KeyError("DO-NOT-LOG-TOKEN"), "LOCAL_DATA_SHAPE"),
        (httpx.ReadTimeout("DO-NOT-LOG-TOKEN"), "NETWORK_TIMEOUT"),
        (RuntimeError("DO-NOT-LOG-TOKEN"), "UNEXPECTED_EXCEPTION"),
    ],
)
def test_auth_failure_stage_is_kept_without_exception_text(error, expected, tmp_path):
    stages = []

    class Credentials:
        def __init__(self, **kwargs):
            self.root = tmp_path

        def metadata(self):
            return {"account_binding_sha256": "PUBLIC-ACCOUNT"}

        def read(self, path):
            return {
                "account_binding_sha256": "PUBLIC-ACCOUNT",
                "model": MODEL,
                "reasoning_effort": "low",
            }

        def access(self):
            raise error

    with pytest.raises(type(error)) as caught:
        probe.authenticate(
            {"account_binding_sha256": "PUBLIC-ACCOUNT"},
            stages.append,
            credentials_factory=Credentials,
        )
    report = {"stage": stages[-1], **probe.safe_failure(caught.value)}
    assert report["stage"] == "OAUTH_ACCESS"
    assert report["error_kind"] == expected
    assert "DO-NOT-LOG-TOKEN" not in canonical(report)


def test_unexpected_post_exception_keeps_transport_stage():
    seen = []
    checkpoints = []

    def fail(request):
        seen.append(request)
        raise RuntimeError("DO-NOT-LOG-TOKEN")

    result = asyncio.run(
        probe.request_once(
            "PUBLIC-FAKE", transport=httpx.MockTransport(fail), progress=checkpoints.append
        )
    )
    assert len(seen) == 1
    assert result["stage"] == "RESPONSES_REQUEST"
    assert result["responses_post_attempted"] is True
    assert result["error_kind"] == "UNEXPECTED_EXCEPTION"
    assert checkpoints and "DO-NOT-LOG-TOKEN" not in canonical(result)


def test_arbitrary_exception_class_is_not_logged():
    private = type("DO_NOT_LOG_TOKEN", (Exception,), {})
    assert probe.safe_failure(private("DO-NOT-LOG-TOKEN")) == {
        "exception_class": "OTHER",
        "error_kind": "UNEXPECTED_EXCEPTION",
    }


def test_main_local_failure_after_auth_is_not_labelled_auth(tmp_path, monkeypatch, capsys):
    from pathlib import Path

    monkeypatch.setattr(probe, "Path", lambda name: tmp_path if name == "/evidence" else Path(name))
    monkeypatch.setattr(probe, "verify_bundle", lambda *a: {})
    monkeypatch.setattr("sys.argv", ["probe", "--manifest-sha256", "public", "--send-one-request"])

    def auth(manifest, progress, **kwargs):
        progress("OAUTH_ACCESS")
        return "PUBLIC"

    def fail(*a, **kwargs):
        raise TypeError("DO-NOT-LOG-TOKEN")

    monkeypatch.setattr(probe, "authenticate", auth)
    monkeypatch.setattr(probe, "request_once", fail)
    probe.main()
    result = json.loads(capsys.readouterr().out)
    assert result["stage"] == "RESPONSES_PREPARATION"
    assert result["exception_class"] == "TypeError"
    assert result["responses_post_attempted"] is False
    assert (tmp_path / "one-request.claim").exists()
    assert "DO-NOT-LOG-TOKEN" not in canonical(result)
