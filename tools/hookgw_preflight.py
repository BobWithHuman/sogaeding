"""Model-free readiness; temporary unbound MCP metadata connection only.

Never creates a user turn/candidate, calls a tool or submits inference. The
startup probe removes its temporary connection and reports cleanup failures.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# Executed as the SAME container UID as the judge. No API client/claim/init/write.
CONTROL_PROBE = '''import hashlib,json,os,sqlite3
from pathlib import Path
from app.transparent.judge import DevelopmentJudge
from app.common import RUNTIME,mask
out={"live_env":os.getenv("HOOKGW_USER_LIVE")=="1","key_readable_nonempty":False,"budget_readable":False,"model":DevelopmentJudge.model}
out["runtime_directory_preserved"]=str(RUNTIME)=="/runtime"
try:
 human=Path("/runtime/human.token").read_text(encoding="ascii").strip()
 out["existing_literal_masking"]=bool(human) and mask(chr(0xAC00)+human+chr(0xB098))==chr(0xAC00)+"[REDACTED]"+chr(0xB098)
except OSError: out["existing_literal_masking"]=False
try:
 out["key_readable_nonempty"]=bool(Path(os.getenv("RUNTIME_DIR","/runtime"),"judge.api-key").read_bytes().strip())
except OSError: pass
path=Path("/legacy-budget/judge-budget.sqlite3")
if os.getenv("JUDGE_BUDGET_DB_PATH")==str(path) and path.is_file():
 try:
  before=hashlib.sha256(path.read_bytes()).hexdigest()
  db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
  count=db.execute("SELECT count(*) FROM attempts").fetchone()[0]
  db.close()
  out.update(budget_readable=True,requests_attempted=count,limit=24,remaining=max(0,24-count),budget_sha256=before,budget_unchanged=before==hashlib.sha256(path.read_bytes()).hexdigest())
 except (OSError,sqlite3.Error): pass
print(json.dumps(out))'''

JEV_CONTROL_PROBE = '''import json,os
from pathlib import Path
from app.common import RUNTIME,mask
from app.transparent.jev_config import load_settings
settings=load_settings(Path(os.getenv("JEV_POLICY_FILE","/jev-config/policy.json")))
out={"pdp_mode":os.getenv("HOOKGW_PDP"),"model":settings.model,"settings_enabled":settings.enabled,"live_authorization":"AUTHORIZED" if settings.authorized() else "NOT_AUTHORIZED","runtime_directory_preserved":str(RUNTIME)=="/runtime","existing_literal_masking":False,"provider_key_present":Path("/jev-key/jev.api-key").is_file(),"provider_ledger_present":Path("/jev-budget/typesafe-budget.sqlite3").is_file()}
try:
 human=Path("/runtime/human.token").read_text(encoding="ascii").strip()
 out["existing_literal_masking"]=bool(human) and mask(chr(0xAC00)+human+chr(0xB098))==chr(0xAC00)+"[REDACTED]"+chr(0xB098)
except OSError: pass
print(json.dumps(out))'''


def command(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)


def login_kind():
    # Read just the mode discriminator; do not print/cache credentials or mutate auth.
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    try:
        auth = json.loads((home / "auth.json").read_text(encoding="utf-8"))
        mode = auth.get("auth_mode")
        if isinstance(mode, str) and mode.lower() in ("chatgpt", "api", "apikey"):
            return mode.upper()
        if auth.get("tokens"):
            return "CHATGPT"
        if auth.get("OPENAI_API_KEY"):
            return "API_KEY"
    except (OSError, ValueError):
        pass
    return "NOT_INSPECTABLE_OR_NO_FILE_AUTH"


def tls_health(host, jev=False):
    profile = json.loads((host / "profile.json").read_text(encoding="utf-8-sig"))
    # Production preflight cannot be redirected to arbitrary credential/diagnostic endpoints.
    control_port, gateway_port = (8032, 8042) if jev else (8030, 8040)
    if profile.get("control_url") != f"https://127.0.0.1:{control_port}" or profile.get("gateway_url") != f"https://127.0.0.1:{gateway_port}/mcp":
        raise ValueError("UNEXPECTED_ENDPOINT")
    context = ssl.create_default_context(cafile=str(host / "ca.pem"))
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
    with opener.open(profile["control_url"] + "/health", timeout=5) as response:
        health = json.loads(response.read(4096))
    with socket.create_connection(("127.0.0.1", gateway_port), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname="127.0.0.1"):
            pass
    return {"spec": health.get("spec"), "judge_mode": health.get("judge_mode"), "gateway_tls": True}


def control_probe(root, jev=False):
    docker = shutil.which("docker")
    if not docker or Path(docker).resolve().is_relative_to(root.resolve()):
        raise ValueError("TRUSTED_DOCKER_EXECUTABLE_REQUIRED")
    result = command([str(Path(docker).resolve()), "compose", "-f", str(root / "compose.hookgw.yaml"), "-f", str(root / ("compose.hookgw.jev.yaml" if jev else "compose.hookgw.live.yaml")),
                      "exec", "-T", "control", "python", "-c", JEV_CONTROL_PROBE if jev else CONTROL_PROBE])
    if result.returncode:
        raise ValueError("CONTROL_EXEC_UNAVAILABLE")
    value = json.loads(result.stdout)
    allowed = ({"pdp_mode", "model", "settings_enabled", "live_authorization", "runtime_directory_preserved", "existing_literal_masking", "provider_key_present", "provider_ledger_present"}
               if jev else {"live_env", "key_readable_nonempty", "budget_readable", "model", "requests_attempted", "limit", "remaining", "budget_sha256", "budget_unchanged", "runtime_directory_preserved", "existing_literal_masking"})
    if not isinstance(value, dict) or set(value) - allowed or not isinstance(value.get("model"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}", value["model"]):
        raise ValueError("INVALID_CONTROL_DIAGNOSTIC")
    if jev and (set(value) != allowed or any(type(value[name]) is not bool for name in
                ("settings_enabled", "runtime_directory_preserved", "existing_literal_masking", "provider_key_present", "provider_ledger_present"))):
        raise ValueError("INVALID_CONTROL_DIAGNOSTIC")
    return value


def mcp_startup(root, host):
    spec = importlib.util.spec_from_file_location("with_human_mcp_probe", Path(__file__).with_name("hookgw_mcp_probe.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.probe(root, host)


def run(root, host, exe, flags, model, jev=False, manual_review=False):
    report = {"utc": datetime.now(UTC).isoformat(), "mode": "NO_MODEL_PREFLIGHT", "ready_to_open_cli": False,
              "model_access": "NOT_VERIFIED_NO_REQUEST", "paid_requests": 0,
              "actor": {"provider": "with_human_openai_api", "model": model, "authentication": "ENV_API_KEY",
                        "env_key": "OPENAI_API_KEY", "key_present": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
                        "endpoint": "https://api.openai.com/v1/responses", "personal_stored_auth": login_kind()},
              "hook_trust": "NOT_VERIFIED_REVIEW_EXACT_DEFINITIONS_IN_/hooks_BEFORE_FIRST_PROMPT",
              "issues": []}
    report["host_review"] = {
        "requested_reviewer": "user" if manual_review else "INHERITED_NOT_VERIFIED",
        "requested_approval_policy": "on-request" if manual_review else "INHERITED_NOT_VERIFIED",
        "scope": "THIS_CLI_INVOCATION" if manual_review else "UNCHANGED",
        "sandbox": "INHERITED_UNCHANGED", "managed_requirements": "CLI_ENFORCED",
        "auto_review_model_access": "NOT_REQUIRED_FOR_USER_REVIEWER" if manual_review else "NOT_VERIFIED_NO_REQUEST",
        "human_tool_approval": "NOT_RUN_USER_NEXT", "configuration": "NOT_CHECKED",
    }
    if jev:
        report.update(pdp_mode="JEV_RULES_ONLY", semantic_write_ready=False,
                      jev_live="NOT_AUTHORIZED", jev_model_access="NOT_VERIFIED_NO_REQUEST")
    issues = report["issues"]
    expected_manual_flags = ["-c", 'approvals_reviewer="user"', "-c", 'approval_policy="on-request"']
    if manual_review and (not jev or flags[-4:] != expected_manual_flags):
        issues.append("HOST_MANUAL_REVIEW_FLAGS_INVALID")
    if not report["actor"]["key_present"]:
        issues.append("ACTOR_API_KEY_MISSING")
    try:
        report["host_credentials_readable"] = all(bool((host / name).read_bytes().strip()) for name in ("machine.token", "human.token"))
        if not report["host_credentials_readable"]:
            issues.append("HOST_CONNECTION_CREDENTIAL_UNAVAILABLE")
    except OSError:
        issues.append("HOST_CONNECTION_CREDENTIAL_UNAVAILABLE")
    try:
        version = command([exe, "--version"])
        text = version.stdout.strip()
        report["cli_version"] = text if re.fullmatch(r"codex-cli [0-9A-Za-z.+-]+", text) else "UNRECOGNIZED"
        config = command([exe, *flags, "features", "list"])
        report["cli_configuration_parsed"] = config.returncode == 0
        report["host_review"]["configuration"] = "ACCEPTED_BY_CLI_NOT_HUMAN_APPROVAL" if config.returncode == 0 else "REJECTED_BY_CLI"
        if manual_review and config.returncode:
            issues.append("HOST_MANUAL_REVIEW_CONFIGURATION_REJECTED")
        if manual_review and config.stderr.strip():
            # Managed constraints may fall back with exit0 + warning. Never
            # mistake that for the user's explicitly requested reviewer route.
            # Do not print raw stderr, config values or managed policy content.
            report["host_review"]["configuration"] = "UNVERIFIED_CLI_WARNING"
            issues.append("HOST_MANUAL_REVIEW_CLI_WARNING")
        report["hooks_enabled"] = any(len(line.split()) == 3 and line.split()[0] == "hooks" and line.split()[2] == "true" for line in config.stdout.splitlines())
        report["cli_sha256"] = hashlib.sha256(Path(exe).read_bytes()).hexdigest()
        if version.returncode or report["cli_version"] == "UNRECOGNIZED" or not report["cli_configuration_parsed"] or not report["hooks_enabled"]:
            issues.append("CLI_HOOK_CONFIGURATION_FAILED")
    except (OSError, subprocess.SubprocessError):
        issues.append("CLI_UNAVAILABLE")
    try:
        bundle = command([sys.executable, "-I", str(root / "tools/hookgw_bundle.py"), str(root), "--verify", "--current"])
        report["frozen_bundle_verified"] = bundle.returncode == 0
        if bundle.returncode:
            issues.append("FROZEN_BUNDLE_UNVERIFIED")
    except (OSError, subprocess.SubprocessError):
        issues.append("FROZEN_BUNDLE_UNVERIFIED")
    try:
        report["tls"] = tls_health(host, jev=True) if jev else tls_health(host)
        expected_mode = "JEV_RULES_ONLY" if jev else "LIVE_USER"
        if report["tls"]["spec"] != "MVP-SPEC-5" or report["tls"]["judge_mode"] != expected_mode:
            issues.append("CONTROL_NOT_JEV_RULES_ONLY" if jev else "CONTROL_NOT_LIVE_USER")
    except (OSError, ValueError):
        issues.append("APP_CA_OR_TLS_HEALTH_FAILED")
    try:
        report["mcp_startup"] = mcp_startup(root, host)
        if not report["mcp_startup"].get("ready"):
            issues.append("WITH_HUMAN_MCP_STARTUP_FAILED")
    except (OSError, ValueError, subprocess.SubprocessError):
        report["mcp_startup"] = {"server": "with_human", "ready": False, "stage": "PROBE", "code": "PROBE_UNAVAILABLE",
                                 "other_personal_mcp_servers": "NOT_INSPECTED", "original_startup_issue_server": "UNDETERMINED"}
        issues.append("WITH_HUMAN_MCP_STARTUP_FAILED")
    try:
        if jev:
            report["control_jev"] = control_probe(root, jev=True)
            provider = report["control_jev"]
            if provider.get("pdp_mode") != "JEV":
                issues.append("CONTROL_NOT_JEV_RULES_ONLY")
            if provider.get("model") != "jev-1.13.0":
                issues.append("JEV_MODEL_NOT_PINNED")
            if not provider.get("runtime_directory_preserved") or not provider.get("existing_literal_masking"):
                issues.append("EXISTING_SECRET_MASKING_UNVERIFIED")
            if provider.get("settings_enabled") is not False or provider.get("live_authorization") != "NOT_AUTHORIZED":
                issues.append("JEV_LIVE_CONFIGURATION_REQUIRES_SEPARATE_REVIEW")
            if provider.get("provider_key_present") is not False or provider.get("provider_ledger_present") is not False:
                issues.append("JEV_RULES_EXPECTS_NO_PROVIDER_KEY_OR_LEDGER")
            provider.update(authentication="NOT_CONFIGURED_RULES_ONLY", endpoint="https://api.typesafe.ai/v1/systemone",
                            model_access="NOT_VERIFIED_NO_REQUEST")
            report["ready_to_open_cli"] = not issues
            return report
        report["control_judge"] = control_probe(root)
        judge = report["control_judge"]
        if not judge.get("live_env"):
            issues.append("CONTROL_LIVE_ENV_MISSING")
        if not judge.get("key_readable_nonempty"):
            issues.append("CONTROL_JUDGE_KEY_UNREADABLE_OR_EMPTY")
        if not judge.get("runtime_directory_preserved") or not judge.get("existing_literal_masking"):
            issues.append("EXISTING_SECRET_MASKING_UNVERIFIED")
        if not judge.get("budget_readable") or not judge.get("budget_unchanged") or not 12 <= judge.get("requests_attempted", -1) <= 24:
            issues.append("EXISTING_BUDGET_UNVERIFIED")
        elif judge.get("remaining", 0) < 4:
            issues.append("JUDGE_BUDGET_INSUFFICIENT_FOR_READ_AND_WRITE")
        judge["authentication"] = "CONTROL_FILE_API_KEY_SEPARATE_FROM_ACTOR"
        judge["endpoint"] = "https://api.openai.com/v1/responses"
        judge["model_access"] = "NOT_VERIFIED_NO_REQUEST"
    except (OSError, ValueError, subprocess.SubprocessError):
        issues.append("CONTROL_JEV_DIAGNOSTIC_UNAVAILABLE" if jev else "CONTROL_JUDGE_DIAGNOSTIC_UNAVAILABLE")
    report["ready_to_open_cli"] = not issues
    return report
