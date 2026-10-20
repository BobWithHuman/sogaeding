"""Bounded, model-free startup of the actual stdio bridge. Never tools/call.

The only persistent operation is a temporary unbound connection, removed in
finally. No user turn, candidate, source, judge adapter or budget claim is made.
"""
import importlib.util
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

STAGES = {"INITIALIZE", "INITIALIZED", "TOOLS_LIST", "BOOTSTRAP", "INPUT"}
CODES = {"HTTP_AUTH_REJECTED", "HTTP_UNAVAILABLE", "TLS_VERIFICATION_FAILED", "TRANSPORT_UNAVAILABLE",
         "INVALID_RPC_RESPONSE", "RPC_ERROR", "INVALID_INPUT", "CONNECTION_UNAVAILABLE", "ADAPTER_UNAVAILABLE", "HTTP_REJECTION_UNCLASSIFIED"}
PREFIX = b"WITH_HUMAN_MCP_DIAGNOSTIC "


class ProbeFailure(Exception):
    def __init__(self, stage, code):
        self.stage, self.code = stage, code


def helper_send():
    spec = importlib.util.spec_from_file_location("with_human_probe_hook", Path(__file__).with_name("hookgw_hook.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send


def safe_diagnostic(raw):
    if not raw.startswith(PREFIX) or len(raw) > 1024:
        return None
    try:
        value = json.loads(raw[len(PREFIX):])
        if set(value) == {"server", "stage", "code"} and value["server"] == "with_human" and value["stage"] in STAGES and value["code"] in CODES:
            return value
    except (TypeError, ValueError):
        pass
    return None


def exchange(root, host, connection, timeout):
    # Same executable, -I flag, script and host arguments installed by launcher.
    env = {**os.environ, "WITH_HUMAN_CONNECTION": connection}
    env.pop("OPENAI_API_KEY", None)  # This process never needs actor credentials.
    proc = subprocess.Popen([sys.executable, "-I", str(root / "tools/hookgw_mcp.py"), str(host)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    replies, diagnostics = queue.Queue(maxsize=4), []
    def read_stdout():
        for _ in range(3):
            raw = proc.stdout.readline(65538)
            replies.put(raw)
            if not raw:
                break
    def read_stderr():
        for _ in range(16):
            raw = proc.stderr.readline(1025)
            if not raw:
                break
            safe = safe_diagnostic(raw)
            if safe:
                diagnostics.append(safe)
    stdout = threading.Thread(target=read_stdout, daemon=True)
    stderr = threading.Thread(target=read_stderr, daemon=True)
    stdout.start()
    stderr.start()
    stage = "INITIALIZE"
    def write(method, rid=None, params=None):
        value = {"jsonrpc": "2.0", "method": method}
        if rid is not None:
            value["id"] = rid
        if params is not None:
            value["params"] = params
        proc.stdin.write(json.dumps(value).encode() + b"\n")
        proc.stdin.flush()
    def read(rid):
        try:
            raw = replies.get(timeout=timeout)
        except queue.Empty:
            raise ProbeFailure(stage, "TIMEOUT") from None
        if not raw:
            stderr.join(timeout=0.2)
            if diagnostics:
                first = diagnostics[0]
                raise ProbeFailure(first["stage"], first["code"])
            raise ProbeFailure(stage, "PROCESS_EXIT")
        try:
            value = json.loads(raw)
            if len(raw) > 65536 or not isinstance(value, dict) or value.get("jsonrpc") != "2.0" or value.get("id") != rid:
                raise ValueError()
            if "error" in value:
                data = value["error"].get("data", {})
                code = data.get("code") if data.get("server") == "with_human" and data.get("stage") == stage else None
                raise ProbeFailure(stage, code if code in CODES else "RPC_ERROR")
            if not isinstance(value.get("result"), dict):
                raise ValueError()
            return value["result"]
        except (TypeError, ValueError, AttributeError):
            raise ProbeFailure(stage, "INVALID_RPC_RESPONSE") from None
    completed = []
    try:
        write("initialize", 1, {"protocolVersion": "2025-03-26", "capabilities": {},
                                "clientInfo": {"name": "with-human-preflight", "version": "1"}})
        result = read(1)
        capabilities, server = result.get("capabilities"), result.get("serverInfo")
        if result.get("protocolVersion") != "2025-03-26" or not isinstance(capabilities, dict) or not isinstance(capabilities.get("tools"), dict) or not isinstance(server, dict) or server.get("name") != "with-human-enrolled-files":
            raise ProbeFailure(stage, "INITIALIZE_CONTRACT_MISMATCH")
        completed.append(stage)
        stage = "INITIALIZED"
        write("notifications/initialized")
        stage = "TOOLS_LIST"
        write("tools/list", 2, {})
        result = read(2)
        tools = result.get("tools")
        if not isinstance(tools, list) or len(tools) != 2 or any(not isinstance(t, dict) or not isinstance(t.get("name"), str) or not isinstance(t.get("inputSchema"), dict) for t in tools) or {t["name"] for t in tools} != {"read_file", "write_file"}:
            raise ProbeFailure(stage, "TOOLS_CONTRACT_MISMATCH")
        proc.stdin.close()
        proc.wait(timeout=timeout)
        stderr.join(timeout=1)
        if diagnostics:
            first = diagnostics[0]
            raise ProbeFailure(first["stage"], first["code"])
        if proc.returncode:
            raise ProbeFailure(stage, "PROCESS_EXIT")
        completed += ["INITIALIZED", "TOOLS_LIST"]
        return {"ready": True, "completed": completed, "stage": "COMPLETE", "code": "OK", "tool_names": ["read_file", "write_file"]}
    except ProbeFailure:
        raise
    except subprocess.TimeoutExpired:
        raise ProbeFailure(stage, "TIMEOUT") from None
    except (OSError, ValueError):
        raise ProbeFailure(stage, "PROCESS_IO_UNAVAILABLE") from None
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=3)
        stdout.join(timeout=1)
        stderr.join(timeout=1)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()


def probe(root, host, timeout=10):
    report = {"server": "with_human", "ready": False, "stage": "CONNECT", "code": "CONNECTION_UNAVAILABLE",
              "paid_requests": 0, "tools_call_count": 0, "user_turn_count": 0, "candidate_count": 0,
              "other_personal_mcp_servers": "NOT_INSPECTED", "original_startup_issue_server": "UNDETERMINED",
              "connection_cleanup": "NOT_CREATED"}
    connection = None
    try:
        send = helper_send()
        connection = send(host, "/connect", {}, timeout=5)["connection"]
        if not isinstance(connection, str) or not connection:
            connection = None
            raise ValueError()
        report["connection_cleanup"] = "PENDING"
        report.update(exchange(root, host, connection, timeout))
    except ProbeFailure as exc:
        report.update(stage=exc.stage, code=exc.code)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ImportError, subprocess.SubprocessError):
        pass
    finally:
        if connection:
            try:
                result = send(host, "/disconnect", {"connection": connection}, timeout=5)
                if result.get("state") != "DISCONNECTED":
                    raise ValueError()
                report["connection_cleanup"] = "REMOVED_UNBOUND_CONNECTION"
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                report.update(ready=False, connection_cleanup="FAILED", stage="DISCONNECT", code="CONNECTION_CLEANUP_UNAVAILABLE")
    return report
