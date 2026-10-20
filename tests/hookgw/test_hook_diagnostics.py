"""No external network/model: fixed diagnostics, fake control and local redirect test."""

import importlib.util
import io
import json
import ssl
import sys
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest


@pytest.fixture
def hook(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("diagnostic_hook", Path(__file__).resolve().parents[2] / "tools/hookgw_hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "profile.json").write_text(json.dumps({"workspace": str(tmp_path)}))
    monkeypatch.setenv("WITH_HUMAN_CONNECTION", "private-connection-value")
    monkeypatch.setattr(sys, "argv", ["hookgw_hook.py", str(tmp_path)])
    return module


def event(tmp_path, kind="PreToolUse", **extra):
    return {"hook_event_name": kind, "session_id": "private-session", "turn_id": "private-turn",
            "cwd": str(tmp_path), "tool_name": "mcp__with_human__read_file",
            "tool_use_id": "private-call", "tool_input": {"path": "private-payload"},
            "prompt": "private-prompt", "tool_response": "private-tool-response", **extra}


def run_main(hook, monkeypatch, capsys, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(raw)))
    hook.main()
    result = capsys.readouterr()
    assert "private-" not in result.out + result.err
    return json.loads(result.out), json.loads(result.err) if result.err else None


def assert_deny(value, stage, code):
    specific = value["hookSpecificOutput"]
    assert specific["permissionDecision"] == "deny"
    assert specific["permissionDecisionReason"] == f"WITH_HUMAN_{stage}:{code}"


@pytest.mark.parametrize("raw,stage,code", [(b'{invalid-private-secret', "PARSE", "INVALID_JSON"),
                                           (b'[]', "PARSE", "EVENT_SCHEMA_INVALID"),
                                           (b'x' * 131073, "INPUT_READ", "EVENT_LIMIT"),
                                           (b'{"hook_event_name":"Other"}', "PARSE", "UNSUPPORTED_HOOK_EVENT")])
def test_input_metadata_only(hook, tmp_path, monkeypatch, capsys, raw, stage, code):
    value, metadata = run_main(hook, monkeypatch, capsys, raw)
    assert_deny(value, stage, code)
    assert metadata == {"component": "with_human_hook", "stage": stage, "code": code}


def test_missing_prompt_blocks_user_event(hook, tmp_path, monkeypatch, capsys):
    data = event(tmp_path, "UserPromptSubmit")
    data.pop("prompt")
    value, metadata = run_main(hook, monkeypatch, capsys, data)
    assert value == {"decision": "block", "reason": "WITH_HUMAN_PARSE:EVENT_SCHEMA_INVALID"}
    assert metadata["stage"] == "PARSE"


def test_workspace_mismatch_and_native_scope_distinct(hook, tmp_path, monkeypatch, capsys):
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path, cwd=str(tmp_path / "other")))
    assert_deny(value, "WORKSPACE", "WORKSPACE_MISMATCH")
    assert metadata["code"] == "WORKSPACE_MISMATCH"
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path, tool_name="Bash", tool_input={"command": "private-command | bad"}))
    assert_deny(value, "NATIVE_SCOPE", "UNSUPPORTED_SHELL_SYNTAX")
    assert metadata["stage"] == "NATIVE_SCOPE"


@pytest.mark.parametrize("error,code", [
    (urllib.error.HTTPError("https://private-url", 403, "private-body", {}, None), "HTTP_403"),
    (urllib.error.HTTPError("https://private-url", 418, "private-body", {}, None), "HTTP_ERROR"),
    (urllib.error.HTTPError("https://private-url", 302, "private-body", {}, None), "HTTP_REDIRECT"),
    (urllib.error.URLError(ssl.SSLError("private-TLS")), "TLS_ERROR"),
    (urllib.error.URLError(TimeoutError("private-timeout")), "CONTROL_TIMEOUT"),
    (urllib.error.URLError("private-unavailable"), "CONTROL_UNAVAILABLE"),
    (ValueError("private-exception-with-Authorization"), "ADAPTER_UNAVAILABLE"),
])
def test_control_failure_no_raw_error_bytes(hook, tmp_path, monkeypatch, capsys, error, code):
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(hook, "send", failed)
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path))
    assert_deny(value, "CONTROL_EVENT", code)
    assert metadata["code"] == code


def test_post_failure_reports_only_safe_metadata_no_preexecution_claim(hook, tmp_path, monkeypatch, capsys):
    def failed(*args, **kwargs):
        raise RuntimeError("private-tool-response")
    monkeypatch.setattr(hook, "send", failed)
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path, "PostToolUse"))
    assert value == {}  # post reporting cannot retroactively prevent execution
    assert metadata == {"component": "with_human_hook", "stage": "CONTROL_EVENT", "code": "ADAPTER_UNAVAILABLE"}


