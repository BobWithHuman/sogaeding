"""No-model startup diagnostics: protocol metadata only, never tools/call."""
import importlib.util
import io
import json
import ssl
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def metadata_bridge(tmp_path):
    (tmp_path / "tools").mkdir()
    script = tmp_path / "tools/hookgw_mcp.py"
    script.write_text('''import sys,json
for line in sys.stdin.buffer:
 v=json.loads(line);method=v["method"]
 assert method in ("initialize","notifications/initialized","tools/list")
 if method=="notifications/initialized":continue
 r={"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"with-human-enrolled-files"}} if method=="initialize" else {"tools":[{"name":x,"inputSchema":{"type":"object"}} for x in ("read_file","write_file")]}
 print(json.dumps({"jsonrpc":"2.0","id":v["id"],"result":r}),flush=True)
''', encoding="utf-8")
    return tmp_path


def test_real_stdio_subprocess_metadata_order_and_cleanup(metadata_bridge, monkeypatch):
    mod = load("hookgw_mcp_probe")
    observed = []
    def send(_host, endpoint, body, **_kwargs):
        observed.append(endpoint)
        return {"connection": "not-a-real-secret"} if endpoint == "/connect" else {"state": "DISCONNECTED"}
    monkeypatch.setattr(mod, "helper_send", lambda: send)
    report = mod.probe(metadata_bridge, metadata_bridge)
    assert report["ready"] and report["completed"] == ["INITIALIZE", "INITIALIZED", "TOOLS_LIST"]
    assert observed == ["/connect", "/disconnect"]
    assert report["connection_cleanup"] == "REMOVED_UNBOUND_CONNECTION"
    assert all(report[x] == 0 for x in ("paid_requests", "tools_call_count", "user_turn_count", "candidate_count"))
    assert report["original_startup_issue_server"] == "UNDETERMINED"
    assert report["other_personal_mcp_servers"] == "NOT_INSPECTED"
    assert "not-a-real-secret" not in json.dumps(report)


@pytest.mark.parametrize("failure", ["malformed", "rpc_error", "wrong_id", "capabilities", "server_info", "tools", "tool_name_type", "notification", "exit"])
def test_startup_failure_stages_are_safe_and_clean_connection(metadata_bridge, monkeypatch, failure):
    path = metadata_bridge / "tools/hookgw_mcp.py"
    script = path.read_text()
    if failure == "malformed":
        script = 'print("not-json private-value",flush=True)'
    elif failure == "rpc_error":
        script = script.replace('"result":r', '"error":{"message":"raw secret","code":-32000}')
    elif failure == "wrong_id":
        script = script.replace('"id":v["id"]', '"id":999')
    elif failure == "capabilities":
        script = script.replace('"capabilities":{"tools":{}}', '"capabilities":[]')
    elif failure == "server_info":
        script = script.replace('"serverInfo":{"name":"with-human-enrolled-files"}', '"serverInfo":None')
    elif failure == "tools":
        script = script.replace('("read_file","write_file")', '("unexpected_private_name","write_file")')
    elif failure == "tool_name_type":
        script = script.replace('"name":x', '"name":[]')
    elif failure == "notification":
        script = script.replace('if method=="notifications/initialized":continue', 'if method=="notifications/initialized":\n  print(\'WITH_HUMAN_MCP_DIAGNOSTIC {"server":"with_human","stage":"INITIALIZED","code":"HTTP_AUTH_REJECTED"}\',file=sys.stderr,flush=True);continue')
    else:
        script = "raise SystemExit(2)"
    path.write_text(script)
    mod = load("hookgw_mcp_probe")
    ends = []
    def send(_host, endpoint, body, **_kwargs):
        ends.append(endpoint)
        return {"connection": "secret"} if endpoint == "/connect" else {"state": "DISCONNECTED"}
    monkeypatch.setattr(mod, "helper_send", lambda: send)
    report = mod.probe(metadata_bridge, metadata_bridge)
    assert not report["ready"] and ends[-1] == "/disconnect"
    assert report["stage"] == ("TOOLS_LIST" if failure in ("tools", "tool_name_type") else "INITIALIZED" if failure == "notification" else "INITIALIZE")
    assert "secret" not in json.dumps(report) and "private" not in json.dumps(report)


def test_probe_cleanup_failure_blocks_preflight_even_if_metadata_succeeded(metadata_bridge, monkeypatch):
    mod = load("hookgw_mcp_probe")
    def send(_host, endpoint, body, **_kwargs):
        if endpoint == "/disconnect":
            raise OSError("private error")
        return {"connection": "secret"}
    monkeypatch.setattr(mod, "helper_send", lambda: send)
    report = mod.probe(metadata_bridge, metadata_bridge)
    assert not report["ready"] and report["stage"] == "DISCONNECT" and report["connection_cleanup"] == "FAILED"
    assert "private error" not in json.dumps(report)


