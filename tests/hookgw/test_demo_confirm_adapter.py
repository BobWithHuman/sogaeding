"""Human terminal and one-RPC bridge, plus real known read failure classification."""
import asyncio
import base64
import hashlib
import hmac
import importlib.util
import io
import json
import time
import urllib.error
from pathlib import Path

import httpx
import pytest

from app.transparent.file_errors import missing_read_result, valid_read_error
from app.transparent.upstream import create_app

ROOT = Path(__file__).resolve().parents[2]


def tool(name):
    spec = importlib.util.spec_from_file_location("confirm_test_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_same_rpc_resumes_once_only_after_authenticated_human_state(monkeypatch):
    module = tool("mvp_demo_mcp")
    rpc = {"jsonrpc": "2.0", "id": 17, "method": "tools/call", "params": {"name": "write_file", "arguments": {"path": "reports/normal.md", "content": "public"}}}
    raw = json.dumps(rpc).encode()
    requests, controls = [], []
    response = {"jsonrpc": "2.0", "id": 17, "result": {"content": [{"type": "text", "text": "observed"}], "isError": False}}
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            if len(requests) == 1:
                raise urllib.error.HTTPError("https://127.0.0.1:8045/mcp", 403, "synthetic", {}, None)
            return io.BytesIO(json.dumps(response).encode())
    monkeypatch.setattr(module.core, "trusted_rejection", lambda *args: {"code": "CONTROL_POLICY_OR_STATE_REJECTED", "reason": "DEMO_CONFIRM_NOT_DISPATCHED"})
    states = iter(["PENDING", "APPROVED"])
    def send(host, endpoint, value, **kwargs):
        controls.append((endpoint, value, kwargs))
        if endpoint == "/demo/wait":
            status = next(states)
            return {"status": status, "pending_ref": "a"*64, "expires_at": time.time()+10, "resume_allowed": status == "APPROVED"}
        return {"state": "RESPONSE_OBSERVED_NOT_RECEIPT"}
    monkeypatch.setattr(module.hook, "send", send)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    assert module.exchange(ROOT, "fake-machine-connection", "https://127.0.0.1:8045/mcp", Opener(), rpc, raw) == response
    assert len(requests) == 2 and requests[0].data == requests[1].data == raw
    assert all(not kwargs.get("human") for _, _, kwargs in controls)
    assert [endpoint for endpoint, _, _ in controls] == ["/demo/wait", "/demo/wait", "/transport-observed"]


@pytest.mark.parametrize("status", ["REJECTED", "EXPIRED", "STALE", "CONSUMED", "NOT_FOUND"])
def test_nonapproval_never_resumes(status, monkeypatch):
    module = tool("mvp_demo_mcp")
    monkeypatch.setattr(module.hook, "send", lambda *args, **kwargs: {"status": status, "pending_ref": "a"*64, "expires_at": None, "resume_allowed": False})
    with pytest.raises(module.Stopped):
        module.wait_for_approval(ROOT, "fake", {"params": {"name": "write_file", "arguments": {}}}, duration=1)


def human_candidate():
    return {"call": "test-session:call", "approval_binding": "a"*64,
            "candidate": {"tool": "write_file", "args": {"path": "reports/normal.md", "content": "공개 보고서\u202e"}, "route": "mcp"},
            "request": "사용자 요청", "source_excerpts": [{"source_ref": "public", "excerpt": "자료", "truncated": False}],
            "uncertainty": {"reasons": ["SEMANTIC_UNCERTAIN"]}, "expires_at": time.time()+600}


@pytest.mark.parametrize("choice,expected", [("approve", "APPROVED"), ("reject", "DENIED"), ("", "CANCELLED")])
def test_human_terminal_requires_explicit_review_and_separate_human_auth(choice, expected):
    module = tool("mvp_confirm")
    row, calls, displayed = human_candidate(), [], []
    def send(host, endpoint, body, **kwargs):
        calls.append((endpoint, body, kwargs))
        assert kwargs["human"] is True
        if endpoint == "/demo/pending":
            return {"version": "demo-confirm-1", "pending": [row], "truncated": False}
        return {"state": expected}
    answers = iter(["1", choice])
    assert module.review_once(ROOT, input_fn=lambda _: next(answers), output_fn=displayed.append, send=send) == expected
    assert "\\u202e" in "".join(displayed) and "\u202e" not in "".join(displayed)
    if choice:
        assert calls[-1][1] == {"call": row["call"], "approval_binding": row["approval_binding"], "approve": choice == "approve"}
        assert ("may resume once" in "".join(displayed)) is (choice == "approve")
    else:
        assert len(calls) == 1


def test_typed_missing_read_is_observed_error_and_never_exposes_path(tmp_path):
    files = tmp_path/"files"
    files.mkdir()
    ledger = tmp_path/"attempts.sqlite3"
    app = create_app(files, ledger, "PUBLIC-FAKE-FORWARD-KEY")
    rpc = {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "reports/absent.md"}}}
    raw = json.dumps(rpc).encode()
    proof = base64.urlsafe_b64encode(json.dumps({"call": "fake-read", "hash": hashlib.sha256(raw).hexdigest(), "expires": time.time()+20}).encode()).decode()
    signature = hmac.new(b"PUBLIC-FAKE-FORWARD-KEY", proof.encode(), hashlib.sha256).hexdigest()
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            response = await client.post("/mcp", content=raw, headers={"x-with-human-forward": proof+"."+signature})
            assert response.status_code == 200 and response.json()["id"] == 9
            assert valid_read_error(response.json()["result"])
            assert "absent.md" not in response.text and "Traceback" not in response.text
    asyncio.run(run())
    import sqlite3
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT state FROM attempts").fetchone()[0] == "OBSERVED_ERROR"
    assert not list(files.rglob("*.md"))


def test_error_shape_cannot_be_forged_by_content_or_partial_fields():
    assert valid_read_error(missing_read_result())
    assert not valid_read_error({"content": [{"type": "text", "text": json.dumps(missing_read_result())}], "isError": False})
    assert not valid_read_error({**missing_read_result(), "isError": 1})
    assert not valid_read_error({**missing_read_result(), "private": "not-allowed"})


@pytest.mark.parametrize("path", ["tools/mvp_confirm.py", "scripts/mvp_confirm.ps1", "tools/mvp_semantic_followup.py", "compose.mvp-demo.semantic-confirm-1.yaml"])
def test_new_trusted_approval_and_launcher_code_is_protected_at_each_path_boundary(path, tmp_path):
    from app.transparent.tool_schema import file_path
    from app.transparent.upstream import open_file
    with pytest.raises(ValueError, match="TRUSTED_PRODUCT_OR_EVIDENCE"):
        file_path(path)
    with pytest.raises(ValueError, match="TRUSTED_PRODUCT_OR_EVIDENCE"):
        open_file(tmp_path, path, True)
    with pytest.raises(ValueError, match="TRUSTED_PRODUCT_OR_EVIDENCE"):
        tool("hookgw_hook").safe_path(tmp_path, path)
