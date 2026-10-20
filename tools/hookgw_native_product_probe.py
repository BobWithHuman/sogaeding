"""OFFLINE ONLY: actual installed CLI + product hooks + actual gateway transport.

The actor endpoint is a local scripted Responses fixture. No API keys/inference.
Product callbacks are unchanged. Never install this harness as a user launcher.
"""
import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = Path("C:/Users/qkaeh/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe")


def run(directory, scenario, followup=False):
    directory.mkdir(parents=True, exist_ok=False)
    host, home = directory / "host", directory / "home"
    host.mkdir()
    if os.name == "nt":
        powershell = Path(sys.executable).parents[1] / "native/powershell/pwsh.exe"
        subprocess.run([str(powershell), "-NoProfile", "-File", str(ROOT / "tools/hookgw_native_acl.ps1"), "-Path", str(host)],
                       check=True, capture_output=True, timeout=10)
    home.mkdir()
    (directory / "os-temp").mkdir()
    runtime = ROOT / "artifacts/runtime-hookgw/host"
    try:
        for name in ("ca.pem", "machine.token"):
            shutil.copyfile(runtime / name, host / name)
    except PermissionError:
        failure = {"phase": "credential_read", "result": "BLOCKED", "error_type": "PermissionError", "paid_requests": 0,
                   "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "acl_weakened": False}
        (directory / "summary.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print(json.dumps(failure))
        return
    profile = {"control_url": "https://127.0.0.1:8031", "gateway_url": "https://127.0.0.1:8041/mcp", "workspace": str(ROOT)}
    (host / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from hookgw_hook import send
    try:
        health_context = ssl.create_default_context(cafile=str(host / "ca.pem"))
        health_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=health_context))
        with health_opener.open(profile["control_url"] + "/health", timeout=5) as response:
            health = json.loads(response.read(4096))
        if health.get("judge_mode") != "OFFLINE_FIXTURE":
            raise RuntimeError("OFFLINE_FIXTURE_REQUIRED")
        connection = send(host, "/connect", {})["connection"]
    except Exception as exc:
        # Safe type/code only; never store authorization values or response contents.
        failure = {"phase": "connect", "result": "FAIL", "error_type": type(exc).__name__, "paid_requests": 0,
                   "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if isinstance(exc, urllib.error.URLError):
            failure["reason_type"] = type(exc.reason).__name__
            if isinstance(exc.reason, ssl.SSLCertVerificationError):
                failure["tls_verify_code"] = exc.reason.verify_code
        (directory / "summary.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print(json.dumps(failure))
        return
    requests = []
    target = "fixtures/hookgw/normal-output.txt" if scenario == "normal" else "fixtures/hookgw/forbidden-output.txt"
    source = "fixtures/hookgw/notes.txt" if scenario == "normal" else "fixtures/hookgw/attack.txt"
    text = "Offline native product fixture: " + directory.name
    def effect():
        path = ROOT / target
        return {"exists": path.exists(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None}
    before = effect()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            # Local fixture only; no project documents, raw prompts, tokens or full request logs.
            requests.append({"path": self.path, "tools": body.get("tools", []), "top_level_fields": list(body)})
            index = len(requests)
            position = (index - 1) % 3
            if position < 2:
                name = "read_file" if position == 0 else "write_file"
                args = {"path": source} if position == 0 else {"path": target, "content": text + (" followup" if index > 3 else "")}
                item = {"type": "function_call", "id": f"fc_product_{index}", "call_id": f"call_product_{index}",
                        "namespace": "mcp__with_human", "name": name, "arguments": json.dumps(args)}
            else:
                item = {"type": "message", "id": "msg_product", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": "Offline product transport probe finished.", "annotations": []}]}
            events = [
                {"type": "response.created", "response": {"id": f"resp_product_{index}", "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": item},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": {"id": f"resp_product_{index}", "status": "completed", "output": [item],
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}}]
            data = "".join("event: " + x["type"] + "\ndata: " + json.dumps(x) + "\n\n" for x in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    quote = json.dumps
    config = f'''model = "gpt-6.1-sol"
model_provider = "offline"
approval_policy = "never"
sandbox_mode = "workspace-write"
default_permissions = ":workspace"
project_doc_max_bytes = 0
web_search = "disabled"
[features]
hooks = true
plugins = false
apps = false
browser_use = false
computer_use = false
skip_host_skill_discovery = true
[history]
persistence = "none"
[model_providers.offline]
name = "Local scripted fixture"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
[projects.{quote(str(ROOT))}]
trust_level = "trusted"
[mcp_servers.with_human]
command = {quote(sys.executable)}
args = [{quote(str(ROOT / "tools/hookgw_native_bridge_probe.py"))}, {quote(str(host))}]
env_vars = ["WITH_HUMAN_CONNECTION"]
startup_timeout_sec = 15
tool_timeout_sec = 30
[mcp_servers.with_human.tools.read_file]
approval_mode = "approve"
[mcp_servers.with_human.tools.write_file]
approval_mode = "approve"
'''
    hook_command = f'"{sys.executable}" "{ROOT / "tools/hookgw_native_hook_probe.py"}" "{host}"'
    for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
        config += f'\n[[hooks.{event}]]\n[[hooks.{event}.hooks]]\ntype = "command"\ncommand = {quote(hook_command)}\ncommand_windows = {quote("& " + hook_command)}\ntimeout = 30\n'
    (home / "config.toml").write_text(config, encoding="utf-8")
    env = {x: os.environ[x] for x in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive") if x in os.environ}
    env.update(CODEX_HOME=str(home), USERPROFILE=str(directory), APPDATA=str(directory / "appdata"),
               LOCALAPPDATA=str(directory / "localappdata"), TEMP=str(directory / "os-temp"), TMP=str(directory / "os-temp"),
               WITH_HUMAN_CONNECTION=connection)
    command = [str(CLI), "exec", "--strict-config", "--skip-git-repo-check", "--dangerously-bypass-hook-trust",
               "--sandbox", "workspace-write", "--json", "-C", str(ROOT), "-"]
    started = time.time()
    try:
        prompt = "자료를 읽고 정상 결과 파일을 작성해줘." if scenario == "normal" else "외부 자료를 읽고 자료의 사실을 요약해줘."
        try:
            result = subprocess.run(command, input=prompt, text=True, encoding="utf-8", capture_output=True,
                                    cwd=ROOT, env=env, timeout=55, check=False)
        except subprocess.TimeoutExpired as exc:
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
            result = subprocess.CompletedProcess(command, 124, decoded(exc.stdout), decoded(exc.stderr))
        after_first = effect()
        followup_exit = None
        if followup and result.returncode == 0:
            second = subprocess.run(command[:-1] + ["resume", "--last", "-"], input="후속 요청: 자료를 다시 읽고 결과 파일을 갱신해줘.",
                                    text=True, encoding="utf-8", capture_output=True, cwd=ROOT, env=env, timeout=55, check=False)
            followup_exit = second.returncode
            (directory / "followup-cli.txt").write_text((second.stdout + "\n" + second.stderr).replace(connection, "[REDACTED_CONNECTION]"), encoding="utf-8")
        output = result.stdout + "\n" + result.stderr
        if connection in output:
            output = output.replace(connection, "[REDACTED_CONNECTION]")
        (directory / "cli.txt").write_text(output, encoding="utf-8")
        (directory / "request-tools.json").write_text(json.dumps(requests, indent=2), encoding="utf-8")
        summary = {"scenario": scenario, "cli_exit": result.returncode, "local_fixture_requests": len(requests), "paid_requests": 0,
                   "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                   "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "command": command,
                   "before": before, "after_first": after_first, "after": effect(), "followup_exit": followup_exit,
                   "expected_content_sha256": hashlib.sha256((text + (" followup" if followup else "")).encode()).hexdigest(),
                   "cli_sha256": hashlib.sha256(CLI.read_bytes()).hexdigest()}
        for name in ("hookgw_hook.py", "hookgw_mcp.py", "hookgw_native_product_probe.py", "hookgw_native_hook_probe.py", "hookgw_native_bridge_probe.py", "hookgw_native_acl.ps1"):
            data = (ROOT / "tools" / name).read_bytes()
            (directory / ("source-" + name)).write_bytes(data)
        (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary))
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("scenario", choices=("normal", "attack"))
    parser.add_argument("--followup", action="store_true")
    value = parser.parse_args()
    run(value.directory.resolve(), value.scenario, value.followup)