def test_helper_import_failure_is_safe_report(metadata_bridge, monkeypatch):
    mod = load("hookgw_mcp_probe")
    def fail():
        raise ImportError("private exception")
    monkeypatch.setattr(mod, "helper_send", fail)
    report = mod.probe(metadata_bridge, metadata_bridge)
    assert not report["ready"] and report["code"] == "CONNECTION_UNAVAILABLE"
    assert "private exception" not in json.dumps(report)


@pytest.mark.parametrize("value", [b'raw exception secret', b'WITH_HUMAN_MCP_DIAGNOSTIC {"server":"private","stage":"INITIALIZE","code":"RPC_ERROR"}',
                                  b'WITH_HUMAN_MCP_DIAGNOSTIC {"server":"with_human","stage":"INITIALIZE","code":"RPC_ERROR","body":"secret"}'])
def test_diagnostic_allowlist_rejects_untrusted_details(value):
    assert load("hookgw_mcp_probe").safe_diagnostic(value) is None


@pytest.mark.parametrize("failure,expected", [("auth", "HTTP_REJECTION_UNCLASSIFIED"), ("tls", "TLS_VERIFICATION_FAILED"),
                                             ("network", "TRANSPORT_UNAVAILABLE"), ("body", "INVALID_RPC_RESPONSE")])
def test_actual_bridge_failure_is_structured_without_raw_secrets(tmp_path, monkeypatch, failure, expected):
    mod = load("hookgw_mcp")
    (tmp_path / "profile.json").write_text(json.dumps({"gateway_url": "https://127.0.0.1:8040/mcp"}))
    monkeypatch.setattr(mod.ssl, "create_default_context", lambda **_: object())
    monkeypatch.setenv("WITH_HUMAN_CONNECTION", "secret-not-to-log")
    class Opener:
        def open(self, *_args, **_kwargs):
            if failure == "auth":
                raise urllib.error.HTTPError("https://secret", 403, "secret reason", {}, None)
            if failure == "tls":
                raise urllib.error.URLError(ssl.SSLCertVerificationError("secret reason"))
            if failure == "network":
                raise urllib.error.URLError("secret reason")
            return self
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self, *_):
            return b"not-json secret body"
    monkeypatch.setattr(mod.urllib.request, "build_opener", lambda *_: Opener())
    source = io.TextIOWrapper(io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'), encoding="utf-8")
    target = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    error = io.StringIO()
    monkeypatch.setattr(sys, "stdin", source)
    monkeypatch.setattr(sys, "stdout", target)
    monkeypatch.setattr(sys, "stderr", error)
    monkeypatch.setattr(sys, "argv", ["bridge", str(tmp_path)])
    mod.main()
    target.flush()
    report = json.loads(target.buffer.getvalue())
    assert report["error"]["data"] == {"server": "with_human", "stage": "INITIALIZE", "code": expected}
    assert "secret" not in target.buffer.getvalue().decode() + error.getvalue()


def test_preflight_reflects_stdio_startup_failure(tmp_path, monkeypatch):
    mod = load("hookgw_preflight")
    monkeypatch.setattr(mod, "mcp_startup", lambda *_: {"server": "with_human", "ready": False, "stage": "TOOLS_LIST", "code": "HTTP_AUTH_REJECTED"})
    monkeypatch.setattr(mod, "command", lambda *_: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(mod, "tls_health", lambda *_: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(mod, "control_probe", lambda *_: (_ for _ in ()).throw(OSError()))
    report = mod.run(tmp_path, tmp_path, "not-a-real-executable", [], "gpt-5.6-luna")
    assert not report["ready_to_open_cli"] and "WITH_HUMAN_MCP_STARTUP_FAILED" in report["issues"]
    assert report["mcp_startup"]["stage"] == "TOOLS_LIST" and report["paid_requests"] == 0


def test_actual_bridge_truthy_nondict_input_is_safe_diagnostic(tmp_path, monkeypatch):
    mod = load("hookgw_mcp")
    (tmp_path / "profile.json").write_text(json.dumps({"gateway_url": "https://127.0.0.1:8040/mcp"}))
    monkeypatch.setattr(mod.ssl, "create_default_context", lambda **_: object())
    monkeypatch.setattr(mod.urllib.request, "build_opener", lambda *_: None)
    monkeypatch.setenv("WITH_HUMAN_CONNECTION", "secret-not-to-log")
    source = io.TextIOWrapper(io.BytesIO(b'[1]\n'), encoding="utf-8")
    target = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    error = io.StringIO()
    monkeypatch.setattr(sys, "stdin", source)
    monkeypatch.setattr(sys, "stdout", target)
    monkeypatch.setattr(sys, "stderr", error)
    monkeypatch.setattr(sys, "argv", ["bridge", str(tmp_path)])
    mod.main()
    target.flush()
    assert target.buffer.getvalue() == b""
    diagnostic = load("hookgw_mcp_probe").safe_diagnostic(error.getvalue().encode())
    assert diagnostic == {"server": "with_human", "stage": "INPUT", "code": "INVALID_INPUT"}
    assert "secret" not in error.getvalue()
