"""JSON-lines stdio ↔ actual TLS agentgateway MCP transport; no retry or prompt input."""
import argparse
import importlib.util
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


def send(host, endpoint, body):
    spec = importlib.util.spec_from_file_location("with_human_trusted_hook", Path(__file__).with_name("hookgw_hook.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send(host, endpoint, body)


STAGES = {"initialize": "INITIALIZE", "notifications/initialized": "INITIALIZED", "tools/list": "TOOLS_LIST", "tools/call": "TOOLS_CALL"}
DIAGNOSTIC_CODES = {"HTTP_AUTH_REJECTED", "HTTP_UNAVAILABLE", "TLS_VERIFICATION_FAILED", "TRANSPORT_UNAVAILABLE",
                    "INVALID_RPC_RESPONSE", "RPC_ERROR", "INVALID_INPUT", "CONNECTION_UNAVAILABLE", "ADAPTER_UNAVAILABLE",
                    "HTTP_REJECTION_UNCLASSIFIED", "CONTROL_AUTHENTICATION_REJECTED", "CONTROL_FRESHNESS_REJECTED", "CONTROL_POLICY_OR_STATE_REJECTED"}
AUTH_REASONS = {"AUTHENTICATION_FAILED", "AUTH_RATE_LIMIT", "CONNECTION_BINDING", "CONNECTION_OR_SESSION_EXPIRED"}
STATE_REASONS = {"SESSION_OR_TURN_MISMATCH", "PRIOR_RESULT_UNOBSERVED", "NO_UNIQUE_HOOK_BINDING", "FORWARD_REPLAY", "NO_USER_TURN", "UNSUPPORTED_RPC", "INVALID_RPC", "INVALID_RPC_METADATA"}


def trusted_rejection(host, connection, request_id, value):
    """One diagnostic lookup, never a repeat of tools/call or model analysis."""
    result = {"code": "HTTP_REJECTION_UNCLASSIFIED"}
    if not isinstance(value, dict) or value.get("method") != "tools/call":
        return result
    try:
        params = value["params"]
        receipt = send(host, "/transport-rejection", {"connection": connection, "request_id": request_id,
                       "tool": params["name"], "args": params["arguments"]})
        if not isinstance(receipt, dict) or set(receipt) != {"origin", "reason", "call_ref"} or receipt["origin"] != "CONTROL":
            return result
        reason, call_ref = receipt["reason"], receipt["call_ref"]
        if not isinstance(reason, str) or reason not in AUTH_REASONS | STATE_REASONS | {"FORWARD_SNAPSHOT_STALE"}:
            return result
        if call_ref is not None and (not isinstance(call_ref, str) or not re.fullmatch(r"[a-f0-9]{64}", call_ref)):
            return result
        code = "CONTROL_AUTHENTICATION_REJECTED" if reason in AUTH_REASONS else "CONTROL_FRESHNESS_REJECTED" if reason == "FORWARD_SNAPSHOT_STALE" else "CONTROL_POLICY_OR_STATE_REJECTED"
        return {"code": code, "reason": reason, "call_ref": call_ref}
    except Exception:
        return result


def diagnostic(stage, code, details=None):
    # Only these fixed labels leave the process. Never serialize exception text,
    # RPC bodies, tool arguments, credentials or arbitrary server messages.
    value = {"server": "with_human", "stage": stage if stage in {*STAGES.values(), "BOOTSTRAP", "INPUT"} else "INPUT",
             "code": code if code in DIAGNOSTIC_CODES else "ADAPTER_UNAVAILABLE"}
    if details:
        value.update(details)
    sys.stderr.write("WITH_HUMAN_MCP_DIAGNOSTIC " + json.dumps(value) + "\n")
    sys.stderr.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("host", type=Path)
    host = p.parse_args().host
    try:
        profile = json.loads((host / "profile.json").read_text(encoding="utf-8-sig"))
        url = profile["gateway_url"]
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path != "/mcp" or parsed.query or parsed.fragment or parsed.username:
            raise ValueError()
        context = ssl.create_default_context(cafile=str(host / "ca.pem"))
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
        connection = os.environ["WITH_HUMAN_CONNECTION"]
        if not connection:
            raise KeyError()
    except Exception:
        diagnostic("BOOTSTRAP", "CONNECTION_UNAVAILABLE")
        return 2
    for line in sys.stdin.buffer:
        rid = None
        value = None
        stage, code = "INPUT", "INVALID_INPUT"
        rejection_details = None
        request_id = uuid4().hex
        try:
            if len(line) > 65536:
                raise ValueError()
            value = json.loads(line)
            if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                raise ValueError()
            rid = value.get("id")
            stage = STAGES.get(value.get("method"), "INPUT")
            code = "INVALID_RPC_RESPONSE"
            req = urllib.request.Request(url, line.strip(), {
                "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-03-26", "Authorization": "Bearer " + connection,
                "x-with-human-request": request_id})
            with opener.open(req, timeout=28) as response:
                raw = response.read(65537)
                if rid is None:
                    continue
                if len(raw) > 65536:
                    raise ValueError()
                result = json.loads(raw)
                if not isinstance(result, dict) or result.get("jsonrpc") != "2.0" or result.get("id") != rid:
                    raise ValueError()
                if "error" in result or value.get("method") == "tools/call" and result.get("result", {}).get("isError"):
                    code = "RPC_ERROR"
                    raise ValueError()
                if value.get("method") == "tools/call":
                    send(host, "/transport-observed", {"connection": os.environ["WITH_HUMAN_CONNECTION"], "tool": value["params"]["name"], "args": value["params"]["arguments"], "result": result["result"]})
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError):
                code = "HTTP_UNAVAILABLE"
                if exc.code in (401, 403):
                    receipt = trusted_rejection(host, connection, request_id, value)
                    code = receipt.pop("code")
                    rejection_details = receipt or None
            elif isinstance(exc, ssl.SSLCertVerificationError) or isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, ssl.SSLCertVerificationError):
                code = "TLS_VERIFICATION_FAILED"
            elif isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
                code = "TRANSPORT_UNAVAILABLE"
            diagnostic(stage, code, rejection_details)
            if isinstance(value, dict) and value.get("method") == "tools/call":
                try:
                    send(host, "/transport-failure", {"connection": os.environ["WITH_HUMAN_CONNECTION"], "tool": value["params"]["name"], "args": value["params"]["arguments"]})
                except Exception:
                    # A missing observation keeps the original execution reservation unresolved.
                    sys.stderr.write("WITH_HUMAN_UNKNOWN_OBSERVATION_UNAVAILABLE\n")
            if rid is None:
                continue
            result = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": "WITH_HUMAN_DENIED_OR_UNAVAILABLE; no automatic retry",
                       "data": {"server": "with_human", "stage": stage, "code": code, **(rejection_details or {})}}}
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8") + b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
