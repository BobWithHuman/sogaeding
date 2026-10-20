"""Actual native CLI with fake credentials and loopback Responses only.

This tests option parsing and per-invocation containment, not an interactive
human approval. No production launcher endpoint override is introduced.
"""

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = ROOT / "artifacts/20261016-host-review-fixture"
FAKE_KEY = "fixture-only-manual-review-api-key-not-real"
MANUAL_FLAGS = ["-c", 'approvals_reviewer="user"', "-c", 'approval_policy="on-request"']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(path, parent):
    resolved, anchor = path.resolve(), parent.resolve()
    if resolved == anchor or not resolved.is_relative_to(anchor):
        raise ValueError("Fixture path must be strictly inside its evidence directory")
    return resolved


def summary(outcome):
    # Output can contain fake auth/requests. Keep only fixed metadata and hashes.
    stderr = outcome.stderr or ""
    return {"exit": outcome.returncode, "stderr_nonempty": bool(stderr.strip()),
            "stdout_sha256": hashlib.sha256((outcome.stdout or "").encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            "reviewer_invalid_value_detected": "invalid_fixture_reviewer" in stderr,
            "managed_reviewer_warning_detected": "approvals_reviewer" in stderr and any(word in stderr.lower() for word in ("requirement", "allowed", "fall", "cannot", "not permitted")),
            "stderr_categories": [word for word in ("warning", "unknown", "unsupported", "deprecated", "experimental", "error", "requirement", "PATH", "utf", "feature", "trusted") if word in stderr]}


def run(exe):
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("manual_fixture_launcher", ROOT / "tools/hookgw_launch.py")
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    manual = launch.manual_review_overrides()
    if manual != MANUAL_FLAGS:
        raise ValueError("Manual flags contract changed")
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            route = self.path.partition("?")[0]
            seen.append({"method": "GET", "endpoint_class": "MODEL_CATALOG" if route in ("/models", "/v1/models") else "OTHER_LOOPBACK_METADATA"})
            self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("content-length", "0"))
            if not 0 <= length <= 1048576:
                self.send_error(413)
                return
            body = json.loads(self.rfile.read(length))
            seen.append({"method": "POST", "endpoint_path": self.path, "model": body.get("model"),
                         "authorization_is_fake": self.headers.get("Authorization") == "Bearer " + FAKE_KEY})
            item = {"type": "message", "id": "msg_manual_fixture", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": "Local manual reviewer fixture acknowledgement.", "annotations": []}]}
            response = {"id": "resp_manual_fixture", "status": "completed", "output": [item],
                        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            events = [{"type": "response.created", "response": {"id": response["id"], "status": "in_progress", "output": []}},
                      {"type": "response.output_item.added", "output_index": 0, "item": item},
                      {"type": "response.output_item.done", "output_index": 0, "item": item},
                      {"type": "response.completed", "response": response}]
            raw = "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n" for event in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    folder = contained(Path(tempfile.mkdtemp(prefix="run-", dir=EVIDENCE_ROOT)), EVIDENCE_ROOT)
    result = {"started_at": datetime.now(UTC).isoformat(), "cli_sha256": sha(exe),
              "paid_actor_requests": 0, "paid_judge_requests": 0, "paid_jev_requests": 0,
              "personal_auth_or_config_read": False, "real_provider_key_read": False,
              "interactive_human_approval": "NOT_RUN", "native_exec_on_request_effective": "NOT_PROVEN",
              "product_tool_calls": 0, "manual_flags_exact": True,
              "manual_flags_modify_sandbox": False,
              "official_reference": "https://learn.chatgpt.com/docs/config-file/config-reference"}
    try:
        home, workspace, programdata = folder / "codex-home", folder / "workspace", folder / "programdata"
        for path in (home, workspace, programdata, folder / "appdata", folder / "localappdata"):
            path.mkdir()
        config, auth = home / "config.toml", home / "auth.json"
        config.write_text('model="personal-other-fixture-model"\napprovals_reviewer="auto_review"\napproval_policy="on-request"\nsandbox_mode="read-only"\ncli_auth_credentials_store="file"\nproject_doc_max_bytes=0\nweb_search="disabled"\n[features]\nplugins=false\napps=false\nbrowser_use=false\ncomputer_use=false\nskip_host_skill_discovery=true\n[history]\npersistence="none"\n', encoding="utf-8")
        def segment(value):
            return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
        jwt = segment({"alg": "none"}) + "." + segment({"email": "fixture@example.invalid", "https://api.openai.com/auth": {"chatgpt_account_id": "fixture-account", "chatgpt_plan_type": "plus"}}) + ".fixture"
        auth.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"id_token": jwt, "access_token": "fixture-chatgpt", "refresh_token": "fixture-refresh", "account_id": "fixture-account"}}), encoding="utf-8")
        before = {path.name: sha(path) for path in (config, auth)}
        env = {key: os.environ[key] for key in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive") if key in os.environ}
        env.update(CODEX_HOME=str(home), USERPROFILE=str(folder), APPDATA=str(folder / "appdata"),
                   LOCALAPPDATA=str(folder / "localappdata"), ProgramData=str(programdata),
                   TEMP=str(folder), TMP=str(folder), OPENAI_API_KEY=FAKE_KEY)
        flags = [value.replace(launch.API_BASE, f"http://127.0.0.1:{server.server_port}/v1") for value in launch.api_overrides("gpt-5.6-luna")]
        def native(extra, *, prompt=None):
            return subprocess.run([str(exe), *flags, *extra], input=prompt, cwd=workspace, env=env,
                                  text=True, encoding="utf-8", errors="replace", capture_output=True,
                                  timeout=45, check=False)
        initial = native(["features", "list"])
        manual_features = native([*manual, "features", "list"])
        invalid = native(["-c", 'approvals_reviewer="invalid_fixture_reviewer"', "features", "list"])
        actor = native([*manual, "exec", "--skip-git-repo-check", "--json", "-"],
                       prompt="Reply with the local fixture acknowledgement. Use no tools.")
        requirements = programdata / "OpenAI/Codex/requirements.toml"
        requirements.parent.mkdir(parents=True)
        requirements.write_text('allowed_approvals_reviewers=["auto_review"]\nallowed_approval_policies=["on-request"]\n', encoding="utf-8")
        required_before = sha(requirements)
        constrained = native([*manual, "features", "list"])
        # Remove only the synthetic file we just wrote, within the verified fixture.
        contained(requirements, folder).unlink()
        after = native(["features", "list"])
        unchanged = all(before[path.name] == sha(path) for path in (config, auth))
        managed_detected = constrained.returncode != 0 or summary(constrained)["managed_reviewer_warning_detected"]
        result.update(default_features=summary(initial), manual_features=summary(manual_features),
                      invalid_reviewer=summary(invalid), managed_constraint=summary(constrained),
                      native_exec=summary(actor), final_default_features=summary(after), local_requests=seen,
                      generated_auth_and_config_unchanged=unchanged,
                      default_config_auto_review_preserved='approvals_reviewer="auto_review"' in config.read_text(),
                      default_config_on_request_preserved='approval_policy="on-request"' in config.read_text(),
                      default_config_sandbox_read_only_preserved='sandbox_mode="read-only"' in config.read_text(),
                      managed_requirements_sha256=required_before,
                      managed_forbids_user_detected=managed_detected,
                      managed_requirement_enforcement="DETECTED" if managed_detected else "NOT_VERIFIED_ISOLATED_PROGRAMDATA_NOT_LOADED",
                      managed_zero_exit_warning_requires_preflight_rejection=constrained.returncode == 0 and bool(constrained.stderr.strip()))
        result["pass_scope"] = "NATIVE_OPTIONS_FAKE_ACTOR_AND_GENERATED_FILE_PRESERVATION_ONLY"
        result["pass"] = (initial.returncode == 0 and manual_features.returncode == 0 and invalid.returncode != 0
                          and actor.returncode == 0 and after.returncode == 0 and unchanged
                          and [item for item in seen if item["method"] == "POST"] == [{"method": "POST", "endpoint_path": "/v1/responses", "model": "gpt-5.6-luna", "authorization_is_fake": True}])
    except (OSError, ValueError, subprocess.SubprocessError):
        result.update(pass_=False, diagnostic="ISOLATED_NATIVE_FIXTURE_UNAVAILABLE")
        result["pass"] = False
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
        # Single-shell equivalent: resolved absolute containment is checked immediately before recursive cleanup.
        cleanup = contained(folder, EVIDENCE_ROOT)
        shutil.rmtree(cleanup)
        result["isolated_fixture_cleaned"] = not cleanup.exists()
    result["finished_at"] = datetime.now(UTC).isoformat()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    target = contained(options.output, EVIDENCE_ROOT)
    record = run(options.exe.resolve())
    with target.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    print(json.dumps(record))
    raise SystemExit(0 if record["pass"] else 1)
