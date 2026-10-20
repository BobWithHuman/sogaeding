"""OFFLINE real gateway fault/negative TLS probe. No paid API, no old services."""
import argparse
import hashlib
import json
import socket
import ssl
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("authz-down", "upstream-down", "tls-negative"))
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve existing evidence")
    root = Path(__file__).resolve().parents[1]
    host = root / "artifacts/runtime-hookgw/host"
    context = ssl.create_default_context(cafile=str(host / "ca.pem"))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
    machine = (host / "machine.token").read_text().strip()
    human = (host / "human.token").read_text().strip()
    checks = []
    def req(url, data=None, credential=machine):
        request = urllib.request.Request(url, json.dumps(data).encode() if data is not None else None,
                                         {"Authorization": "Bearer " + credential, "Content-Type": "application/json"})
        try:
            with opener.open(request, timeout=28) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, {}
    def check(name, yes, **metadata):
        checks.append({"name": name, "pass": bool(yes), **metadata})
        assert yes, name
    status, health = req("https://127.0.0.1:8031/health")
    check("offline_fixture_only", status == 200 and health.get("judge_mode") == "OFFLINE_FIXTURE")
    if args.mode == "tls-negative":
        for label, ctx, hostname in [("untrusted_ca", ssl.create_default_context(), "localhost"),
                                      ("wrong_hostname", context, "wrong.invalid")]:
            rejected = False
            try:
                with socket.create_connection(("127.0.0.1", 8041), timeout=3) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname):
                        pass
            except ssl.SSLCertVerificationError:
                rejected = True
            check(label, rejected)
    else:
        _, conn = req("https://127.0.0.1:8031/connect", {})
        token, session, turn = conn["connection"], str(uuid4()), "fault-turn"
        values = {"path": "fixtures/hookgw/normal-output.txt", "content": "offline fault must not execute"}
        call = session + ":fault"
        def event(kind, **extra):
            return req("https://127.0.0.1:8031/event", {"event": kind, "connection": token, "session": session, "turn": turn, **extra})
        event("UserPromptSubmit", prompt="Write the normal public file.", cwd=str(root))
        status, decision = event("PreToolUse", call=call, route="mcp", tool="write_file", args=values)
        check("fixture_ready", status == 200 and decision["decision"] == "ALLOW")
        effect = root / values["path"]
        before = hashlib.sha256(effect.read_bytes()).hexdigest() if effect.exists() else None
        target = "with-human-hookgw-offline-control-1" if args.mode == "authz-down" else "with-human-hookgw-offline-upstream-1"
        stopped = subprocess.run(["docker", "stop", target], capture_output=True, check=False)
        check("isolated_service_stopped", stopped.returncode == 0)
        try:
            status, _ = req("https://127.0.0.1:8041/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "write_file", "arguments": values}}, token)
            check("actual_gateway_failure_denied", status != 200, http_status=status)
            after = hashlib.sha256(effect.read_bytes()).hexdigest() if effect.exists() else None
            check("no_file_mutation", before == after, before_sha256=before, after_sha256=after)
            if args.mode == "upstream-down":
                req("https://127.0.0.1:8031/transport-failure", {"connection": token, "tool": "write_file", "args": values})
                status, _ = event("PostToolUse", call=call, route="mcp", tool="write_file", args=values, output={"error": "synthetic no response"})
                check("error_post_does_not_release_unknown", status == 403)
                _, history = req("https://127.0.0.1:8031/history", credential=human)
                row = next(row for row in history["calls"] if row["id"] == call)
                check("unknown_preserved", row["state"] == "UNKNOWN")
                status, next_call = event("PreToolUse", call=session + ":no-retry", route="mcp", tool="write_file", args=values)
                check("subsequent_risk_not_retried", status == 200 and next_call["decision"] == "DENY")
        finally:
            restarted = subprocess.run(["docker", "start", target], capture_output=True, check=False)
            check("isolated_service_restored", restarted.returncode == 0)
    output = {"utc": datetime.now(UTC).isoformat(), "mode": args.mode, "paid_requests": 0, "checks": checks}
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"mode": args.mode, "passed": len(checks), "paid_requests": 0}))


if __name__ == "__main__":
    main()