@pytest.mark.parametrize("kind", ["PreToolUse", "PostToolUse", "UserPromptSubmit"])
def test_success_keeps_codex_own_approval_and_model_free(hook, tmp_path, monkeypatch, capsys, kind):
    calls = []
    def send(*args, **kwargs):
        calls.append((args, kwargs))
        return {"decision": "ALLOW"}
    monkeypatch.setattr(hook, "send", send)
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path, kind))
    assert value == {} and metadata is None and len(calls) == 1


def test_missing_connection_and_unknown_internal_error(hook, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("WITH_HUMAN_CONNECTION")
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path))
    assert_deny(value, "PARSE", "MISSING_CONNECTION")
    monkeypatch.setenv("WITH_HUMAN_CONNECTION", "private-connection")
    monkeypatch.setattr(hook, "handle", lambda *args: 1 / 0)
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path))
    assert_deny(value, "INTERNAL", "ADAPTER_UNAVAILABLE")


def test_approval_poll_failure_and_timeout_settings_unchanged(hook, tmp_path, monkeypatch, capsys):
    calls = []
    def send(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {"decision": "CONFIRM", "action_hash": "bound-hash"}
        raise urllib.error.HTTPError("https://private-url", 503, "private-body", {}, None)
    monkeypatch.setattr(hook, "send", send)
    monkeypatch.setattr(hook.time, "sleep", lambda _: None)
    raw = json.dumps(event(tmp_path)).encode()
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(raw)))
    hook.main()
    result = capsys.readouterr()
    assert "private-" not in result.out + result.err
    assert_deny(json.loads(result.out), "APPROVAL_POLL", "HTTP_503")
    assert json.loads(result.err.splitlines()[-1])["stage"] == "APPROVAL_POLL"
    assert calls == [{}, {"timeout": 5}]


def test_pending_poll_keeps_original_hash_then_approval_allows_without_codex_bypass(hook, tmp_path, monkeypatch, capsys):
    calls = []
    responses = iter([
        {"decision": "CONFIRM", "action_hash": "exact-original-action-hash"},
        {"state": "CONFIRM", "decision": "CONFIRM"},
        {"state": "READY", "decision": "ALLOW"},
    ])
    def send(_host, endpoint, body, **kwargs):
        calls.append((endpoint, dict(body), kwargs))
        return next(responses)
    monkeypatch.setattr(hook, "send", send)
    monkeypatch.setattr(hook.time, "sleep", lambda _: None)
    raw = json.dumps(event(tmp_path)).encode()
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(raw)))
    hook.main()
    result = capsys.readouterr()
    assert json.loads(result.out) == {}  # With Human ALLOW does not override Codex approval.
    assert result.err.strip() == "With Human exception: human approval required"
    assert len(calls) == 3
    assert "action_hash" not in calls[0][1]
    for endpoint, body, kwargs in calls[1:]:
        assert endpoint == "/event" and body["event"] == "ApprovalPoll"
        assert body["action_hash"] == "exact-original-action-hash"
        assert body["call"] == calls[0][1]["call"]
        assert body["args"] == calls[0][1]["args"]
        assert kwargs == {"timeout": 5}


def test_untrusted_control_shape_fails_closed(hook, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "send", lambda *args, **kwargs: {"decision": "private-malicious"})
    value, metadata = run_main(hook, monkeypatch, capsys, event(tmp_path))
    assert_deny(value, "CONTROL_EVENT", "RESPONSE_INVALID")


def test_urllib_redirect_handler_never_sends_authorization_to_redirect_target(hook):
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.path, self.headers.get("Authorization")))
            self.send_response(302 if self.path == "/origin" else 200)
            self.send_header("Location", "/forbidden-redirect-target")
            self.end_headers()

        def log_message(self, *_):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        opener = hook.urllib.request.build_opener(hook.urllib.request.ProxyHandler({}), hook.NoRedirect())
        request = hook.urllib.request.Request(f"http://127.0.0.1:{server.server_port}/origin", headers={"Authorization": "Bearer offline-fake-only"})
        with pytest.raises(urllib.error.HTTPError) as error:
            opener.open(request, timeout=2)
        assert error.value.code == 302
        assert calls == [("/origin", "Bearer offline-fake-only")]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_send_installs_no_redirect_and_disables_environment_proxy(hook, tmp_path, monkeypatch):
    captured = []
    (tmp_path / "machine.token").write_text("offline-fake-only")
    (tmp_path / "profile.json").write_text(json.dumps({"control_url": "https://127.0.0.1:8030"}))
    monkeypatch.setattr(hook.ssl, "create_default_context", lambda **kwargs: None)
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, limit):
            assert limit == 131073
            return b'{}'
    class Opener:
        def open(self, request, timeout):
            assert timeout == 25
            return Response()
    def build(*handlers):
        captured.extend(handlers)
        return Opener()
    monkeypatch.setattr(hook.urllib.request, "build_opener", build)
    assert hook.send(tmp_path, "/event", {"event": "offline"}) == {}
    assert any(isinstance(item, hook.NoRedirect) for item in captured)
    assert next(item for item in captured if isinstance(item, hook.urllib.request.ProxyHandler)).proxies == {}
