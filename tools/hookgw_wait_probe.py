"""Real pinned TLS/mTLS gateway probe against a new isolated clock fixture only."""
import argparse
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--control", default="https://127.0.0.1:8033")
    parser.add_argument("--gateway", default="https://127.0.0.1:8043")
    opts = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    host = root / "artifacts/runtime-hookgw/host-jev"
    machine, human = [(host / name).read_text().strip() for name in ("machine.token", "human.token")]
    context = ssl.create_default_context(cafile=str(host / "ca.pem"))
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
    def req(base, path, token=None, body=None, extra_headers=None):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if token:
            headers["Authorization"] = "Bearer " + token
        headers.update(extra_headers or {})
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, headers)
        try:
            with client.open(request, timeout=28) as reply:
                return reply.status, json.loads(reply.read() or b"{}")
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read())
            except ValueError:
                body = {"gateway_denied": True}
            return exc.code, body
    checks, calls = [], []
    def check(name, passed, **safe):
        checks.append({"name": name, "pass": bool(passed), **safe})
    def fixture(action, **value):
        status, result = req(opts.control, "/fixture-control", machine, {"action": action, **value})
        assert status == 200 and result.get("fixture"), "NOT_ISOLATED_CLOCK_FIXTURE"
    def setup(label, path="fixtures/hookgw/notes.txt"):
        fixture("reset")
        status, data = req(opts.control, "/connect", machine, {})
        assert status == 200
        connection = data["connection"]
        session, turn, call = str(uuid4()), "turn-1", str(uuid4())
        def event(kind, **value):
            return req(opts.control, "/event", machine, {"event": kind, "connection": connection, "session": session, "turn": turn, **value})
        turn_status, turn_result = event("UserPromptSubmit", prompt="Read the public release notes once.", cwd=str(root))
        assert turn_status == 200, (turn_status, turn_result.get("code"), str(root))
        values = {"path": path}
        status, result = event("PreToolUse", call=call, route="mcp", tool="read_file", args=values)
        calls.append({"scenario": label, "call": call, "session": session})
        def rpc(arguments=None):
            actual = arguments or values
            request_id = uuid4().hex
            status, body = req(opts.gateway, "/mcp", connection, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "read_file", "arguments": actual}}, {"x-with-human-request": request_id})
            if status != 200 and not opts.baseline:
                diagnostic_status, diagnostic = req(opts.control, "/transport-rejection", machine, {"connection": connection, "request_id": request_id, "tool": "read_file", "args": actual})
                if diagnostic_status == 200:
                    body = {"trusted_diagnostic": diagnostic}
            return status, body
        return connection, session, call, event, rpc, result, values

    for label, delay in (("immediate", 0), ("wait_91_seconds", 91)):
        connection, session, call, event, rpc, pre, values = setup(label)
        check(label+"_ready", pre.get("state") == "READY")
        if delay:
            fixture("advance", seconds=delay)
        status, output = rpc()
        expected_success = not opts.baseline or not delay
        check(label+"_gateway", (status == 200) == expected_success, status=status, safe_control_code=output.get("code"), clock_advance=delay)
        if status == 200:
            assert req(opts.control, "/transport-observed", machine, {"connection": connection, "tool": "read_file", "args": values, "result": output["result"]})[0] == 200
            post_status, post = event("PostToolUse", call=call, route="mcp", tool="read_file", args=values, output=output["result"])
            check(label+"_observed_source", post_status == 200 and post.get("state") == "OBSERVED" and post.get("analysis_complete"))
            check(label+"_replay_denied", rpc()[0] != 200)
    if not opts.baseline:
        for mutation in ("arguments", "turn", "grant", "policy", "protected", "source", "gap", "unknown", "semantic", "request", "session_expiry", "connection_expiry", "analysis_stop"):
            connection, session, call, event, rpc, pre, values = setup(mutation)
            fixture("advance", seconds=91)
            if mutation == "turn":
                status, _ = req(opts.control, "/event", machine, {"event": "UserPromptSubmit", "connection": connection, "session": session, "turn": "turn-2", "prompt": "A different task.", "cwd": str(root)})
                assert status == 200
            elif mutation != "arguments":
                fixture(mutation, call=call)
            status, result = rpc({"path": "fixtures/hookgw/attack.txt"} if mutation == "arguments" else None)
            check(mutation+"_denied", status != 200, status=status, trusted_diagnostic=result.get("trusted_diagnostic"))
            diagnostic = result.get("trusted_diagnostic", {})
            expected = "NO_UNIQUE_HOOK_BINDING" if mutation in ("arguments", "turn", "unknown") else "PRIOR_RESULT_UNOBSERVED" if mutation == "gap" else "CONNECTION_OR_SESSION_EXPIRED" if mutation in ("session_expiry", "connection_expiry") else "FORWARD_SNAPSHOT_STALE"
            bound = mutation not in ("arguments", "turn", "unknown", "session_expiry", "connection_expiry")
            check(mutation+"_trusted_control_correlation", diagnostic.get("origin") == "CONTROL" and diagnostic.get("reason") == expected and diagnostic.get("call_ref") == (hashlib.sha256(call.encode()).hexdigest() if bound else None))
        connection, session, call, event, rpc, pre, values = setup("concurrent_replay")
        fixture("advance", seconds=91)
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: rpc()[0], range(2)))
        check("concurrent_single_forward", statuses.count(200) == 1, statuses=statuses)
        for path in ("../private", "credentials.json", "docs/plans/00_CONTROL_CENTER.md"):
            _, _, _, _, rpc, result, _ = setup("scope_" + hashlib.sha256(path.encode()).hexdigest()[:8], path)
            check("scope_pre_deny_"+path, result.get("decision") == "DENY")
            check("scope_gateway_deny_"+path, rpc()[0] != 200)
        status, result = req(opts.control, "/connect", "fake-invalid-credential", {})
        check("actual_bad_auth", status in (401, 403) and result.get("code") == "AUTHENTICATION_FAILED", status=status)
        status, result = req(opts.control, "/transport-rejection", machine, {"connection": connection, "request_id": uuid4().hex, "tool": "read_file", "args": values})
        check("unmatched_rejection_remains_unclassified", status == 200 and result == {"origin": "UNCONFIRMED", "code": "HTTP_REJECTION_UNCLASSIFIED"})
        try:
            wrong = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            wrong.open(opts.control + "/health", timeout=5)
            check("untrusted_tls_denied", False)
        except urllib.error.URLError as exc:
            check("untrusted_tls_denied", isinstance(exc.reason, ssl.SSLCertVerificationError))
    fixture("reset")
    status, history = req(opts.control, "/history", human)
    rows = [row for row in history.get("calls", []) if any(row["id"] == call["call"] for call in calls)]
    if not opts.baseline:
        delayed = next(row for row in rows if row["id"] == next(c["call"] for c in calls if c["scenario"] == "wait_91_seconds"))
        context = json.loads(delayed["reason"])
        check("original_analysis_preserved_and_final_recheck_distinct", context.get("forward_check", {}).get("checked_at", 0) - context["analyzed_at"] >= 91 and context["forward_check"]["original_snapshot_sha256"] == context["snapshot_sha256"])
    result = {"utc": datetime.now(UTC).isoformat(), "baseline": opts.baseline, "checks": checks, "calls": calls,
              "history": rows, "paid_model_calls": 0, "actor_calls": 0, "fixture_clock_only": True,
              "human_approval_ui": "NOT_RUN", "pass": all(c["pass"] for c in checks)}
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    if opts.output.exists():
        raise SystemExit("REFUSE_EVIDENCE_OVERWRITE")
    opts.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": sum(c["pass"] for c in checks), "checks": len(checks), "pass": result["pass"], "paid_model_calls": 0}))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
