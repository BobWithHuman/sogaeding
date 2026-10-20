"""Actual installed Codex, fake credentials and loopback Responses ONLY.

This is an auth-path test, not the interactive product launcher or a model eval.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE_KEY = "fixture-only-openai-api-key-not-real"


def run(exe, legacy_profile=False):
    spec = importlib.util.spec_from_file_location("launcher", ROOT / "tools/hookgw_launch.py")
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            seen.append({"endpoint_path": self.path, "model": body.get("model"),
                         "authorization_is_fake_env_key": self.headers.get("Authorization") == "Bearer " + FAKE_KEY,
                         "authorization_is_personal_fixture": "fixture-chatgpt" in self.headers.get("Authorization", "")})
            item = {"type": "message", "id": "msg_auth_fixture", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": "Local authentication fixture complete.", "annotations": []}]}
            response = {"id": "resp_auth_fixture", "status": "completed", "output": [item],
                        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            events = [{"type": "response.created", "response": {"id": response["id"], "status": "in_progress", "output": []}},
                      {"type": "response.output_item.added", "output_index": 0, "item": item},
                      {"type": "response.output_item.done", "output_index": 0, "item": item},
                      {"type": "response.completed", "response": response}]
            raw = "".join("event: " + x["type"] + "\ndata: " + json.dumps(x) + "\n\n" for x in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.send_error(404)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    result = {"started_at": datetime.now(UTC).isoformat(), "paid_actor_requests": 0, "paid_judge_requests": 0}
    try:
        with tempfile.TemporaryDirectory(prefix="hookgw-api-fixture-") as folder:
            root = Path(folder)
            home = root / "codex-home"
            home.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            config = home / "config.toml"
            text = 'model="personal-other-model"\ncli_auth_credentials_store="file"\nproject_doc_max_bytes=0\nweb_search="disabled"\n[features]\nplugins=false\napps=false\nbrowser_use=false\ncomputer_use=false\nskip_host_skill_discovery=true\n[history]\npersistence="none"\n'
            if legacy_profile:
                text = 'profile="personal"\n' + text + '[profiles.personal]\nmodel="profile-other-model"\nmodel_provider="openai"\n'
            config.write_text(text, encoding="utf-8")
            def segment(value):
                return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
            jwt = segment({"alg": "none"}) + "." + segment({"email": "fixture@example.invalid", "https://api.openai.com/auth": {"chatgpt_account_id": "fixture-account", "chatgpt_plan_type": "plus"}}) + ".fixture"
            auth = home / "auth.json"
            auth.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"id_token": jwt, "access_token": "fixture-chatgpt-do-not-use", "refresh_token": "fixture-refresh", "account_id": "fixture-account"}}), encoding="utf-8")
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (auth, config)}
            env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive") if k in os.environ}
            env.update(CODEX_HOME=str(home), USERPROFILE=str(root), APPDATA=str(root / "appdata"), LOCALAPPDATA=str(root / "localappdata"),
                       TEMP=str(root), TMP=str(root), OPENAI_API_KEY=FAKE_KEY)
            flags = launch.api_overrides("gpt-5.6-luna")
            # Test-only substitution; production provides NO endpoint override.
            flags = [value.replace(launch.API_BASE, f"http://127.0.0.1:{server.server_port}/v1") for value in flags]
            command = [str(exe), *flags, "exec", "--skip-git-repo-check", "--json", "-"]
            outcome = subprocess.run(command, input="Reply with the local fixture acknowledgement. Use no tools.", cwd=workspace, env=env,
                                     text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=45, check=False)
            result.update(cli_exit=outcome.returncode, local_requests=seen,
                          isolated_auth_unchanged=before[auth.name] == hashlib.sha256(auth.read_bytes()).hexdigest(),
                          isolated_config_unchanged=before[config.name] == hashlib.sha256(config.read_bytes()).hexdigest(),
                          cli_sha256=hashlib.sha256(Path(exe).read_bytes()).hexdigest())
            result["pass"] = (outcome.returncode == 0 and len(seen) == 1 and seen[0] == {"endpoint_path": "/v1/responses", "model": "gpt-5.6-luna", "authorization_is_fake_env_key": True, "authorization_is_personal_fixture": False}
                              and result["isolated_auth_unchanged"] and result["isolated_config_unchanged"])
            if legacy_profile:
                result["expected"] = "CLI_REJECTS_UNSUPPORTED_LEGACY_PROFILE_BEFORE_REQUEST"
                result["pass"] = (outcome.returncode != 0 and not seen and 'legacy `profile' in outcome.stderr
                                  and result["isolated_auth_unchanged"] and result["isolated_config_unchanged"])
            # Only error category, never actual request/env/raw auth output.
            if not result["pass"]:
                result["diagnostic"] = "LOCAL_FIXTURE_FAILED"
                result["isolated_cli_error"] = outcome.stderr[-2000:].replace(FAKE_KEY, "[FAKE_KEY]").replace(jwt, "[FAKE_JWT]").replace("fixture-chatgpt-do-not-use", "[FAKE_CHATGPT]")
    finally:
        server.shutdown()
    result["finished_at"] = datetime.now(UTC).isoformat()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--legacy-profile", action="store_true")
    opts = parser.parse_args()
    record = run(opts.exe, opts.legacy_profile)
    with opts.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    print(json.dumps(record))
    raise SystemExit(0 if record["pass"] else 1)
