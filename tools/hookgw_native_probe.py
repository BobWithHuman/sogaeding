"""Actual installed Windows Codex hooks driven by a local scripted Responses fixture.

No OpenAI/API credentials or model inference; isolated workspace and CODEX_HOME.
"""
import argparse
import hashlib
import json
import os
import subprocess
import struct
import sys
import threading
import time
import zlib
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def callback(directory, mode):
    value = json.loads(sys.stdin.buffer.read(262145))
    with (directory / "events.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(value, ensure_ascii=False) + "\n")
    if value["hook_event_name"] == "PreToolUse":
        if mode == "crash":
            return 1
        if mode == "timeout":
            time.sleep(8)
        if mode == "malformed":
            print("{not valid json")
            return 0
        if mode == "pdp-unavailable":
            try:
                urllib.request.urlopen("http://127.0.0.1:1/offline-no-pdp", timeout=0.2)
            except Exception:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "permissionDecision": "deny", "permissionDecisionReason": "OFFLINE_PDP_UNAVAILABLE"}}))
                return 0
            return 2
        if mode == "deny":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny", "permissionDecisionReason": "OFFLINE_PROBE_DENY"}}))
            return 0
    print("{}")
    return 0


def run(directory, mode, kind, vetted_fixture_hooks=False, followup=False):
    directory.mkdir(parents=True, exist_ok=False)
    workspace = directory / "workspace"
    home = directory / "home"
    workspace.mkdir()
    home.mkdir()
    (directory / "os-temp").mkdir()
    script = Path(__file__).resolve()
    requests = []
    marker = workspace / "effect.txt"
    command = "Set-Content -LiteralPath '" + marker.as_posix() + "' -Value 'native effect'; Get-Content -LiteralPath '" + marker.as_posix() + "'"
    args = {"cmd": command, "yield_time_ms": 1000, "max_output_tokens": 1000}
    tool = "exec_command"
    if kind == "image":
        image = workspace / "public-fixture.png"
        def png_chunk(name, data):
            return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
                          + png_chunk(b"IDAT", zlib.compress((b"\x00" + b"\xff\xff\xff" * 2) * 2)) + png_chunk(b"IEND", b""))
        tool, args = "view_image", {"path": str(image)}
    elif kind == "patch":
        tool = "apply_patch"
        args = "*** Begin Patch\n*** Add File: effect.txt\n+normal file edit\n*** End Patch"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            tools = body.get("tools", [])
            requests.append({"path": self.path, "tools": tools})
            index = len(requests)
            if index % 2 == 1:
                item = {"type": "function_call", "id": "fc_probe_" + str(index), "call_id": "call_probe_" + str(index),
                        "name": tool, "arguments": json.dumps(args) if isinstance(args, dict) else args}
                if kind == "patch":
                    item = {"type": "custom_tool_call", "id": "ctc_probe_" + str(index), "call_id": "call_probe_" + str(index),
                            "name": tool, "input": args}
            else:
                item = {"type": "message", "id": "msg_probe", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": "Offline probe finished.", "annotations": []}]}
            events = [
                {"type": "response.created", "response": {"id": "resp_" + str(index), "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": item},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": {"id": "resp_" + str(index), "status": "completed", "output": [item],
                 "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
            ]
            data = "".join("event: " + row["type"] + "\ndata: " + json.dumps(row) + "\n\n" for row in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    config = f'''model = "gpt-5.6-luna"
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
[projects.{json.dumps(str(workspace))}]
trust_level = "trusted"
'''
    hook_command = f'"{sys.executable}" "{script}" callback "{directory}" {mode}'
    windows_command = "& " + hook_command
    for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
        config += f'\n[[hooks.{event}]]\n[[hooks.{event}.hooks]]\ntype = "command"\ncommand = {json.dumps(hook_command)}\ncommand_windows = {json.dumps(windows_command)}\ntimeout = 5\n'
    (home / "config.toml").write_text(config, encoding="utf-8")
    env = {key: os.environ[key] for key in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive") if key in os.environ}
    env.update({"CODEX_HOME": str(home), "USERPROFILE": str(directory), "APPDATA": str(directory / "appdata"),
                "LOCALAPPDATA": str(directory / "localappdata"), "TEMP": str(directory / "os-temp"), "TMP": str(directory / "os-temp")})
    exe = "C:/Users/qkaeh/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe"
    started = time.time()
    try:
        cli_args = [exe, "exec", "--strict-config", "--skip-git-repo-check", "--sandbox", "workspace-write", "--json", "-C", str(workspace), "-"]
        if vetted_fixture_hooks:
            # Test-only: exact locally authored fixture definitions were reviewed.
            # Never emitted into the product profile or used with a paid provider.
            cli_args.insert(2, "--dangerously-bypass-hook-trust")
        timed_out = False
        try:
            result = subprocess.run(cli_args,
                                    input="정상 파일을 편집하고 공개 자료를 읽어줘.", text=True, encoding="utf-8",
                                    capture_output=True, cwd=workspace, env=env, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
            result = subprocess.CompletedProcess(cli_args, 124, decoded(exc.stdout), decoded(exc.stderr))
        second_result = None
        if followup and result.returncode == 0:
            second_args = cli_args[:-1] + ["resume", "--last", "-"]
            second_result = subprocess.run(second_args, input="이제 공개 이미지를 다시 확인해줘.", text=True,
                                           encoding="utf-8", capture_output=True, cwd=workspace, env=env, timeout=45, check=False)
            (directory / "followup-cli.txt").write_text(second_result.stdout + "\n" + second_result.stderr, encoding="utf-8")
        # Inputs and outputs here contain only this local synthetic fixture.
        (directory / "cli.txt").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        (directory / "request-tools.json").write_text(json.dumps(requests, indent=2), encoding="utf-8")
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()] if (directory / "events.jsonl").exists() else []
        summary = {"mode": mode, "kind": kind, "cli_exit": result.returncode, "timed_out": timed_out, "requests_to_local_fixture": len(requests),
                   "paid_requests": 0, "vetted_fixture_hooks": vetted_fixture_hooks,
                   "effects": int(marker.exists()), "events": [row["hook_event_name"] for row in events],
                   "elapsed_ms": round((time.time() - started) * 1000),
                   "cli_sha256": hashlib.sha256(Path(exe).read_bytes()).hexdigest()}
        summary["started_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))
        summary["finished_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        summary["command"] = cli_args
        summary["source_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
        summary["followup_exit"] = second_result.returncode if second_result else None
        (directory / "probe-source.py").write_bytes(script.read_bytes())
        (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary))
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "callback"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("mode", choices=("allow", "deny", "crash", "timeout", "malformed", "pdp-unavailable"))
    parser.add_argument("--kind", choices=("shell", "patch", "image"), default="shell")
    parser.add_argument("--vetted-fixture-hooks", action="store_true")
    parser.add_argument("--followup", action="store_true")
    value = parser.parse_args()
    if value.action == "callback":
        sys.exit(callback(value.directory, value.mode))
    run(value.directory.resolve(), value.mode, value.kind, value.vetted_fixture_hooks, value.followup)
